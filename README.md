# ai-mind-works (Consilium)

Monorepo: `frontend/`, `backend/`, `desktop/`.

**Product documentation:** [docs/PRD.md](docs/PRD.md) — full PRD of implemented features, flows, APIs, and gaps.

## Documentation

- [Product Requirements (PRD)](docs/PRD.md)
- [Technical Implementation](docs/TECHNICAL_IMPLEMENTATION.md)

## Run locally

### 1. Infrastructure

```bash
cd backend
docker compose up -d mongodb redis
```

### 2. Backend API

```bash
cd backend
cp .env.example .env   # set GROQ_API_KEY and TINYFISH_API_KEY (research)

# Infrastructure only (do not start the `api` service — it conflicts on port 8000):
docker compose up -d mongodb redis

# If Docker API is already running, stop it so local uvicorn uses your .env:
# docker compose stop api

PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://127.0.0.1:8000/api/health` should show `"groq_configured": true`.

API: http://localhost:8000

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

### 4. Live transcription (Web Speech API)

Live meetings use the browser **Web Speech API** (Chrome or Edge). Allow microphone access when you start a meeting — no Whisper and no desktop audio daemon required for transcription.

Optional legacy desktop Whisper agent still lives under `desktop/` but is not used by the meeting UI.

### 5. Post-meeting processing

When a meeting ends, summary, action items, decisions, and tasks are generated **automatically in the API process**. A Celery worker is **optional** for scheduled background jobs.

Without `GROQ_API_KEY`, the backend still saves a basic summary and creates tasks from transcript content.

### 6. Verify end-to-end

1. Log in and open a workspace meeting page (Chrome or Edge).
2. Start the meeting and allow the microphone.
3. Speak for a few seconds — your lines should appear in the live transcript.
4. Stop the meeting.
5. Within a few seconds: Summary tab shows text, Action items tab shows bullets and extracted tasks.

### Research agent

Manager → **Research** is a chat UI. Groq answers normally; **TinyFish** Search + Agent runs only when the conversation needs live web sources (markets, competitors, citations, etc.). Completed reports stay attached in the thread with **MD / JSON / CSV / PDF** exports.

Set `TINYFISH_API_KEY` and `GROQ_API_KEY` in `backend/.env` (never expose keys to the frontend). Use `GROQ_MODEL=openai/gpt-oss-120b` — older IDs like `qwen/qwen3-32b` return HTTP 404. Restart the API and Celery worker after changing keys.
