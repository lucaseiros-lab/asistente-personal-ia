"""Punto de entrada único que combina las tres capas de memoria para el chat."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EmbeddingError
from app.core.logging import get_logger
from app.memory.semantic import SemanticMemoryService
from app.memory.structured import build_context_snapshot

logger = get_logger(__name__)


class MemoryContextBuilder:
    def __init__(self, semantic_service: SemanticMemoryService | None = None) -> None:
        self._semantic = semantic_service or SemanticMemoryService()

    async def build(self, db: AsyncSession, *, user_id: uuid.UUID, query: str) -> str:
        structured_context = await build_context_snapshot(db, user_id)

        try:
            semantic_context = await self._semantic.search_as_context(db, user_id=user_id, query=query)
        except EmbeddingError as exc:
            # La memoria semántica es una mejora sobre la estructurada, nunca un requisito:
            # si falla (red, cuota, etc.) el chat debe seguir funcionando igual.
            logger.error("semantic_memory_unavailable", error=str(exc))
            semantic_context = ""

        parts = [part for part in (structured_context, semantic_context) if part]
        return "\n\n".join(parts)
