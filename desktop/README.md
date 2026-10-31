# Consilium Desktop Audio Agent

**Note:** Consilium live meetings use the browser **Web Speech API** by default (no Whisper). This desktop daemon is a legacy/optional faster-whisper path and is not required for the meeting UI.

Captures system audio + microphone at the OS level and streams live transcription to the Consilium backend via WebSocket.

**No Zoom/Meet/Teams SDK** — works with any meeting platform.

## Prerequisites

### macOS
1. Install [BlackHole](https://existential.audio/blackhole/) (2ch virtual audio driver)
2. In **Audio MIDI Setup**, create a Multi-Output Device combining your speakers + BlackHole
3. Set system output to that Multi-Output Device during meetings
4. Select BlackHole as the loopback input in the agent (auto-detected by name)

### Windows
1. Install [VB-CABLE](https://vb-audio.com/Cable/)
2. Route meeting app audio through CABLE Input; agent captures CABLE Output

### Linux
1. Use PipeWire/PulseAudio monitor source (auto-detected if named "monitor" or "loopback")

## Install

From the **repository root** (`ai-mind-works/`):

```bash
pip install -r desktop/requirements.txt
```

Optional: use a virtualenv inside `desktop/`:

```bash
cd desktop
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..   # return to repo root before running
```

First run downloads the Whisper model (~75MB for `tiny`).

## Usage (recommended — auto-start)

1. **Start the daemon once** (leave running in a terminal):

```bash
cd /path/to/ai-mind-works
python -m desktop.daemon
```

2. In Consilium, open a meeting and click **Start meeting**
3. Transcription begins automatically — no copy-paste commands
4. Click **Stop meeting** when done (daemon stops capture; keep daemon running for the next meeting)

The browser talks to the daemon at `http://127.0.0.1:9477` (CORS-enabled for localhost).

## Usage (manual CLI — fallback)

If you prefer not to run the daemon:

```bash
python -m desktop \
  --meeting-id=YOUR_MEETING_ID \
  --token=YOUR_JWT_ACCESS_TOKEN \
  --ws-url=ws://localhost:8000
```

## Options (CLI)

| Flag | Default | Description |
|------|---------|-------------|
| `--meeting-id` | required | Meeting ID from Consilium |
| `--token` | required | JWT access token (`consilium.auth.token` in browser localStorage) |
| `--ws-url` | `ws://localhost:8000` | Backend WebSocket base URL |
| `--whisper-model` | `tiny` | faster-whisper model (`tiny`, `base`, `small`) |

## Pipeline

```
System Audio + Mic → 16kHz mono PCM (2s chunks) → faster-whisper → WebSocket → MongoDB
```

Speaker diarization (Pyannote) is deferred — transcripts appear without speaker labels in v1.

## Troubleshooting

- **`No module named 'desktop'`**: Run from the repo root (`ai-mind-works/`), not from inside `desktop/`
- **Start meeting but no transcript**: Ensure `python -m desktop.daemon` is running; check the Audio agent card on the meeting page
- **No loopback device**: Agent falls back to microphone-only; install virtual audio driver above
- **Slow transcription**: Use `--whisper-model=tiny` (default) or enable GPU in faster-whisper
- **WS drops mid-meeting**: Agent auto-reconnects up to 3 times; avoid `uvicorn --reload` while capturing
