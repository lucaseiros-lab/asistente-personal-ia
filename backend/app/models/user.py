from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.conversation import Conversation
    from app.models.document import Document
    from app.models.event import Event
    from app.models.expense import Expense
    from app.models.idea import Idea
    from app.models.person import Person
    from app.models.preference import Preference
    from app.models.project import Project
    from app.models.reminder import Reminder
    from app.models.tag import Tag
    from app.models.task import Task


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    people: Mapped[list["Person"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    companies: Mapped[list["Company"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    ideas: Mapped[list["Idea"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    preferences: Mapped[list["Preference"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
