from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.n8n_client import N8nClient


@pytest.fixture(autouse=True)
def _webhook_token():
    original = settings.N8N_WEBHOOK_TOKEN
    settings.N8N_WEBHOOK_TOKEN = "test-webhook-token"
    yield
    settings.N8N_WEBHOOK_TOKEN = original


def test_inbound_webhook_rejects_missing_token(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/api/v1/automations/webhook",
        json={"user_email": unique_email, "source": "gmail", "title": "x", "content": "y"},
    )
    assert response.status_code == 401


def test_inbound_webhook_rejects_wrong_token(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/api/v1/automations/webhook",
        json={"user_email": unique_email, "source": "gmail", "title": "x", "content": "y"},
        headers={"x-webhook-token": "wrong"},
    )
    assert response.status_code == 401


def test_inbound_webhook_creates_document_for_existing_user(
    client: TestClient, auth_headers: dict[str, str], unique_email: str
) -> None:
    with patch("app.api.v1.endpoints.automations.SemanticMemoryService.index", new=AsyncMock()):
        response = client.post(
            "/api/v1/automations/webhook",
            json={
                "user_email": unique_email,
                "source": "gmail",
                "title": "Reunión con cliente",
                "content": "Nos vemos el jueves a las 10",
            },
            headers={"x-webhook-token": "test-webhook-token"},
        )
    assert response.status_code == 202
    document_id = response.json()["document_id"]

    documents = client.get("/api/v1/documents", headers=auth_headers).json()
    assert any(d["id"] == document_id and d["source"] == "gmail" for d in documents)


def test_inbound_webhook_unknown_user_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/automations/webhook",
        json={"user_email": "no-existe@example.com", "source": "gmail", "title": "x", "content": "y"},
        headers={"x-webhook-token": "test-webhook-token"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_n8n_client_is_noop_when_disabled() -> None:
    client = N8nClient(base_url="")
    assert client.enabled is False
    await client.dispatch_event("evento-creado", {"foo": "bar"})  # no debe lanzar ni hacer requests


@pytest.mark.asyncio
async def test_n8n_client_dispatches_when_enabled() -> None:
    client = N8nClient(base_url="http://n8n.local", token="secret")
    assert client.enabled is True

    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=fake_response)) as mock_post:
        await client.dispatch_event("evento-creado", {"foo": "bar"})

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://n8n.local/webhook/evento-creado"
    assert kwargs["json"] == {"foo": "bar"}
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
