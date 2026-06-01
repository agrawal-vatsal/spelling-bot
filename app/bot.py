from pipecat.frames.frames import LLMRunFrame
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

from loguru import logger

from app.core.config import get_settings
from app.api.transport import get_transport_params
from app.pipeline import build_pipeline


async def bot(runner_args: RunnerArguments) -> None:
    """Session lifecycle worker for a single WebRTC browser connection."""
    settings = get_settings()
    logger.info("Starting a new voice bot session via SmallWebRTC...")

    # 1. Transport factory mapping (keyed by transport type, e.g. "webrtc").
    transport_params_map = get_transport_params()

    # 2. Build the transport the client requested.
    transport = await create_transport(runner_args, transport_params_map)

    # 3. Build the processor pipeline; context lets us trigger the greeting.
    pipeline, context = build_pipeline(transport, settings)

    # 4. Wrap the pipeline in a task. PipelineParams configures run-time behaviour
    #    (metrics, etc). The task is RUN BY a PipelineRunner — never call
    #    task.run() yourself; that's the runner's job.
    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport_instance, client):
        logger.info(f"Client connected: {client}")
        # Kick off the bot's opening line. The pipeline emits its own StartFrame
        # when the runner starts the task, so we do NOT queue one here.
        await task.queue_frames([LLMRunFrame()])

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