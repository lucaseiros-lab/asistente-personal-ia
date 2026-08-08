from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación, cargada desde variables de entorno."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicación
    APP_NAME: str = "Asistente Personal IA"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Base de datos
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/asistente"
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/asistente"
    )

    # Seguridad / JWT
    JWT_SECRET_KEY: str = Field(default="CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # OpenAI
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_TRANSCRIBE_MODEL: str = "whisper-1"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536

    # Automatizaciones
    N8N_BASE_URL: str = Field(default="")
    N8N_WEBHOOK_TOKEN: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
