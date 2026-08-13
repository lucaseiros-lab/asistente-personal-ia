from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_JWT_SECRET = "CHANGE_ME_IN_PRODUCTION"


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
    JWT_SECRET_KEY: str = Field(default=_INSECURE_DEFAULT_JWT_SECRET)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Google Gemini
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TRANSCRIBE_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_DIMENSIONS: int = 768

    # Automatizaciones
    N8N_BASE_URL: str = Field(default="")
    N8N_WEBHOOK_TOKEN: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.is_production and self.JWT_SECRET_KEY == _INSECURE_DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY debe configurarse con un valor seguro en producción "
                "(ENVIRONMENT=production usa todavía el valor por defecto)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
