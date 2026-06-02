from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions

from app.core.config import get_settings


def create_stt(settings=None) -> DeepgramSTTService:
    """Return a configured Deepgram STT service."""
    if settings is None:
        settings = get_settings()

    if not settings.deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY is missing from settings.")

    return DeepgramSTTService(
        api_key=settings.deepgram_api_key,
        live_options=LiveOptions(
            model=settings.deepgram_stt_model,
            language="en-US",
            smart_format=True,
        ),
    )