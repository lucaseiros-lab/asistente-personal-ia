import uuid
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """CRUD genérico para entidades propiedad de un usuario (`user_id`).

    Aplica soft-delete automáticamente cuando el modelo lo soporta, para
    cumplir el principio de que toda acción debe poder deshacerse.
    """

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model
        self.soft_delete = hasattr(model, "deleted_at")

    def _base_query(self, user_id: uuid.UUID):
        query = select(self.model).where(self.model.user_id == user_id)
        if self.soft_delete:
            query = query.where(self.model.deleted_at.is_(None))
        return query

    async def list(
        self, db: AsyncSession, *, user_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[ModelType]:
        query = (
            self._base_query(user_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, *, user_id: uuid.UUID, id: uuid.UUID) -> ModelType | None:
        query = self._base_query(user_id).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, user_id: uuid.UUID, data: CreateSchemaType) -> ModelType:
        obj = self.model(user_id=user_id, **data.model_dump())
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def update(self, db: AsyncSession, *, obj: ModelType, data: UpdateSchemaType) -> ModelType:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, *, obj: ModelType) -> None:
        if self.soft_delete:
            obj.deleted_at = datetime.now(UTC)
            await db.commit()
        else:
            await db.delete(obj)
            await db.commit()
