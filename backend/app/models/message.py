import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin
from app.models.enums import MessageInputType, MessageRole


class Message(UUIDMixin, Base):
    """Los mensajes son inmutables: solo tienen created_at, nunca se editan."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"), nullable=False)
    input_type: Mapped[MessageInputType] = mapped_column(
        SAEnum(MessageInputType, name="message_input_type"), default=MessageInputType.TEXTO, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted_actions: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Salida estructurada del Motor IA para este mensaje"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
