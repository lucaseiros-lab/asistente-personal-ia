from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.client import get_ai_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TRANSCRIBE_PROMPT = (
    "Transcribí este audio de forma literal, en español. Devolvé "
    "únicamente el texto transcripto, sin comentarios ni formato adicional."
)


class TranscriptionError(Exception):
    pass


class TranscriptionService:
    """Convierte audio a texto usando un modelo multimodal de Gemini.

    El texto resultante se trata como cualquier mensaje de texto: nunca se
    interpreta acá mismo, solo se transcribe. La interpretación de intención
    ocurre siempre después, en el Motor IA, vía Structured Outputs.
    """

    def __init__(self, client: genai.Client | None = None) -> None:
        self._client = client or get_ai_client()

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def transcribe(self, audio_bytes: bytes, *, filename: str, content_type: str) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=settings.GEMINI_TRANSCRIBE_MODEL,
                contents=[
                    _TRANSCRIBE_PROMPT,
                    types.Part.from_bytes(data=audio_bytes, mime_type=content_type),
                ],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("transcription_call_failed", error=str(exc))
            raise TranscriptionError("Fallo al transcribir el audio") from exc

        text = response.text
        if not text:
            raise TranscriptionError("El modelo no devolvió texto transcripto")

        return text.strip()
