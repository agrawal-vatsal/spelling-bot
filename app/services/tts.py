from pipecat.services.deepgram.tts import DeepgramTTSService

from app.core.config import get_settings


def create_tts(settings=None) -> DeepgramTTSService:
    """Creates and configures a Deepgram Text-to-Speech (TTS) service instance for Pipecat 1.3.0.

    Args:
        settings: Optional pre-loaded settings instance; defaults to resolving via get_settings().
    """
    if settings is None:
        settings = get_settings()

    api_key = settings.deepgram_api_key
    if not api_key:
        raise ValueError("Deepgram API Key is missing from settings.")

    # In 1.3.0, voice is specified as a top-level kwarg to the DeepgramTTSService constructor
    return DeepgramTTSService(
        api_key=api_key,
        voice=settings.deepgram_voice,  # defaults to "aura-2-andromeda-en"
    )