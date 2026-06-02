"""Application configuration.

All runtime configuration is read from environment variables (loaded from a
local .env in development) and validated once at startup via a pydantic-settings
model. Everything else in the app imports the singleton `settings` from here
rather than calling os.getenv directly, so there is exactly one place that knows
about the environment.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings.

    Reads from environment variables. Required keys (no default) will raise a
    clear validation error at startup if missing, which is what we want — fail
    fast instead of crashing mid-call with a confusing auth error.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Provider credentials (required) ---
    deepgram_api_key: str = Field(..., alias="DEEPGRAM_API_KEY")
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")

    # --- Provider credentials (optional) ---
    google_api_key: str | None = Field(None, alias="GOOGLE_API_KEY")

    # --- Model / voice selection (optional, sensible defaults) ---
    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")
    groq_model: str = Field("llama-3.3-70b-versatile", alias="GROQ_MODEL")
    deepgram_voice: str = Field("aura-2-andromeda-en", alias="DEEPGRAM_VOICE")
    deepgram_stt_model: str = Field("nova-3", alias="DEEPGRAM_STT_MODEL")

    # --- Server ---
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(7860, alias="PORT")


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton.

    Cached so the .env is parsed and validated only once per process.
    """
    return Settings()  # type: ignore[call-arg]