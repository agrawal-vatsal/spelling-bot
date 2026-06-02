# Spell Bee Voice Bot

A real-time voice spelling-bee game built with [Pipecat](https://github.com/pipecat-ai/pipecat) 1.3.x.
The browser connects over WebRTC; the bot listens to speech, judges the spelling, keeps score, and speaks back.

---

## Quick start

```bash
# 1. Install dependencies
uv sync

# 2. Configure credentials
cp .env.example .env
# Edit .env and fill in:
#   DEEPGRAM_API_KEY=...   (STT + TTS)
#   GROQ_API_KEY=...       (Groq LLM — for fallback)
#   GEMINI_API_KEY=...     (primary LLM, used by default)

# 3. Run the bot
uv run python -m app.bot

# 4. Open the game in your browser
open http://localhost:7860
```

Click **Connect**, allow microphone access, and start spelling.

---

## How it works

### Frame pipeline

```
[auto] RTVIProcessor          ← RTVI handshake + server→client messaging
  → transport.input()         ← WebRTC audio in (SmallWebRTC)
  → Deepgram STT              ← audio → TranscriptionFrame
  → SpellingValidator         ← judges attempt, updates game, sends RTVIServerMessageFrame
  → user_aggregator           ← accumulates user turn; VAD (Silero, stop_secs=0.8)
  → Gemini LLM                ← context → streamed reply text
  → Deepgram TTS              ← text → audio
  → transport.output()        ← audio out to browser
  → assistant_aggregator      ← records bot reply in context
```

### Custom frame processor (`app/processors/spelling_validator.py`)

`SpellingValidator` sits between STT and the user aggregator.
It watches for finalized `TranscriptionFrame`s, normalizes the spoken letters
(handling spoken letter-names like "ay pee pee el ee" → "apple"), and compares
against the current target word from `SpellBeeGame`.

On each attempt it:
1. Records the result and advances the game.
2. **Pushes `RTVIServerMessageFrame`** — the RTVI observer automatically converts
   this into a JSON `server-message` that reaches the browser over the WebRTC data channel.
3. Injects an `LLMMessagesAppendFrame` with a verdict instruction, so the host LLM
   reacts and either presents the next word or wraps up.

The original transcription is consumed (not forwarded) so the raw letters don't
also drive the LLM through the normal turn path.

### Game state reaching the frontend

Pipecat 1.3.x's `PipelineTask` enables RTVI automatically (`enable_rtvi=True`
default).  It prepends an `RTVIProcessor` and wires up an `RTVIObserver`.
Any frame processor can push `RTVIServerMessageFrame(data={...})` and the observer
serialises it to a `{"label":"rtvi-ai","type":"server-message","data":{...}}`
JSON message that the JS client receives as an `RTVIEvent.ServerMessage` event.

### Frontend

`app/static/index.html` is a self-contained vanilla-JS page served at `/`.
It loads `@pipecat-ai/client-js` and `@pipecat-ai/small-webrtc-transport` from
`esm.sh` (CDN), connects to `/start`, and listens for `RTVIEvent.ServerMessage`
to update the live score panel alongside the audio session.

> The page requires internet access at runtime to fetch the Pipecat JS SDK from `esm.sh`.

---

## Environment variables

| Variable            | Required | Default                    | Description                    |
|---------------------|----------|----------------------------|--------------------------------|
| `DEEPGRAM_API_KEY`  | ✓        | —                          | Deepgram STT + TTS             |
| `GOOGLE_API_KEY`    | ✓        | —                          | Google Gemini (fallback LLM)   |
| `GROQ_API_KEY`      |          | —                          | Groq (primary LLM)             |
| `GEMINI_MODEL`      |          | `gemini-2.5-flash`         | Gemini model ID                |
| `GROQ_MODEL`        |          | `llama-3.3-70b-versatile`  | Groq model ID                  |
| `DEEPGRAM_VOICE`    |          | `aura-2-andromeda-en`      | TTS voice                      |
| `DEEPGRAM_STT_MODEL`|          | `nova-3`                   | STT model                      |
| `HOST`              |          | `0.0.0.0`                  | Server bind host               |
| `PORT`              |          | `7860`                     | Server port                    |

---

## Running tests

```bash
uv run pytest tests/
```

Tests cover `SpellBeeGame` (state machine) and `normalize_spelling` (transcription normalizer).

---

## RTVI verification (1.3.0)

Verified against the installed `pipecat-ai==1.3.0` source:

- `PipelineTask` / `PipelineWorker` has `enable_rtvi=True` by default.
  When no `RTVIProcessor` is in the pipeline, one is auto-prepended and an
  `RTVIObserver` is auto-added — **no manual wiring needed**.
- Pushing `RTVIServerMessageFrame(data={...})` from any processor causes the
  observer to emit a `server-message` RTVI frame to the transport.
- The JS client SDK event is `RTVIEvent.ServerMessage` (= `"serverMessage"`),
  confirmed in the prebuilt client bundle.
- JS packages used: `@pipecat-ai/client-js` and `@pipecat-ai/small-webrtc-transport`
  (identified from the prebuilt bundle imports).
- Transport start flow: POST `/start` with `{transport:"webrtc", enableDefaultIceServers:true}`,
  then WebRTC offer/answer at `/sessions/{id}/api/offer` (handled internally by the SDK).
