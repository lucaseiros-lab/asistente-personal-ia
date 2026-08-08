import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import EntityType, ReminderStatus

if TYPE_CHECKING:
    from app.models.user import User


class Reminder(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "reminders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[ReminderStatus] = mapped_column(
        SAEnum(ReminderStatus, name="reminder_status"), default=ReminderStatus.PENDIENTE, nullable=False
    )
    related_entity_type: Mapped[EntityType | None] = mapped_column(
        SAEnum(EntityType, name="entity_type"), nullable=True
    )
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="reminders")
