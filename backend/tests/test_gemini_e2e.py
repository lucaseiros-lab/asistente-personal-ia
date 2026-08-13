"""Pruebas end-to-end contra la API real de Gemini (chat, embeddings, transcripción).

No corren en la suite normal ni en CI: hacen llamadas reales (y sujetas a los
límites del free tier) contra la API de Gemini. Se saltean automáticamente
salvo que se invoquen explícitamente con una `GEMINI_API_KEY` real y la
variable `RUN_GEMINI_E2E_TESTS=1`:

    GEMINI_API_KEY=... RUN_GEMINI_E2E_TESTS=1 pytest tests/test_gemini_e2e.py -v

Para la prueba de transcripción no se versiona ningún archivo de audio: el
audio de entrada se genera en el momento con el modelo de texto-a-voz de
Gemini, también contra la API real, y ese resultado (un WAV armado en
memoria a partir del PCM crudo que devuelve el modelo) se usa como insumo
del propio `TranscriptionService`.
"""

import io
import os
import wave

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from app.ai.embeddings import EmbeddingService
from app.ai.engine import AIEngine
from app.ai.transcription import TranscriptionService
from app.core.config import settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_GEMINI_E2E_TESTS") != "1" or not settings.GEMINI_API_KEY,
    reason=(
        "Requiere GEMINI_API_KEY real y RUN_GEMINI_E2E_TESTS=1 "
        "(hace llamadas reales a la API de Gemini, sujetas al free tier)"
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

    assert len(vector) == settings.GEMINI_EMBEDDING_DIMENSIONS
    assert all(isinstance(value, float) for value in vector)


@pytest.mark.asyncio
async def test_transcription_service_against_real_api() -> None:
    from app.ai.client import get_ai_client

    speech = await get_ai_client().aio.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents="Recordame comprar café mañana",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                )
            ),
        ),
    )
    pcm_data = speech.candidates[0].content.parts[0].inline_data.data

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_data)

    transcription = TranscriptionService()
    text = await transcription.transcribe(
        wav_buffer.getvalue(), filename="e2e-sample.wav", content_type="audio/wav"
    )

    assert text.strip()


def test_chat_endpoint_full_flow_against_real_api(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Recorre el flujo HTTP completo (auth -> conversación -> mensaje) sin
    overridear ninguna dependencia de IA: usa el Motor IA, la memoria
    semántica y la memoria conversacional reales, contra la API real."""
    conversation = client.post(
        "/api/v1/conversations", json={"title": "E2E Gemini"}, headers=auth_headers
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
