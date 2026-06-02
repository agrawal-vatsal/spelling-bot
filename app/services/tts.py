from pipecat.services.deepgram.tts import DeepgramTTSService

from app.core.config import get_settings


def create_tts(settings=None) -> DeepgramTTSService:
    """Return a configured Deepgram TTS service."""
    if settings is None:
        settings = get_settings()

    if not settings.deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY is missing from settings.")

    return DeepgramTTSService(
        api_key=settings.deepgram_api_key,
        voice=settings.deepgram_voice,
    )