"""Pipeline assembly.

Builds the Pipecat processing pipeline and the conversation context/aggregators.

Pipeline order (each processor hands frames to the next):

    transport.input()      audio in from the browser
      -> stt               speech -> text (TranscriptionFrame)
      -> user_aggregator   collects the user's turn into the LLM context
      -> llm               context -> reply text (streamed)
      -> tts               reply text -> speech audio
      -> transport.output() audio out to the browser
      -> assistant_aggregator  records what the bot said back into context

Turn-taking note (Pipecat 1.x):
VAD is attached to the USER aggregator, not the transport. The Silero VAD
analyzer detects when the user starts/stops speaking; `stop_secs` is how long a
silence must last before the user's turn is considered finished. This is also
what enables interruptions — while the bot is speaking, fresh user speech
detected by VAD interrupts it. (A smarter, ML-based turn detector,
LocalSmartTurnAnalyzerV3, can be layered on later via UserTurnStrategies.)
"""

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)

from app.core.config import Settings
from app.services.llm import create_llm
from app.services.stt import create_stt
from app.services.tts import create_tts

# Generic assistant persona for Iteration 0. Spoken-style: short, no markdown.
SYSTEM_PROMPT = (
    "You are a friendly, upbeat voice assistant. Keep replies short and "
    "conversational since they are spoken aloud. Do not use markdown, lists, "
    "or emojis. When the user first connects, greet them warmly and ask how "
    "you can help."
)


def build_pipeline(transport, settings: Settings):
    """Construct the pipeline and return (pipeline, context).

    Args:
        transport: The transport built by create_transport() (provides
            .input() and .output() processors).
        settings: Validated app settings.

    Returns:
        A tuple of (Pipeline, LLMContext). The context is returned so the
        caller (bot.py) can kick off the first LLM run to greet the user.
    """
    # --- AI services (provider details live in app/services) ---
    stt = create_stt(settings)
    tts = create_tts(settings)
    llm = create_llm(SYSTEM_PROMPT, settings)

    # --- Conversation context + aggregators ---
    # The context holds the running message history. The aggregator pair wraps
    # it: user() collects the user's spoken turn, assistant() records the bot's
    # replies. VAD is configured on the user side.
    context = LLMContext(messages=[{"role": "system", "content": SYSTEM_PROMPT}])
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            # stop_secs: silence (seconds) before the user's turn is "done".
            # 0.5s is responsive without clipping short pauses.
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )

    return pipeline, context