"""Memoria semántica: embeddings vectoriales sobre PostgreSQL + pgvector.

Permite indexar cualquier entidad (o fragmento de conversación) y recuperar
las más similares semánticamente a una consulta, para enriquecer el contexto
del Motor IA más allá de coincidencias exactas de texto.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingService
from app.core.config import settings
from app.models.enums import EntityType
from app.models.memory import MemoryEmbedding


class SemanticMemoryService:
    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self._embeddings = embedding_service or EmbeddingService()

    async def index(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        source_type: EntityType,
        source_id: uuid.UUID,
        content: str,
    ) -> MemoryEmbedding:
        """Crea o actualiza (upsert) el embedding de una entidad."""

        vector = await self._embeddings.embed_text(content)

        existing = await db.execute(
            select(MemoryEmbedding).where(
                MemoryEmbedding.source_type == source_type,
                MemoryEmbedding.source_id == source_id,
            )
        )
        record = existing.scalar_one_or_none()

        if record is not None:
            record.content = content
            record.embedding = vector
            record.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        else:
            record = MemoryEmbedding(
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                content=content,
                embedding=vector,
                embedding_model=settings.OPENAI_EMBEDDING_MODEL,
            )
            db.add(record)

        await db.commit()
        await db.refresh(record)
        return record

    async def forget(self, db: AsyncSession, *, source_type: EntityType, source_id: uuid.UUID) -> None:
        existing = await db.execute(
            select(MemoryEmbedding).where(
                MemoryEmbedding.source_type == source_type,
                MemoryEmbedding.source_id == source_id,
            )
        )
        record = existing.scalar_one_or_none()
        if record is not None:
            await db.delete(record)
            await db.commit()

    async def search(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
    ) -> list[MemoryEmbedding]:
        query_vector = await self._embeddings.embed_text(query)
        result = await db.execute(
            select(MemoryEmbedding)
            .where(MemoryEmbedding.user_id == user_id)
            .order_by(MemoryEmbedding.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def search_as_context(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
    ) -> str:
        matches = await self.search(db, user_id=user_id, query=query, top_k=top_k)
        if not matches:
            return ""
        lines = [f"- ({m.source_type.value}) {m.content}" for m in matches]
        return "Recuerdos relacionados encontrados por similitud semántica:\n" + "\n".join(lines)
