import io

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_transcription_service
from app.main import app


class _FakeTranscriptionService:
    async def transcribe(self, audio_bytes: bytes, *, filename: str, content_type: str) -> str:
        assert audio_bytes
        return "Recordame comprar café mañana"


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_transcribe_audio_returns_text(client: TestClient, auth_headers: dict[str, str]) -> None:
    app.dependency_overrides[get_transcription_service] = lambda: _FakeTranscriptionService()

    fake_audio = io.BytesIO(b"\x00\x01fake-audio-bytes")
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("audio.webm", fake_audio, "audio/webm")},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Recordame comprar café mañana"


def test_transcribe_empty_audio_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    app.dependency_overrides[get_transcription_service] = lambda: _FakeTranscriptionService()

    empty_audio = io.BytesIO(b"")
    response = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("audio.webm", empty_audio, "audio/webm")},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_transcribe_requires_authentication(client: TestClient) -> None:
    fake_audio = io.BytesIO(b"\x00\x01")
    response = client.post(
        "/api/v1/voice/transcribe", files={"file": ("audio.webm", fake_audio, "audio/webm")}
    )
    assert response.status_code == 401
