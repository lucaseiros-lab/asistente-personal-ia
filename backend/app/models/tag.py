import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EntityType

if TYPE_CHECKING:
    from app.models.user import User


class Tag(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6B7280", nullable=False)

    owner: Mapped["User"] = relationship(back_populates="tags")


class EntityTag(Base):
    """Asociación polimórfica entre etiquetas y cualquier entidad del sistema."""

    __tablename__ = "entity_tags"

    tag_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type"), primary_key=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    tag: Mapped["Tag"] = relationship()
