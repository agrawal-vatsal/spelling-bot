from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions

from app.core.config import get_settings


def create_stt(settings=None) -> DeepgramSTTService:
    """Creates and configures a Deepgram Speech-to-Text (STT) service instance for Pipecat 1.3.0.

    Args:
        settings: Optional pre-loaded settings instance; defaults to resolving via get_settings().
    """
    if settings is None:
        settings = get_settings()

    api_key = settings.deepgram_api_key
    if not api_key:
        raise ValueError("Deepgram API Key is missing from settings.")

    # In 1.3.0, model, language, and smart_format must be bundled into LiveOptions
    # rather than passed as top-level kwargs to DeepgramSTTService.
    stt_options = LiveOptions(
        model=settings.deepgram_stt_model,  # defaults to "nova-3"
        language="en-US",
        smart_format=True,
    )

    return DeepgramSTTService(
        api_key=api_key,
        live_options=stt_options,
    )