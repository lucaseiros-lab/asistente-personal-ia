from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.client import get_openai_client
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
    OpenAI contra un JSON Schema estricto.
    """

    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or get_openai_client()

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

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in conversation_history or []:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": user_message})

        try:
            completion = await self._client.chat.completions.parse(
                model=settings.OPENAI_CHAT_MODEL,
                messages=messages,  # type: ignore[arg-type]
                response_format=AssistantInterpretation,
            )
        except Exception as exc:  # noqa: BLE001 - se traduce a un error de dominio
            logger.error("ai_engine_call_failed", error=str(exc))
            raise AIEngineError("Fallo al interpretar el mensaje con el Motor IA") from exc

        choice = completion.choices[0]
        if choice.message.refusal:
            raise AIEngineError(f"El modelo rechazó la solicitud: {choice.message.refusal}")

        parsed = choice.message.parsed
        if parsed is None:
            raise AIEngineError("El modelo no devolvió una salida estructurada válida")

        return parsed
