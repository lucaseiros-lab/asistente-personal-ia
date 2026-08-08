"""Memoria estructurada: la propia base relacional (Postgres) es la fuente de verdad.

Este módulo no almacena nada nuevo; construye una instantánea textual y
acotada de los datos estructurados más relevantes del usuario para dársela
como contexto al Motor IA antes de interpretar un mensaje.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PriorityLevel, ProjectStatus, ReminderStatus, TaskStatus
from app.models.event import Event
from app.models.project import Project
from app.models.preference import Preference
from app.models.reminder import Reminder
from app.models.task import Task

_PRIORITY_ORDER = {PriorityLevel.ROJO: 0, PriorityLevel.AMARILLO: 1, PriorityLevel.VERDE: 2}


async def build_context_snapshot(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Devuelve un resumen en texto plano del estado estructurado del usuario."""

    now = datetime.now(timezone.utc)
    sections: list[str] = []

    tasks_result = await db.execute(
        select(Task)
        .where(
            Task.user_id == user_id,
            Task.deleted_at.is_(None),
            Task.status.in_([TaskStatus.PENDIENTE, TaskStatus.EN_PROGRESO]),
        )
        .order_by(Task.due_date.asc().nulls_last())
        .limit(15)
    )
    tasks = sorted(tasks_result.scalars().all(), key=lambda t: _PRIORITY_ORDER[t.priority])[:10]
    if tasks:
        lines = [
            f"- [{t.priority.value}] {t.title}" + (f" (vence {t.due_date.isoformat()})" if t.due_date else "")
            for t in tasks
        ]
        sections.append("Tareas pendientes:\n" + "\n".join(lines))

    events_result = await db.execute(
        select(Event)
        .where(Event.user_id == user_id, Event.deleted_at.is_(None), Event.start_time >= now)
        .order_by(Event.start_time.asc())
        .limit(10)
    )
    events = list(events_result.scalars().all())
    if events:
        lines = [f"- {e.title}: {e.start_time.isoformat()}" + (f" en {e.location}" if e.location else "") for e in events]
        sections.append("Próximos eventos:\n" + "\n".join(lines))

    reminders_result = await db.execute(
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.deleted_at.is_(None),
            Reminder.status == ReminderStatus.PENDIENTE,
        )
        .order_by(Reminder.remind_at.asc())
        .limit(10)
    )
    reminders = list(reminders_result.scalars().all())
    if reminders:
        lines = [f"- {r.title}: {r.remind_at.isoformat()}" for r in reminders]
        sections.append("Recordatorios pendientes:\n" + "\n".join(lines))

    projects_result = await db.execute(
        select(Project)
        .where(
            Project.user_id == user_id,
            Project.deleted_at.is_(None),
            Project.status == ProjectStatus.ACTIVO,
        )
        .limit(10)
    )
    projects = list(projects_result.scalars().all())
    if projects:
        lines = [f"- [{p.priority.value}] {p.name}" for p in projects]
        sections.append("Proyectos activos:\n" + "\n".join(lines))

    prefs_result = await db.execute(select(Preference).where(Preference.user_id == user_id).limit(20))
    prefs = list(prefs_result.scalars().all())
    if prefs:
        lines = [f"- {p.key}: {p.value}" for p in prefs]
        sections.append("Preferencias conocidas del usuario:\n" + "\n".join(lines))

    if not sections:
        return "El usuario todavía no tiene información estructurada registrada."

    return "\n\n".join(sections)
