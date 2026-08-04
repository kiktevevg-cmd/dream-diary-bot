from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str
    webhook_url: str = ""
    webhook_path: str = "/webhook"
    webhook_secret: str = ""

    # Database (Railway provides DATABASE_URL)
    database_url_override: str = Field(default="", validation_alias="DATABASE_URL")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "dream_diary"
    postgres_password: str = "changeme"
    postgres_db: str = "dream_diary"

    # Redis (Railway provides REDIS_URL)
    redis_url_override: str = Field(default="", validation_alias="REDIS_URL")
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # LLM — Kimi (Moonshot API, OpenAI-compatible)
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("KIMI_API_KEY", "LLM_API_KEY", "MOONSHOT_API_KEY"),
    )
    llm_api_base: str = "https://api.moonshot.ai/v1"
    llm_model: str = "kimi-k2.6"
    llm_timeout: int = 180
    llm_max_retries: int = 2

    # Whisper (отдельно от Kimi — у Moonshot нет speech-to-text)
    whisper_api_key: str = ""
    whisper_api_base: str = "https://api.openai.com/v1"
    whisper_model: str = "whisper-1"

    # Security
    encryption_key: str = ""

    # App (Railway provides PORT)
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, validation_alias="PORT")
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgres://"):
                return url.replace("postgres://", "postgresql+asyncpg://", 1)
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def voice_enabled(self) -> bool:
        return bool(self.whisper_api_key)


settings = Settings()
