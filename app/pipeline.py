from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)

from app.core.config import Settings
from app.game.state import SpellBeeGame
from app.processors.spelling_validator import SpellingValidator
from app.prompts import SYSTEM_PROMPT
from app.services.llm import create_llm
from app.services.stt import create_stt
from app.services.tts import create_tts


def build_pipeline(transport, settings: Settings):
    """Build the pipeline. Returns (pipeline, game).

    game is returned so bot.py can announce word 1 and send the initial
    RTVI state on connect.
    """
    stt = create_stt(settings)
    tts = create_tts(settings)
    llm = create_llm(SYSTEM_PROMPT, settings)

    game = SpellBeeGame()

    context = LLMContext(messages=[{"role": "system", "content": SYSTEM_PROMPT}])
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.8)),
        ),
    )

    validator = SpellingValidator(game)

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

    return pipeline, game
