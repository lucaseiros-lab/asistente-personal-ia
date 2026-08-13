"""ajustar dimensión de embeddings a Gemini (768)

Revision ID: 11ee20844774
Revises: fca0430c1e9a
Create Date: 2026-08-13 23:20:00.000000

"""
from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa

from alembic import op

revision: str = '11ee20844774'
down_revision: str | None = 'fca0430c1e9a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_KWARGS = {
    "postgresql_using": "hnsw",
    "postgresql_with": {"m": 16, "ef_construction": 64},
    "postgresql_ops": {"embedding": "vector_cosine_ops"},
}


def upgrade() -> None:
    op.drop_index("ix_memory_embeddings_vector", table_name="memory_embeddings", **_INDEX_KWARGS)
    op.execute("TRUNCATE TABLE memory_embeddings")
    op.alter_column(
        "memory_embeddings",
        "embedding",
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
        postgresql_using="embedding::vector(768)",
    )
    op.create_index("ix_memory_embeddings_vector", "memory_embeddings", ["embedding"], unique=False, **_INDEX_KWARGS)


def downgrade() -> None:
    op.drop_index("ix_memory_embeddings_vector", table_name="memory_embeddings", **_INDEX_KWARGS)
    op.execute("TRUNCATE TABLE memory_embeddings")
    op.alter_column(
        "memory_embeddings",
        "embedding",
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=1536),
        postgresql_using="embedding::vector(1536)",
    )
    op.create_index("ix_memory_embeddings_vector", "memory_embeddings", ["embedding"], unique=False, **_INDEX_KWARGS)
