from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.client import get_openai_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TranscriptionError(Exception):
    pass


class TranscriptionService:
    """Convierte audio a texto usando el modelo de transcripción de OpenAI.

    El texto resultante se trata como cualquier mensaje de texto: nunca se
    interpreta acá mismo, solo se transcribe. La interpretación de intención
    ocurre siempre después, en el Motor IA, vía Structured Outputs.
    """

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or get_openai_client()

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def transcribe(self, audio_bytes: bytes, *, filename: str, content_type: str) -> str:
        try:
            response = await self._client.audio.transcriptions.create(
                model=settings.OPENAI_TRANSCRIBE_MODEL,
                file=(filename, audio_bytes, content_type),
                language="es",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("transcription_call_failed", error=str(exc))
            raise TranscriptionError("Fallo al transcribir el audio") from exc

        return response.text
