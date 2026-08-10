import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RevokedToken(Base):
    """Denylist de refresh tokens invalidados (logout, rotación).

    Solo los refresh tokens se revocan acá: los access tokens viven poco
    (30 min por defecto) y no se chequean contra esta tabla en cada request
    para no pagar una consulta extra por request autenticado.
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
