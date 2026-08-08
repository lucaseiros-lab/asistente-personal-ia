import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ActionType, AssistantAction
from app.core.logging import get_logger
from app.integrations.n8n_client import N8nClient
from app.memory.semantic import SemanticMemoryService
from app.models.company import Company
from app.models.enums import EntityType, PriorityLevel, TaskStatus
from app.models.event import Event
from app.models.expense import Expense
from app.models.idea import Idea
from app.models.person import Person
from app.models.project import Project
from app.models.reminder import Reminder
from app.models.task import Task

logger = get_logger(__name__)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        logger.warning("action_executor_invalid_datetime", value=value)
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


@dataclass(frozen=True, slots=True)
class ExecutedAction:
    type: ActionType
    entity_type: EntityType
    entity_id: uuid.UUID
    title: str


class ActionExecutor:
    """Traduce cada `AssistantAction` estructurada en cambios reales sobre la base.

    Es la única capa autorizada a escribir en el modelo de datos a partir de
    una interpretación de la IA: nunca se ejecuta SQL ni se modifica estado
    directamente desde el motor de IA.
    """

    def __init__(
        self,
        semantic_memory: SemanticMemoryService | None = None,
        n8n_client: N8nClient | None = None,
    ) -> None:
        self._semantic = semantic_memory or SemanticMemoryService()
        self._n8n = n8n_client or N8nClient()

    async def execute(
        self, db: AsyncSession, *, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        handler = self._HANDLERS[action.type]
        return await handler(self, db, user_id, action)

    async def _resolve_project_id(
        self, db: AsyncSession, user_id: uuid.UUID, name: str | None
    ) -> uuid.UUID | None:
        if not name:
            return None
        project = await self._get_or_create_project(db, user_id, name, None)
        return project.id

    async def _touch_related_entities(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> None:
        """Registra en memoria estructurada/semántica a las personas y empresas mencionadas.

        No siempre existe una columna FK directa (ej. tareas no tienen person_id), pero
        toda mención debe quedar recordada: se aplica el principio de no perder información.
        """
        if action.related_person_name:
            await self._get_or_create_person(db, user_id, action.related_person_name)
        if action.related_company_name:
            await self._get_or_create_company(db, user_id, action.related_company_name)

    async def _get_or_create_person(self, db: AsyncSession, user_id: uuid.UUID, name: str) -> Person:
        result = await db.execute(
            select(Person).where(Person.user_id == user_id, Person.full_name == name)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            obj = Person(user_id=user_id, full_name=name)
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            await self._index(db, user_id, EntityType.PERSONA, obj.id, f"Persona: {name}")
        return obj

    async def _get_or_create_company(self, db: AsyncSession, user_id: uuid.UUID, name: str) -> Company:
        result = await db.execute(
            select(Company).where(Company.user_id == user_id, Company.name == name)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            obj = Company(user_id=user_id, name=name)
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            await self._index(db, user_id, EntityType.EMPRESA, obj.id, f"Empresa: {name}")
        return obj

    async def _get_or_create_project(
        self, db: AsyncSession, user_id: uuid.UUID, name: str, priority: PriorityLevel | None
    ) -> Project:
        result = await db.execute(
            select(Project).where(Project.user_id == user_id, Project.name == name)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            obj = Project(user_id=user_id, name=name, priority=priority or PriorityLevel.VERDE)
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            await self._index(db, user_id, EntityType.PROYECTO, obj.id, f"Proyecto: {name}")
        return obj

    async def _index(
        self, db: AsyncSession, user_id: uuid.UUID, entity_type: EntityType, entity_id: uuid.UUID, content: str
    ) -> None:
        try:
            await self._semantic.index(
                db, user_id=user_id, source_type=entity_type, source_id=entity_id, content=content
            )
        except Exception as exc:  # noqa: BLE001 - indexar no debe romper la acción principal
            logger.error("semantic_index_failed", error=str(exc), entity_type=entity_type.value)

    async def _create_task(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        project_id = await self._resolve_project_id(db, user_id, action.related_project_name)
        await self._touch_related_entities(db, user_id, action)
        obj = Task(
            user_id=user_id,
            project_id=project_id,
            title=action.title,
            description=action.description,
            priority=action.priority or PriorityLevel.VERDE,
            due_date=_parse_datetime(action.due_date),
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        await self._index(db, user_id, EntityType.TAREA, obj.id, f"Tarea: {obj.title}. {obj.description or ''}")
        if obj.priority == PriorityLevel.ROJO:
            await self._n8n.dispatch_event(
                "tarea-urgente",
                {
                    "user_id": str(user_id),
                    "task_id": str(obj.id),
                    "title": obj.title,
                    "due_date": obj.due_date.isoformat() if obj.due_date else None,
                },
            )
        return ExecutedAction(action.type, EntityType.TAREA, obj.id, obj.title)

    async def _complete_task(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        reference = action.target_reference or action.title
        result = await db.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status != TaskStatus.COMPLETADA,
                Task.title.ilike(f"%{reference}%"),
            )
        )
        obj = result.scalars().first()
        if obj is None:
            obj = Task(
                user_id=user_id,
                title=action.title,
                status=TaskStatus.COMPLETADA,
                completed_at=datetime.now(UTC),
            )
            db.add(obj)
        else:
            obj.status = TaskStatus.COMPLETADA
            obj.completed_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(obj)
        return ExecutedAction(action.type, EntityType.TAREA, obj.id, obj.title)

    async def _create_event(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        project_id = await self._resolve_project_id(db, user_id, action.related_project_name)
        await self._touch_related_entities(db, user_id, action)
        start_time = _parse_datetime(action.start_time) or datetime.now(UTC)
        obj = Event(
            user_id=user_id,
            project_id=project_id,
            title=action.title,
            description=action.description,
            location=action.location,
            start_time=start_time,
            end_time=_parse_datetime(action.end_time),
            priority=action.priority or PriorityLevel.AMARILLO,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        await self._index(db, user_id, EntityType.EVENTO, obj.id, f"Evento: {obj.title}. {obj.description or ''}")
        await self._n8n.dispatch_event(
            "evento-creado",
            {
                "user_id": str(user_id),
                "event_id": str(obj.id),
                "title": obj.title,
                "start_time": obj.start_time.isoformat(),
                "location": obj.location,
            },
        )
        return ExecutedAction(action.type, EntityType.EVENTO, obj.id, obj.title)

    async def _create_reminder(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        remind_at = _parse_datetime(action.due_date) or datetime.now(UTC)
        obj = Reminder(user_id=user_id, title=action.title, remind_at=remind_at)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return ExecutedAction(action.type, EntityType.RECORDATORIO, obj.id, obj.title)

    async def _create_idea(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        project_id = await self._resolve_project_id(db, user_id, action.related_project_name)
        await self._touch_related_entities(db, user_id, action)
        obj = Idea(
            user_id=user_id,
            project_id=project_id,
            title=action.title,
            content=action.description,
            priority=action.priority or PriorityLevel.VERDE,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        await self._index(db, user_id, EntityType.IDEA, obj.id, f"Idea: {obj.title}. {obj.content or ''}")
        return ExecutedAction(action.type, EntityType.IDEA, obj.id, obj.title)

    async def _create_expense(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        project_id = await self._resolve_project_id(db, user_id, action.related_project_name)
        await self._touch_related_entities(db, user_id, action)
        obj = Expense(
            user_id=user_id,
            project_id=project_id,
            description=action.title,
            amount=action.amount or 0,
            currency=action.currency or "ARS",
            category=action.category,
            notes=action.description,
            expense_date=date.today(),
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return ExecutedAction(action.type, EntityType.GASTO, obj.id, obj.description)

    async def _create_person_action(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        obj = await self._get_or_create_person(db, user_id, action.title)
        return ExecutedAction(action.type, EntityType.PERSONA, obj.id, obj.full_name)

    async def _create_company_action(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        obj = await self._get_or_create_company(db, user_id, action.title)
        return ExecutedAction(action.type, EntityType.EMPRESA, obj.id, obj.name)

    async def _create_project_action(
        self, db: AsyncSession, user_id: uuid.UUID, action: AssistantAction
    ) -> ExecutedAction:
        obj = await self._get_or_create_project(db, user_id, action.title, action.priority)
        return ExecutedAction(action.type, EntityType.PROYECTO, obj.id, obj.name)

    _HANDLERS: dict = {}


ActionExecutor._HANDLERS = {
    ActionType.CREAR_TAREA: ActionExecutor._create_task,
    ActionType.COMPLETAR_TAREA: ActionExecutor._complete_task,
    ActionType.CREAR_EVENTO: ActionExecutor._create_event,
    ActionType.CREAR_RECORDATORIO: ActionExecutor._create_reminder,
    ActionType.CREAR_IDEA: ActionExecutor._create_idea,
    ActionType.CREAR_GASTO: ActionExecutor._create_expense,
    ActionType.CREAR_PERSONA: ActionExecutor._create_person_action,
    ActionType.CREAR_EMPRESA: ActionExecutor._create_company_action,
    ActionType.CREAR_PROYECTO: ActionExecutor._create_project_action,
}
