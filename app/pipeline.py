import random

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
from app.processors.spelling_validator import SpellingValidator

# Code owns the word. One random pick per session = one round.
WORD_POOL = ["apple", "garden", "rhythm", "bicycle", "island", "biscuit"]

SYSTEM_PROMPT = (
    "You are an excited, warm spell bee host speaking out loud in a voice game. "
    "Keep replies short and natural — no markdown, lists, or emojis. "
    "You will be TOLD which word to present and, after the player spells it, you "
    "will be TOLD whether they were right or wrong. Never choose a word yourself "
    "and never decide correctness yourself — always follow the instructions you "
    "are given. When asked to present a word, say it clearly and ask the player "
    "to spell it out letter by letter, but do NOT spell it for them."
)


def build_pipeline(transport, settings: Settings):
    """Build the pipeline. Returns (pipeline, target_word).

    target_word is returned so bot.py can have the host announce it on connect.
    """
    stt = create_stt(settings)
    tts = create_tts(settings)
    llm = create_llm(SYSTEM_PROMPT, settings, provider="groq")

    target_word = random.choice(WORD_POOL)

    context = LLMContext(messages=[{"role": "system", "content": SYSTEM_PROMPT}])
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.8)),
        ),
    )

    # The validator sits right after STT so it sees the user's transcription
    # before the aggregator turns it into an LLM turn.
    validator = SpellingValidator(target_word)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            validator,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )

    return pipeline, target_word