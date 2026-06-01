from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.llm_service import LLMService

from app.core.config import get_settings


def create_llm(system_prompt: str, settings=None, provider: str | None = None) -> LLMService:
    if settings is None:
        settings = get_settings()

    provider = (provider or "gemini").lower()

    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing from settings.")
        return GroqLLMService(
            api_key=settings.groq_api_key,
            settings=GroqLLMService.Settings(model=settings.groq_model),
        )

    # Default: Gemini
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is missing from settings.")
    return GoogleLLMService(
        api_key=settings.google_api_key,
        system_instruction=system_prompt,
        settings=GoogleLLMService.Settings(model=settings.gemini_model),
    )
