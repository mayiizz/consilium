import json
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqUnavailableError(Exception):
    pass


class GroqLLMService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def available(self) -> bool:
        return bool(self.settings.groq_api_key)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        if not self.available:
            raise GroqUnavailableError(
                "GROQ_API_KEY is not configured. Set it to enable AI features."
            )
        primary = (model or self.settings.groq_model or "").strip()
        fallback = (self.settings.groq_fallback_model or "openai/gpt-oss-120b").strip()
        candidates: List[str] = []
        for m in (primary, fallback, "openai/gpt-oss-120b"):
            if m and m not in candidates:
                candidates.append(m)

        last_exc: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=60.0) as client:
            for idx, use_model in enumerate(candidates):
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": use_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    body = ""
                    try:
                        body = (exc.response.text or "")[:400]
                    except Exception:
                        body = ""
                    last_exc = exc
                    if exc.response.status_code in (429, 503):
                        raise GroqUnavailableError(
                            "Groq rate limit or service unavailable; try again shortly"
                        ) from exc
                    # Deprecated / unknown model → try fallback
                    if exc.response.status_code in (400, 404) and idx < len(candidates) - 1:
                        logger.warning(
                            "Groq model %s failed (%s); retrying with next model. %s",
                            use_model,
                            exc.response.status_code,
                            body,
                        )
                        continue
                    if exc.response.status_code in (400, 404):
                        raise GroqUnavailableError(
                            f"Groq model unavailable ({use_model}): {body or exc}"
                        ) from exc
                    raise
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        raise GroqUnavailableError(str(last_exc) if last_exc else "Groq request failed")

    async def extract_tasks(self, transcript: str, context: str = "") -> List[Dict[str, Any]]:
        prompt = f"""Extract confirmed task commitments from this meeting transcript.
Return a JSON array of objects with keys: title, description, assignee, status, confidence, evidence, type.
Only include direct assignments or clear request+acceptance. Status must be one of: To Do, In Progress, In Review, Done, Blockers.
Score confidence 0.0-1.0 based on clarity of assignment. Include verbatim evidence quote.

Historical context (weight by network and confidence; adjust estimates if opinions suggest team patterns):
{context or "No prior memory."}

Rules:
- Only direct assignments or clear request+acceptance
- If historical context suggests this team underestimates tasks, adjust confidence down for vague estimates
- Include verbatim evidence quote in evidence field

Transcript:
{transcript}
"""
        raw = await self.chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a task extraction assistant. "
                        "Return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            logger.warning("Failed to parse task extraction JSON")
        return []

    async def suggest_status_moves(self, transcript: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prompt = f"""Given the latest meeting transcript and current tasks, suggest status changes.
Return JSON array with: task_id, new_status, evidence (verbatim quote from transcript), confidence (0.0-1.0), speaker (who said it if known).
Only suggest changes with clear transcript evidence.

Tasks: {json.dumps(tasks)}
Transcript: {transcript}
"""
        raw = await self.chat_completion(
            [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ]
        )
        try:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            logger.warning("Failed to parse status move JSON")
        return []

    async def board_sync_tasks(
        self,
        latest_transcript: str,
        board_snapshot: List[Dict[str, Any]],
        *,
        latest_meeting_id: str = "",
        reference_date: str = "",
    ) -> Dict[str, Any]:
        payload = {
            "latest_meeting_id": latest_meeting_id,
            "reference_date": reference_date,
            "kanban_board": board_snapshot,
            "latest_meeting_transcript": latest_transcript,
        }
        sys_prompt = """You are updating a Kanban board from the LATEST meeting only.
Output ONE JSON object only:
{
  "task_updates": [
    {
      "task_id": "string",
      "new_status": "todo" | "in_progress" | "in_review" | "done" | "blockers",
      "due_date": "YYYY-MM-DD" | null,
      "blockers": ["string"],
      "transcript_evidence": "verbatim excerpt from latest_meeting_transcript",
      "confidence": 0.0-1.0
    }
  ],
  "informal_action_items": ["string"]
}
transcript_evidence MUST be copied verbatim. If you cannot quote it, omit the update."""
        raw = await self.chat_completion(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            max_tokens=self.settings.task_automation_board_sync_max_tokens,
            temperature=0.1,
        )
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                if isinstance(data, dict):
                    return data
        except json.JSONDecodeError:
            logger.warning("Failed to parse board sync JSON")
        return {"task_updates": [], "informal_action_items": []}

    async def summarize_meeting(self, transcript: str) -> Dict[str, Any]:
        if not self.available:
            raise GroqUnavailableError(
                "GROQ_API_KEY is not configured. Set it in backend/.env and restart the API."
            )
        prompt = f"""Summarize this meeting transcript. Return JSON with keys:
- summary (string): concise overview
- action_items (array of strings): commitments and tasks with assignees when mentioned
- key_decisions (array of strings): decisions made, blockers discussed, and resolved items

Extract decisions, blockers, commitments, and assignments explicitly.

Transcript:
{transcript[:8000]}
"""
        raw = await self.chat_completion(
            [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            model=self.settings.groq_summary_model,
        )
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
        return {"summary": raw, "action_items": [], "key_decisions": []}

    async def copilot_reply(
        self,
        message: str,
        context: str,
        history: str,
    ) -> str:
        if not self.available:
            return (
                "Copilot is running in offline mode. Configure GROQ_API_KEY for AI responses. "
                f"You asked: {message}"
            )
        system = (
            "You are Consilium Copilot, an AI assistant for project meetings and tasks.\n"
            f"Workspace context:\n{context}\n\nConversation history:\n{history}"
        )
        return await self.chat_completion(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ]
        )

    async def transcribe_audio(
        self,
        content: bytes,
        filename: str = "audio.webm",
        content_type: Optional[str] = None,
        model: str = "whisper-large-v3",
    ) -> str:
        """Speech-to-text via Groq Whisper (OpenAI-compatible audio API)."""
        if not self.available:
            raise GroqUnavailableError(
                "GROQ_API_KEY is not configured. Set it to enable audio transcription."
            )
        mime = content_type or "application/octet-stream"
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
                files={"file": (filename or "audio.webm", content, mime)},
                data={"model": model, "response_format": "text"},
            )
            if resp.status_code >= 400:
                detail = resp.text[:500]
                logger.error("Groq transcription failed: %s %s", resp.status_code, detail)
                raise GroqUnavailableError(f"Audio transcription failed: {detail}")
            text = (resp.text or "").strip()
            # Sometimes JSON wrapper
            if text.startswith("{"):
                try:
                    data = resp.json()
                    text = str(data.get("text") or text)
                except Exception:
                    pass
            return text.strip()
