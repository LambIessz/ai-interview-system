"""add_pgvector_and_question_bank

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-28 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger("alembic")

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_pgvector() -> bool:
    try:
        conn = op.get_bind()
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            sa.text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        return True
    except Exception:
        return False


def upgrade() -> None:
    has_vector = _has_pgvector()
    if has_vector:
        logger.info("pgvector 扩展可用，将启用向量检索功能")
    else:
        logger.warning("pgvector 扩展不可用，题库表将不包含向量列")

    op.create_table(
        'question_bank',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('reference_answer', sa.Text(), nullable=True),
        sa.Column('key_points', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_question_bank_id'), 'question_bank', ['id'], unique=False)
    op.create_index(op.f('ix_question_bank_category'), 'question_bank', ['category'], unique=False)

    if has_vector:
        op.add_column('question_bank', sa.Column('embedding', postgresql.VECTOR(1536), nullable=True))
        op.create_index(
            'ix_question_bank_embedding',
            'question_bank',
            ['embedding'],
            unique=False,
            postgresql_using='ivfflat',
            postgresql_with={'lists': 10},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        )


def downgrade() -> None:
    try:
        op.drop_index('ix_question_bank_embedding', table_name='question_bank', postgresql_using='ivfflat')
    except Exception:
        pass
    op.drop_index(op.f('ix_question_bank_category'), table_name='question_bank')
    op.drop_index(op.f('ix_question_bank_id'), table_name='question_bank')
    op.drop_table('question_bank')
