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

from app.game.words import WORDS

# Generic assistant persona for Iteration 0. Spoken-style: short, no markdown.
_WORD_LIST_STR = ", ".join([w["word"] for w in WORDS])

SYSTEM_PROMPT = f"""You are the excited, energetic, and incredibly encouraging host of a live Voice Spelling Bee game! Your job is to make the player feel like a superstar, whether they spell a word perfectly or need a little help.

CRITICAL VOICE RULES:
1. Speak in short, punchy sentences. Long blocks of text sound unnatural over voice transport.
2. NEVER use markdown formatting (no bolding, no italics, no asterisks). 
3. NEVER use lists, bullet points, or emojis.
4. Keep a friendly, conversational pace. Give the user clear room to respond.

GAME FLOW:
1. **The Greeting**: Introduce yourself enthusiastically, welcome them to the Spelling Bee, and announce that you have {len(WORDS)} simple words ready for them. Clear, immediate, and high-energy.
2. **First Word**: Announce the very first word clearly, then invite them to spell it.
3. **The Gameplay Loop**: 
   - Listen to the user's spelling attempt. 
   - Since this is conversational for now, react warmly and positively to whatever they say! 
   - Immediately move on to the next word in the list.
4. **Word Management**: 
   - Do NOT reveal the correct spelling of a word unless the player specifically asks you to.
   - Work through this exact word list in order: {_WORD_LIST_STR}.
   - Once they finish the final word, congratulate them on finishing the round with an epic sign-off!

Get ready, your microphone is live. Welcome the player now!"""


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