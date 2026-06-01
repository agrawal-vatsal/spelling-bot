from loguru import logger
from pipecat.frames.frames import LLMMessagesAppendFrame
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from app.api.transport import get_transport_params
from app.core.config import get_settings
from app.pipeline import build_pipeline


async def bot(runner_args: RunnerArguments) -> None:
    """Session lifecycle worker for a single WebRTC browser connection."""
    settings = get_settings()
    logger.info("Starting a new voice bot session via SmallWebRTC...")

    # 1. Transport factory mapping (keyed by transport type, e.g. "webrtc").
    transport_params_map = get_transport_params()

    # 2. Build the transport the client requested.
    transport = await create_transport(runner_args, transport_params_map)

    pipeline, target_word = build_pipeline(transport, settings)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport_instance, client):
        logger.info(f"Client connected: {client}")
        # Tell the host which word to present; run_llm=True makes it speak.
        await task.queue_frames(
            [
                LLMMessagesAppendFrame(
                    messages=[
                        {
                            "role": "system",
                            "content": f"Greet the player warmly and present the word "
                                       f"'{target_word}'. Ask them to spell it out.",
                        }
                    ],
                    run_llm=True,
                )
            ]
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport_instance, client):
        logger.info("Client disconnected. Cancelling session task.")
        await task.cancel()

    # 5. Run the task via the runner.
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from app.core.logging import setup_logging
    from pipecat.runner.run import main

    setup_logging(level="INFO")  # configure logging once, at process start
    main()