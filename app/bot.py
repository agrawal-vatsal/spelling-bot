import app.routes  # registers GET / and GET /game before the runner's redirect  # noqa: F401

from loguru import logger
from pipecat.frames.frames import LLMMessagesAppendFrame
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from app.api.transport import get_transport_params
from app.core.config import get_settings
from app.pipeline import build_pipeline
from app.prompts import greeting


async def bot(runner_args: RunnerArguments) -> None:
    """Session lifecycle worker for a single WebRTC browser connection."""
    settings = get_settings()
    logger.info("Starting a new voice bot session via SmallWebRTC...")

    transport = await create_transport(runner_args, get_transport_params())

    pipeline, game = build_pipeline(transport, settings)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport_instance, client):
        logger.info(f"Client connected: {client}")
        first_word = game.current_word()

        # Push initial game state to the browser UI immediately on connect.
        initial_state = RTVIServerMessageFrame(
            data={
                "type": "game_state",
                "score": game.score,
                "wordNumber": game.word_number,
                "totalWords": game.total_words,
                "finished": game.is_finished(),
            }
        )

        # Tell the host to greet and present word 1.
        opening = LLMMessagesAppendFrame(
            messages=[{"role": "system", "content": greeting(game.total_words, first_word)}],
            run_llm=True,
        )

        await task.queue_frames([initial_state, opening])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport_instance, client):
        logger.info("Client disconnected. Cancelling session task.")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from app.core.logging import setup_logging
    from pipecat.runner.run import main

    setup_logging(level="INFO")
    main()
