import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import PriorityLevel, ProjectStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.event import Event
    from app.models.expense import Expense
    from app.models.idea import Idea
    from app.models.task import Task
    from app.models.user import User


class Project(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, name="project_status"), default=ProjectStatus.ACTIVO, nullable=False
    )
    priority: Mapped[PriorityLevel] = mapped_column(
        SAEnum(PriorityLevel, name="priority_level"), default=PriorityLevel.VERDE, nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    company: Mapped["Company | None"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    events: Mapped[list["Event"]] = relationship(back_populates="project")
    ideas: Mapped[list["Idea"]] = relationship(back_populates="project")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="project")
