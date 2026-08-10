"""Pruebas end-to-end contra la API real de OpenAI (chat, embeddings, transcripción).

No corren en la suite normal ni en CI: hacen llamadas reales y pagas a
OpenAI. Se saltean automáticamente salvo que se invoquen explícitamente con
una `OPENAI_API_KEY` real y la variable `RUN_OPENAI_E2E_TESTS=1`:

    OPENAI_API_KEY=sk-... RUN_OPENAI_E2E_TESTS=1 pytest tests/test_openai_e2e.py -v

Para la prueba de transcripción no se versiona ningún archivo de audio: el
audio de entrada se genera en el momento con `client.audio.speech.create`
(texto a voz), también contra la API real, y ese resultado se usa como
insumo del propio `TranscriptionService`.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.ai.embeddings import EmbeddingService
from app.ai.engine import AIEngine
from app.ai.transcription import TranscriptionService
from app.core.config import settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_OPENAI_E2E_TESTS") != "1" or not settings.OPENAI_API_KEY,
    reason=(
        "Requiere OPENAI_API_KEY real y RUN_OPENAI_E2E_TESTS=1 "
        "(hace llamadas reales y pagas a la API de OpenAI)"
    ),
)


@pytest.mark.asyncio
async def test_ai_engine_interpret_message_against_real_api() -> None:
    engine = AIEngine()
    result = await engine.interpret_message(
        user_message="Recordame comprar café mañana a las 10am"
    )

    assert result.reply.strip()
    assert isinstance(result.needs_clarification, bool)
    assert result.actions, "se esperaba al menos una acción estructurada para un recordatorio claro"


@pytest.mark.asyncio
async def test_embedding_service_against_real_api() -> None:
    service = EmbeddingService()
    vector = await service.embed_text("El usuario tiene una reunión con Juan el lunes")

    assert len(vector) == settings.OPENAI_EMBEDDING_DIMENSIONS
    assert all(isinstance(value, float) for value in vector)


@pytest.mark.asyncio
async def test_transcription_service_against_real_api() -> None:
    from app.ai.client import get_openai_client

    speech = await get_openai_client().audio.speech.create(
        model="tts-1",
        voice="alloy",
        input="Recordame comprar café mañana",
        response_format="mp3",
    )

    transcription = TranscriptionService()
    text = await transcription.transcribe(
        speech.content, filename="e2e-sample.mp3", content_type="audio/mpeg"
    )

    assert text.strip()


def test_chat_endpoint_full_flow_against_real_api(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Recorre el flujo HTTP completo (auth -> conversación -> mensaje) sin
    overridear ninguna dependencia de IA: usa el Motor IA, la memoria
    semántica y la memoria conversacional reales, contra la API real."""
    conversation = client.post(
        "/api/v1/conversations", json={"title": "E2E OpenAI"}, headers=auth_headers
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = conversation.json()["id"]

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Recordame llamar al dentista mañana a las 9am", "input_type": "texto"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_message"]["content"].strip()
    assert isinstance(body["executed_actions"], list)
