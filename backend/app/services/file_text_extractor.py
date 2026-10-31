"""Extract plain text from uploaded files of many formats (text, PDF, DOCX, audio)."""
from __future__ import annotations

import io
import re
from typing import Optional, Tuple

from fastapi import HTTPException, status

from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_UPLOAD_BYTES = 40 * 1024 * 1024  # 40 MB
MAX_TEXT_CHARS = 80_000

AUDIO_EXTENSIONS = {
    ".flac",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".ogg",
    ".wav",
    ".webm",
}
AUDIO_MIMES = {
    "audio/flac",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-wav",
    "audio/x-m4a",
    "video/mp4",
    "video/webm",
    "video/mpeg",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".log",
    ".vtt",
    ".srt",
    ".html",
    ".htm",
    ".xml",
    ".yml",
    ".yaml",
    ".rst",
}


def _ext(filename: Optional[str]) -> str:
    name = (filename or "").lower()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    ok = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    return ok / len(text)


def _from_utf8(content: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            text = content.decode(enc)
            if _printable_ratio(text) >= 0.85:
                return text
        except Exception:
            continue
    text = content.decode("utf-8", errors="ignore")
    return text if _printable_ratio(text) >= 0.7 else ""


def _from_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF support requires pypdf. Install backend requirements.",
        ) from e
    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts).strip()


def _from_docx(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DOCX support requires python-docx. Install backend requirements.",
        ) from e
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()


async def _from_audio(content: bytes, filename: str, content_type: Optional[str]) -> str:
    # Live meetings use the browser Web Speech API — not Whisper.
    # Uploaded audio/video is not transcribed server-side.
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Audio/video upload is not supported ({filename}). "
            "For live transcription use Start meeting (Chrome/Edge Web Speech). "
            "To import a past meeting, upload a text transcript (.txt, .md, .vtt, .srt), PDF, or DOCX."
        ),
    )


async def extract_text_from_upload(
    content: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Return (text, source_kind) where source_kind is text|pdf|docx|audio|binary-text.
    Raises HTTPException if nothing usable can be extracted.
    """
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )

    name = filename or "upload.bin"
    ext = _ext(name)
    mime = (content_type or "").lower().split(";")[0].strip()

    text = ""
    kind = "text"

    try:
        if ext == ".pdf" or mime == "application/pdf":
            kind = "pdf"
            text = _from_pdf(content)
        elif ext in {".docx"} or mime in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            kind = "docx"
            text = _from_docx(content)
        elif ext in AUDIO_EXTENSIONS or mime in AUDIO_MIMES or mime.startswith("audio/"):
            kind = "audio"
            text = await _from_audio(content, name, content_type)
        elif ext in TEXT_EXTENSIONS or mime.startswith("text/") or mime in {
            "application/json",
            "application/xml",
            "application/csv",
        }:
            kind = "text"
            text = _from_utf8(content)
        else:
            # Best-effort: treat as text if mostly printable, else try PDF magic
            if content[:4] == b"%PDF":
                kind = "pdf"
                text = _from_pdf(content)
            elif content[:2] == b"PK" and ext in {".doc", ".odt"}:
                # zip-based office — try docx parser for .docx-like; otherwise utf8 fallback
                try:
                    text = _from_docx(content)
                    kind = "docx"
                except Exception:
                    text = _from_utf8(content)
                    kind = "binary-text"
            else:
                text = _from_utf8(content)
                kind = "binary-text"
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload extract failed for %s", name)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read this file ({name}): {e}",
        ) from e

    text = (text or "").strip()
    # Normalize whitespace a bit for transcripts
    text = re.sub(r"\r\n?", "\n", text)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]

    if not text or len(text) < 3:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Could not extract usable text from '{name}'. "
                "Supported uploads: text (.txt, .md, .vtt, .srt), PDF, or DOCX. "
                "Live speech uses browser Web Speech (Chrome/Edge) — not Whisper."
            ),
        )
    return text, kind
