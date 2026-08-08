from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.engine import AIEngine, AIEngineError, ChatTurn
from app.ai.schemas import ActionType, AssistantAction, AssistantInterpretation
from app.models.enums import PriorityLevel


def _make_interpretation() -> AssistantInterpretation:
    return AssistantInterpretation(
        reply="Listo, anoté la tarea.",
        priority=PriorityLevel.AMARILLO,
        actions=[
            AssistantAction(
                type=ActionType.CREAR_TAREA,
                title="Llamar a Juan",
                description=None,
                priority=PriorityLevel.AMARILLO,
                due_date=None,
                start_time=None,
                end_time=None,
                location=None,
                amount=None,
                currency=None,
                category=None,
                related_person_name="Juan",
                related_company_name=None,
                related_project_name=None,
                target_reference=None,
            )
        ],
        needs_clarification=False,
    )


def _fake_client(parsed: AssistantInterpretation | None, refusal: str | None = None) -> MagicMock:
    fake_client = MagicMock()
    message = MagicMock(parsed=parsed, refusal=refusal)
    choice = MagicMock(message=message)
    completion = MagicMock(choices=[choice])
    fake_client.chat.completions.parse = AsyncMock(return_value=completion)
    return fake_client


@pytest.mark.asyncio
async def test_interpret_message_returns_parsed_structured_output() -> None:
    expected = _make_interpretation()
    fake_client = _fake_client(parsed=expected)
    engine = AIEngine(client=fake_client)

    result = await engine.interpret_message(
        user_message="Recordame llamar a Juan",
        conversation_history=[ChatTurn(role="user", content="hola")],
    )

    assert result == expected
    call_kwargs = fake_client.chat.completions.parse.call_args.kwargs
    assert call_kwargs["response_format"] is AssistantInterpretation
    assert call_kwargs["messages"][0]["role"] == "system"
    assert call_kwargs["messages"][-1] == {"role": "user", "content": "Recordame llamar a Juan"}


@pytest.mark.asyncio
async def test_interpret_message_includes_memory_context_in_system_prompt() -> None:
    fake_client = _fake_client(parsed=_make_interpretation())
    engine = AIEngine(client=fake_client)

    await engine.interpret_message(user_message="hola", memory_context="Tareas pendientes: ninguna")

    system_message = fake_client.chat.completions.parse.call_args.kwargs["messages"][0]["content"]
    assert "Tareas pendientes: ninguna" in system_message


@pytest.mark.asyncio
async def test_interpret_message_raises_on_refusal() -> None:
    fake_client = _fake_client(parsed=None, refusal="No puedo ayudar con eso")
    engine = AIEngine(client=fake_client)

    with pytest.raises(AIEngineError, match="rechazó"):
        await engine.interpret_message(user_message="algo raro")


@pytest.mark.asyncio
async def test_interpret_message_raises_when_parsed_is_none() -> None:
    fake_client = _fake_client(parsed=None, refusal=None)
    engine = AIEngine(client=fake_client)

    with pytest.raises(AIEngineError, match="salida estructurada"):
        await engine.interpret_message(user_message="algo")


@pytest.mark.asyncio
async def test_interpret_message_wraps_api_errors() -> None:
    fake_client = MagicMock()
    fake_client.chat.completions.parse = AsyncMock(side_effect=RuntimeError("boom"))
    engine = AIEngine(client=fake_client)

    with pytest.raises(AIEngineError):
        await engine.interpret_message(user_message="algo")
