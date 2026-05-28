from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from .base import BaseModel
from app.core.config import settings


def _pgvector_available() -> bool:
    try:
        from pgvector.sqlalchemy import Vector
        return settings.PGVECTOR_ENABLED
    except ImportError:
        return False


HAS_PGVECTOR = _pgvector_available()


class QuestionBank(BaseModel):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    difficulty = Column(String(20), default="medium")
    reference_answer = Column(Text, nullable=True)
    key_points = Column(JSONB, nullable=True)

    if HAS_PGVECTOR:
        from pgvector.sqlalchemy import Vector
        embedding = Column(Vector(1536), nullable=True)
