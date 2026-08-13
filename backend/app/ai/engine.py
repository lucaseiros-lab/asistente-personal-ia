from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.client import get_ai_client
from app.ai.prompts import load_system_prompt
from app.ai.schemas import AssistantInterpretation, ChatTurn
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIEngineError(Exception):
    """El Motor IA no pudo producir una interpretación estructurada válida."""


class AIEngine:
    """Interpreta mensajes del usuario exclusivamente mediante Structured Outputs.

    Nunca se hace parsing de texto libre: toda intención, prioridad y acción
    proviene de un objeto `AssistantInterpretation` validado por el SDK de
    Gemini contra un JSON Schema estricto.
    """

    def __init__(self, client: genai.Client | None = None) -> None:
        self._client = client or get_ai_client()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(TimeoutError),
    )
    async def interpret_message(
        self,
        *,
        user_message: str,
        conversation_history: list[ChatTurn] | None = None,
        memory_context: str = "",
    ) -> AssistantInterpretation:
        system_prompt = load_system_prompt()
        if memory_context:
            system_prompt = f"{system_prompt}\n\n## Contexto de memoria relevante\n{memory_context}"

        contents: list[types.Content] = []
        for turn in conversation_history or []:
            role = "model" if turn.role == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn.content)]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=AssistantInterpretation,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - se traduce a un error de dominio
            logger.error("ai_engine_call_failed", error=str(exc))
            raise AIEngineError("Fallo al interpretar el mensaje con el Motor IA") from exc

        block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else None
        if block_reason:
            raise AIEngineError(f"El modelo rechazó la solicitud: {block_reason}")

        parsed = response.parsed
        if parsed is None:
            raise AIEngineError("El modelo no devolvió una salida estructurada válida")

        return parsed
