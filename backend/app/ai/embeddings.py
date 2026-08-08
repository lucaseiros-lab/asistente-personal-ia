from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.client import get_openai_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingError(Exception):
    pass


class EmbeddingService:
    """Genera embeddings vectoriales para la memoria semántica."""

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or get_openai_client()

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def embed_text(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text,
                dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("embedding_call_failed", error=str(exc))
            raise EmbeddingError("Fallo al generar el embedding") from exc

        return response.data[0].embedding
