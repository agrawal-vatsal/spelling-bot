from pipecat.services.google.llm import GoogleLLMService

from app.core.config import get_settings


def create_llm(system_prompt: str, settings=None) -> GoogleLLMService:
    """Creates and configures a Google Gemini LLM service instance for Pipecat 1.3.0.

    Args:
        system_prompt: The instructions governing the LLM's persona and behavior.
        settings: Optional pre-loaded settings instance; defaults to resolving via get_settings().
    """
    if settings is None:
        settings = get_settings()

    api_key = settings.google_api_key
    if not api_key:
        raise ValueError("Google API Key is missing from settings.")

    # Model configuration passed via the nested Settings object in 1.3.0
    llm_settings = GoogleLLMService.Settings(
        model=settings.gemini_model,
    )

    # system_instruction is passed as a top-level parameter to the service initialization
    return GoogleLLMService(
        api_key=api_key,
        system_instruction=system_prompt,
        settings=llm_settings,
    )