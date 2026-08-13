from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.client import get_ai_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingError(Exception):
    pass


class EmbeddingService:
    """Genera embeddings vectoriales para la memoria semántica."""

    def __init__(self, client: genai.Client | None = None) -> None:
        self._client = client or get_ai_client()

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def embed_text(self, text: str) -> list[float]:
        try:
            response = await self._client.aio.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
                config={"output_dimensionality": settings.GEMINI_EMBEDDING_DIMENSIONS},
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("embedding_call_failed", error=str(exc))
            raise EmbeddingError("Fallo al generar el embedding") from exc

        return response.embeddings[0].values
