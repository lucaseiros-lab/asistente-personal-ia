from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.memory.conversational import (
    MESSAGES_TO_KEEP_AFTER_SUMMARY,
    SUMMARIZE_THRESHOLD,
    ConversationalMemoryService,
)
from app.memory.semantic import SemanticMemoryService
from app.memory.structured import build_context_snapshot
from app.models.conversation import Conversation
from app.models.enums import EntityType, MessageRole, PriorityLevel, ProjectStatus, TaskStatus
from app.models.message import Message
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
async def test_structured_snapshot_reflects_pending_work(db_session: AsyncSession, db_user: User) -> None:
    project = Project(
        user_id=db_user.id, name="Lanzamiento", status=ProjectStatus.ACTIVO, priority=PriorityLevel.ROJO
    )
    db_session.add(project)
    task = Task(
        user_id=db_user.id,
        title="Enviar propuesta",
        status=TaskStatus.PENDIENTE,
        priority=PriorityLevel.ROJO,
        due_date=datetime.now(UTC) + timedelta(hours=2),
    )
    db_session.add(task)
    await db_session.commit()

    snapshot = await build_context_snapshot(db_session, db_user.id)

    assert "Enviar propuesta" in snapshot
    assert "Lanzamiento" in snapshot


@pytest.mark.asyncio
async def test_structured_snapshot_empty_state(db_session: AsyncSession, db_user: User) -> None:
    snapshot = await build_context_snapshot(db_session, db_user.id)
    assert "no tiene información estructurada" in snapshot


@pytest.mark.asyncio
async def test_semantic_memory_orders_by_similarity(db_session: AsyncSession, db_user: User) -> None:
    dim = settings.OPENAI_EMBEDDING_DIMENSIONS
    vec_a = [1.0] + [0.0] * (dim - 1)
    vec_b = [0.0, 1.0] + [0.0] * (dim - 2)

    fake_embeddings = AsyncMock()
    fake_embeddings.embed_text = AsyncMock(side_effect=[vec_a, vec_b, vec_a])
    service = SemanticMemoryService(embedding_service=fake_embeddings)

    id_a, id_b = uuid4(), uuid4()
    await service.index(
        db_session, user_id=db_user.id, source_type=EntityType.PERSONA, source_id=id_a, content="Juan Pérez"
    )
    await service.index(
        db_session, user_id=db_user.id, source_type=EntityType.PERSONA, source_id=id_b, content="María López"
    )

    results = await service.search(db_session, user_id=db_user.id, query="juan", top_k=2)

    assert [r.content for r in results] == ["Juan Pérez", "María López"]


@pytest.mark.asyncio
async def test_semantic_memory_index_upserts_existing_entity(db_session: AsyncSession, db_user: User) -> None:
    dim = settings.OPENAI_EMBEDDING_DIMENSIONS
    fake_embeddings = AsyncMock()
    fake_embeddings.embed_text = AsyncMock(return_value=[0.5] * dim)
    service = SemanticMemoryService(embedding_service=fake_embeddings)

    entity_id = uuid4()
    first = await service.index(
        db_session, user_id=db_user.id, source_type=EntityType.TAREA, source_id=entity_id, content="v1"
    )
    second = await service.index(
        db_session, user_id=db_user.id, source_type=EntityType.TAREA, source_id=entity_id, content="v2"
    )

    assert first.id == second.id
    assert second.content == "v2"


async def _create_conversation_with_messages(
    db_session: AsyncSession, user: User, count: int
) -> Conversation:
    conversation = Conversation(user_id=user.id, title="Larga")
    db_session.add(conversation)
    await db_session.flush()
    for i in range(count):
        role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
        db_session.add(Message(conversation_id=conversation.id, role=role, content=f"mensaje {i}"))
    await db_session.commit()
    await db_session.refresh(conversation)
    return conversation


@pytest.mark.asyncio
async def test_maybe_compact_does_nothing_below_threshold(db_session: AsyncSession, db_user: User) -> None:
    conversation = await _create_conversation_with_messages(db_session, db_user, SUMMARIZE_THRESHOLD)

    fake_client = AsyncMock()
    service = ConversationalMemoryService(client=fake_client)
    await service.maybe_compact(db_session, conversation=conversation)

    fake_client.chat.completions.create.assert_not_called()
    assert conversation.summary is None


@pytest.mark.asyncio
async def test_maybe_compact_summarizes_when_over_threshold(
    db_session: AsyncSession, db_user: User
) -> None:
    conversation = await _create_conversation_with_messages(db_session, db_user, SUMMARIZE_THRESHOLD + 5)

    fake_summary_message = AsyncMock(content="Resumen: el usuario coordinó una reunión.")
    fake_choice = AsyncMock(message=fake_summary_message)
    fake_completion = AsyncMock(choices=[fake_choice])
    fake_client = AsyncMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_completion)

    service = ConversationalMemoryService(client=fake_client)
    await service.maybe_compact(db_session, conversation=conversation)

    fake_client.chat.completions.create.assert_called_once()
    assert conversation.summary == "Resumen: el usuario coordinó una reunión."

    # los mensajes más recientes siguen disponibles como turnos, no se borraron
    turns = await service.get_recent_turns(
        db_session, conversation_id=conversation.id, limit=MESSAGES_TO_KEEP_AFTER_SUMMARY
    )
    assert len(turns) == MESSAGES_TO_KEEP_AFTER_SUMMARY
