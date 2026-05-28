import logging
from typing import List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

DASHSCOPE_EMBEDDING_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"


async def get_embedding(text: str) -> List[float]:
    """调用 DashScope Embedding API 获取文本向量"""
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.DASHSCOPE_EMBEDDING_MODEL,
        "input": {"texts": [text]},
        "parameters": {"text_type": "document"}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(DASHSCOPE_EMBEDDING_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            embedding = data["output"]["embeddings"][0]["embedding"]
            return embedding
        except httpx.HTTPStatusError as e:
            logger.error(f"DashScope Embedding API 请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"DashScope Embedding API 响应解析失败: {e}")
            raise
        except Exception as e:
            logger.error(f"DashScope Embedding API 调用异常: {e}")
            raise
