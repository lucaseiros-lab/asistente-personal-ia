from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.ai.engine import AIEngine
from app.ai.schemas import ActionType, AssistantAction, AssistantInterpretation
from app.api.deps import get_action_executor, get_ai_engine, get_memory_context_builder
from app.core.config import settings
from app.main import app
from app.memory.orchestrator import MemoryContextBuilder
from app.memory.semantic import SemanticMemoryService
from app.models.enums import PriorityLevel
from app.services.action_executor import ActionExecutor


class _FakeAIEngine(AIEngine):
    def __init__(self, interpretation: AssistantInterpretation) -> None:
        self._interpretation = interpretation

    async def interpret_message(self, *, user_message, conversation_history=None, memory_context=""):
        return self._interpretation


def _fake_semantic_service() -> SemanticMemoryService:
    fake_embeddings = AsyncMock()
    fake_embeddings.embed_text = AsyncMock(return_value=[0.0] * settings.GEMINI_EMBEDDING_DIMENSIONS)
    return SemanticMemoryService(embedding_service=fake_embeddings)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_chat_message_creates_task_and_links_entities(client: TestClient, auth_headers: dict[str, str]) -> None:
    interpretation = AssistantInterpretation(
        reply="Listo, anoté la tarea de llamar a Juan.",
        priority=PriorityLevel.ROJO,
        actions=[
            AssistantAction(
                type=ActionType.CREAR_TAREA,
                title="Llamar a Juan",
                description="Seguimiento",
                priority=PriorityLevel.ROJO,
                due_date="2026-08-09T15:00:00",
                start_time=None,
                end_time=None,
                location=None,
                amount=None,
                currency=None,
                category=None,
                related_person_name="Juan",
                related_company_name=None,
                related_project_name="Lanzamiento",
                target_reference=None,
            )
        ],
        needs_clarification=False,
    )

    semantic_service = _fake_semantic_service()
    app.dependency_overrides[get_ai_engine] = lambda: _FakeAIEngine(interpretation)
    app.dependency_overrides[get_memory_context_builder] = lambda: MemoryContextBuilder(semantic_service)
    app.dependency_overrides[get_action_executor] = lambda: ActionExecutor(semantic_service)

    conversation = client.post(
        "/api/v1/conversations", json={"title": "Prueba"}, headers=auth_headers
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "Recordame llamar a Juan mañana para el proyecto Lanzamiento"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["priority"] == "rojo"
    assert len(data["executed_actions"]) == 1
    assert data["executed_actions"][0]["type"] == "crear_tarea"

    tasks = client.get("/api/v1/tasks", headers=auth_headers).json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Llamar a Juan"

    people = client.get("/api/v1/people", headers=auth_headers).json()
    assert any(p["full_name"] == "Juan" for p in people)

    projects = client.get("/api/v1/projects", headers=auth_headers).json()
    assert any(p["name"] == "Lanzamiento" for p in projects)

    messages = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages", headers=auth_headers
    ).json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_chat_message_without_actions_only_replies(client: TestClient, auth_headers: dict[str, str]) -> None:
    interpretation = AssistantInterpretation(
        reply="Hola, ¿en qué te puedo ayudar?",
        priority=PriorityLevel.VERDE,
        actions=[],
        needs_clarification=False,
    )
    semantic_service = _fake_semantic_service()
    app.dependency_overrides[get_ai_engine] = lambda: _FakeAIEngine(interpretation)
    app.dependency_overrides[get_memory_context_builder] = lambda: MemoryContextBuilder(semantic_service)
    app.dependency_overrides[get_action_executor] = lambda: ActionExecutor(semantic_service)

    conversation = client.post("/api/v1/conversations", json={}, headers=auth_headers).json()
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "hola"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["executed_actions"] == []


def test_conversation_endpoints_require_ownership(client: TestClient, auth_headers: dict[str, str]) -> None:
    import uuid

    response = client.get(f"/api/v1/conversations/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
