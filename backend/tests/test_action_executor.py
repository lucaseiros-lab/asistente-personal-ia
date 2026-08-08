from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ActionType, AssistantAction
from app.memory.semantic import SemanticMemoryService
from app.models.enums import EntityType, PriorityLevel, TaskStatus
from app.models.person import Person
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.services.action_executor import ActionExecutor


def _action(**overrides) -> AssistantAction:
    defaults = dict(
        type=ActionType.CREAR_TAREA,
        title="Tarea de prueba",
        description=None,
        priority=PriorityLevel.VERDE,
        due_date=None,
        start_time=None,
        end_time=None,
        location=None,
        amount=None,
        currency=None,
        category=None,
        related_person_name=None,
        related_company_name=None,
        related_project_name=None,
        target_reference=None,
    )
    defaults.update(overrides)
    return AssistantAction(**defaults)


@pytest.fixture
def executor() -> ActionExecutor:
    fake_embeddings = AsyncMock()
    fake_embeddings.embed_text = AsyncMock(return_value=[0.0] * 1536)
    return ActionExecutor(semantic_memory=SemanticMemoryService(embedding_service=fake_embeddings))


@pytest.mark.asyncio
async def test_create_task_resolves_project_and_person(
    db_session: AsyncSession, db_user: User, executor: ActionExecutor
) -> None:
    action = _action(
        type=ActionType.CREAR_TAREA,
        title="Llamar a Juan",
        related_person_name="Juan",
        related_project_name="Lanzamiento",
        priority=PriorityLevel.ROJO,
    )

    result = await executor.execute(db_session, user_id=db_user.id, action=action)

    assert result.entity_type == EntityType.TAREA
    assert result.title == "Llamar a Juan"

    task = (await db_session.execute(select(Task).where(Task.id == result.entity_id))).scalar_one()
    assert task.priority == PriorityLevel.ROJO
    assert task.project_id is not None

    project = (await db_session.execute(select(Project).where(Project.id == task.project_id))).scalar_one()
    assert project.name == "Lanzamiento"

    person = (
        await db_session.execute(select(Person).where(Person.user_id == db_user.id))
    ).scalar_one()
    assert person.full_name == "Juan"


@pytest.mark.asyncio
async def test_create_task_is_idempotent_for_same_project_name(
    db_session: AsyncSession, db_user: User, executor: ActionExecutor
) -> None:
    action1 = _action(related_project_name="Proyecto X")
    action2 = _action(title="Otra tarea", related_project_name="Proyecto X")

    await executor.execute(db_session, user_id=db_user.id, action=action1)
    await executor.execute(db_session, user_id=db_user.id, action=action2)

    projects = (
        await db_session.execute(select(Project).where(Project.user_id == db_user.id, Project.name == "Proyecto X"))
    ).scalars().all()
    assert len(projects) == 1


@pytest.mark.asyncio
async def test_complete_task_matches_existing_task_by_title(
    db_session: AsyncSession, db_user: User, executor: ActionExecutor
) -> None:
    create_result = await executor.execute(
        db_session, user_id=db_user.id, action=_action(title="Comprar café")
    )

    complete_action = _action(
        type=ActionType.COMPLETAR_TAREA, title="completar", target_reference="café"
    )
    complete_result = await executor.execute(db_session, user_id=db_user.id, action=complete_action)

    assert complete_result.entity_id == create_result.entity_id
    task = (await db_session.execute(select(Task).where(Task.id == create_result.entity_id))).scalar_one()
    assert task.status == TaskStatus.COMPLETADA
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_complete_task_creates_placeholder_when_no_match(
    db_session: AsyncSession, db_user: User, executor: ActionExecutor
) -> None:
    action = _action(
        type=ActionType.COMPLETAR_TAREA, title="Tarea inexistente", target_reference="no existe"
    )
    result = await executor.execute(db_session, user_id=db_user.id, action=action)

    task = (await db_session.execute(select(Task).where(Task.id == result.entity_id))).scalar_one()
    assert task.status == TaskStatus.COMPLETADA


@pytest.mark.asyncio
async def test_create_person_action_is_find_or_create(
    db_session: AsyncSession, db_user: User, executor: ActionExecutor
) -> None:
    action = _action(type=ActionType.CREAR_PERSONA, title="Ana García")

    first = await executor.execute(db_session, user_id=db_user.id, action=action)
    second = await executor.execute(db_session, user_id=db_user.id, action=action)

    assert first.entity_id == second.entity_id
