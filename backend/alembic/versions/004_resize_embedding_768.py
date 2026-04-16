"""resize_embedding_to_768

Revision ID: 004_resize_embedding_768
Revises: 003_add_chunk_editing
Create Date: 2026-04-16

Resizes the embedding column from vector(1536) to vector(768)
to match the gemini-embedding-001 model output (768 dimensions).
"""
from pgvector.sqlalchemy import Vector
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "004_resize_embedding_768"
down_revision: Union[str, Sequence[str], None] = "003_add_chunk_editing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Resize embedding column from 1536 to 768 dimensions."""
    # Drop the existing ivfflat index (can't alter with index present)
    op.drop_index("idx_embedding_cosine", table_name="chunks")

    # Delete existing chunks (embeddings are incompatible between models)
    # This is necessary because we can't cast vector(1536) to vector(768)
    op.execute("DELETE FROM chunks")

    # Alter column type
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768)")

    # Recreate the index
    op.execute(
        """
        CREATE INDEX idx_embedding_cosine ON chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    """Resize embedding column back from 768 to 1536 dimensions."""
    op.drop_index("idx_embedding_cosine", table_name="chunks")
    op.execute("DELETE FROM chunks")
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(1536)")
    op.execute(
        """
        CREATE INDEX idx_embedding_cosine ON chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
