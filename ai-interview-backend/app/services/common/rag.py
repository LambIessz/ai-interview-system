import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.common.embedding import get_embedding
from app.models.question_bank import QuestionBank

logger = logging.getLogger(__name__)


async def retrieve_questions(
    db: AsyncSession,
    skills: List[str],
    job_type: str,
    limit: int = 10
) -> List[Dict]:
    """根据技能列表和岗位类型，通过向量相似度检索相关题目"""
    query_text = f"{job_type} {' '.join(skills)}"

    try:
        query_embedding = await get_embedding(query_text)
    except Exception as e:
        logger.error(f"获取查询向量失败: {e}")
        return []

    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

    sql = text(
        "SELECT id, question_text, category, difficulty, reference_answer, key_points, "
        "1 - (embedding <=> :embedding) AS similarity "
        "FROM question_bank "
        "WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> :embedding "
        "LIMIT :limit"
    )

    try:
        result = await db.execute(
            sql,
            {"embedding": embedding_str, "limit": limit}
        )
        rows = result.fetchall()

        questions = []
        for row in rows:
            questions.append({
                "id": row.id,
                "question_text": row.question_text,
                "category": row.category,
                "difficulty": row.difficulty,
                "reference_answer": row.reference_answer,
                "key_points": row.key_points,
                "similarity": float(row.similarity) if row.similarity is not None else 0.0
            })
        return questions
    except Exception as e:
        logger.error(f"向量检索失败: {e}")
        return []


async def fallback_retrieve_by_category(
    db: AsyncSession,
    categories: Optional[List[str]] = None,
    limit: int = 10
) -> List[Dict]:
    """当向量检索不可用时，按分类降级检索题目"""
    from sqlalchemy import select

    query = select(QuestionBank)
    if categories:
        query = query.where(QuestionBank.category.in_(categories))
    query = query.limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": row.id,
            "question_text": row.question_text,
            "category": row.category,
            "difficulty": row.difficulty,
            "reference_answer": row.reference_answer,
            "key_points": row.key_points,
        }
        for row in rows
    ]
