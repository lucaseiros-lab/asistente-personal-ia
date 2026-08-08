"""Agrega todos los modelos ORM para que Alembic y Base.metadata los detecten."""

from app.db.base import Base
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.event import Event
from app.models.expense import Expense
from app.models.idea import Idea
from app.models.memory import MemoryEmbedding
from app.models.message import Message
from app.models.person import Person
from app.models.preference import Preference
from app.models.project import Project
from app.models.reminder import Reminder
from app.models.tag import EntityTag, Tag
from app.models.task import Task
from app.models.user import User

__all__ = [
    "Base",
    "Company",
    "Conversation",
    "Document",
    "EntityTag",
    "Event",
    "Expense",
    "Idea",
    "MemoryEmbedding",
    "Message",
    "Person",
    "Preference",
    "Project",
    "Reminder",
    "Tag",
    "Task",
    "User",
]
