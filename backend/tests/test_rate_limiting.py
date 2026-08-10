import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.ai.schemas import AssistantInterpretation
from app.api.deps import (
    get_action_executor,
    get_ai_engine,
    get_conversational_memory,
    get_memory_context_builder,
)
from app.main import app
from app.memory.conversational import ConversationalMemoryService
from app.memory.orchestrator import MemoryContextBuilder
from app.memory.semantic import SemanticMemoryService
from app.models.enums import PriorityLevel
from app.services.action_executor import ActionExecutor


def test_login_rate_limit_returns_429_after_threshold(client: TestClient, unique_email: str) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "password123", "full_name": "RL"},
    )
    payload = {"email": unique_email, "password": "password123"}

    for _ in range(10):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200

    blocked = client.post("/api/v1/auth/login", json=payload)
    assert blocked.status_code == 429


def test_register_rate_limit_returns_429_after_threshold(client: TestClient) -> None:
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"rl-{uuid.uuid4()}@example.com",
                "password": "password123",
                "full_name": "RL",
            },
        )
        assert response.status_code == 201

    blocked = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"rl-{uuid.uuid4()}@example.com",
            "password": "password123",
            "full_name": "RL",
        },
    )
    assert blocked.status_code == 429


class _FakeAIEngine:
    async def interpret_message(self, **kwargs) -> AssistantInterpretation:
        return AssistantInterpretation(
            reply="ok", priority=PriorityLevel.VERDE, actions=[], needs_clarification=False
        )


def _fake_semantic_service() -> SemanticMemoryService:
    fake_embeddings = AsyncMock()
    fake_embeddings.embed_text = AsyncMock(return_value=[0.0] * 1536)
    return SemanticMemoryService(embedding_service=fake_embeddings)


def _fake_openai_client_for_summaries() -> AsyncMock:
    """Cliente OpenAI simulado que responde con un resumen de texto plano,
    para cuando `maybe_compact` se dispara durante el test (>30 mensajes)."""
    message = AsyncMock(content="resumen de prueba")
    choice = AsyncMock(message=message)
    completion = AsyncMock(choices=[choice])
    fake_client = AsyncMock()
    fake_client.chat.completions.create = AsyncMock(return_value=completion)
    return fake_client


def test_chat_message_rate_limit_returns_429_after_threshold(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    semantic_service = _fake_semantic_service()
    app.dependency_overrides[get_ai_engine] = lambda: _FakeAIEngine()
    app.dependency_overrides[get_memory_context_builder] = lambda: MemoryContextBuilder(semantic_service)
    app.dependency_overrides[get_action_executor] = lambda: ActionExecutor(semantic_service)
    app.dependency_overrides[get_conversational_memory] = lambda: ConversationalMemoryService(
        client=_fake_openai_client_for_summaries()
    )
    try:
        conversation = client.post("/api/v1/conversations", json={}, headers=auth_headers).json()
        for _ in range(20):
            response = client.post(
                f"/api/v1/conversations/{conversation['id']}/messages",
                json={"content": "hola"},
                headers=auth_headers,
            )
            assert response.status_code == 200

        blocked = client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            json={"content": "hola"},
            headers=auth_headers,
        )
        assert blocked.status_code == 429
    finally:
        app.dependency_overrides.clear()
