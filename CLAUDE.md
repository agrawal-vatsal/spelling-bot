# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the bot (starts the WebRTC server + serves the browser client)
python main.py

# Run with a specific log level
python -c "from app.core.logging import setup_logging; setup_logging('DEBUG')" && python main.py
```

The app has no test suite yet. There is no lint configuration; `pyproject.toml` only declares dependencies.

## Environment

Copy `.env.example` to `.env` and fill in the required keys:

```
DEEPGRAM_API_KEY=...   # required — STT + TTS
GOOGLE_API_KEY=...     # required — Gemini LLM
```

Optional overrides (all have defaults in `app/core/config.py`):
- `GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `DEEPGRAM_VOICE` (default: `aura-2-andromeda-en`)
- `DEEPGRAM_STT_MODEL` (default: `nova-3`)
- `HOST` / `PORT` (default: `0.0.0.0:7860`)

## Architecture

This is a real-time voice spelling-bee bot built on **Pipecat 1.3.x**. A browser connects over WebRTC; the bot listens to speech, processes it through a linear frame pipeline, and speaks back.

### Frame pipeline (defined in `app/pipeline.py`)

```
transport.input()        ← audio in from browser (SmallWebRTC)
  → STT (Deepgram)       ← audio frames → TranscriptionFrame
  → user_aggregator      ← accumulates user turn; VAD (Silero) lives here
  → LLM (Gemini)         ← context → streamed reply text
  → TTS (Deepgram Aura)  ← text → audio
  → transport.output()   ← audio out to browser
  → assistant_aggregator ← records bot reply back into context
```

VAD (voice activity detection) is on the **user aggregator**, not the transport — this is the Pipecat 1.x design. `stop_secs=0.5` controls how long a silence ends a user turn and also enables mid-speech interruptions of the bot.

### Session lifecycle (`app/bot.py`)

`bot(runner_args)` is the per-connection worker. The Pipecat runner (`pipecat.runner.run.main`) discovers and calls it. On `on_client_connected` it queues an `LLMRunFrame` to trigger the bot's opening greeting. On disconnect it cancels the pipeline task.

### Configuration (`app/core/config.py`)

`get_settings()` is an `@lru_cache` singleton backed by `pydantic-settings`. All modules import it rather than reading `os.environ` directly. Missing required keys raise a validation error at startup.

### AI services (`app/services/`)

Each file (`llm.py`, `stt.py`, `tts.py`) exposes a single `create_*` factory function that reads from `Settings` and returns the appropriate Pipecat service object. Pipecat 1.3.0-specific API differences (e.g., `LiveOptions`, nested `Settings` objects) are isolated here.

### Game logic (`app/game/words.py`)

`WORDS` is a plain list of dicts. The system prompt in `pipeline.py` embeds the word list directly as a formatted string — there is no runtime game state machine yet; the LLM manages turn progression conversationally.

### Transport (`app/api/transport.py`)

Only `"webrtc"` (SmallWebRTC) is supported. The Pipecat runner serves a prebuilt browser client automatically — no separate frontend to build or run.
