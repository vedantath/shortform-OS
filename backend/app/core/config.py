from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # Visuals
    pexels_api_key: str = ""
    pixabay_api_key: str = ""

    # YouTube OAuth
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://shortform-os:password@db:5432/shortform-os"

    # Redis / Celery broker
    redis_url: str = "redis://redis:6379/0"

    # Reddit (read-only app credentials — no user account needed)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""

    # Storage
    media_dir: str = "/app/media"


settings = Settings()
