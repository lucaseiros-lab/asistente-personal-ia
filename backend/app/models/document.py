import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import DocumentSourceType, EntityType

if TYPE_CHECKING:
    from app.models.user import User


class Document(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[DocumentSourceType] = mapped_column(
        SAEnum(DocumentSourceType, name="document_source_type"),
        default=DocumentSourceType.UPLOAD,
        nullable=False,
    )
    extracted_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Texto extraído para indexado en memoria semántica"
    )
    related_entity_type: Mapped[EntityType | None] = mapped_column(
        SAEnum(EntityType, name="entity_type"), nullable=True
    )
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="documents")
