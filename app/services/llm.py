from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.llm_service import LLMService

from app.core.config import get_settings

GROQ = "groq"
GEMINI = "gemini"
_PROVIDERS = (GROQ, GEMINI)


def create_llm(system_prompt: str, settings=None, provider: str | None = None) -> LLMService:
    if settings is None:
        settings = get_settings()

    provider = (provider or GROQ).lower()

    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Use {GROQ!r} or {GEMINI!r}.")

    if provider == GROQ:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing from settings.")
        return GroqLLMService(
            api_key=settings.groq_api_key,
            settings=GroqLLMService.Settings(model=settings.groq_model),
        )

    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is missing from settings.")
    return GoogleLLMService(
        api_key=settings.google_api_key,
        system_instruction=system_prompt,
        settings=GoogleLLMService.Settings(model=settings.gemini_model),
    )
