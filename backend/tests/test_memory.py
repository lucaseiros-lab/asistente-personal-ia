from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.memory.semantic import SemanticMemoryService
from app.memory.structured import build_context_snapshot
from app.models.enums import EntityType, PriorityLevel, ProjectStatus, TaskStatus
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
