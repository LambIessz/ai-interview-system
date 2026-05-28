import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.services.common.agent_tools import create_agent_tools

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是一个专业的 AI 面试系统助手，负责自动化处理简历分析、候选人画像提取、岗位匹配和面试会话创建。

你的工作流程：
1. 首先通过 read_resume 读取简历内容
2. 调用 extract_candidate_profile 从简历中提取候选人画像（姓名、技能、经验年限、学历、目标岗位）
3. 调用 match_job_template 根据候选人技能和目标岗位匹配合适的岗位模板
4. 调用 start_interview_session 创建面试会话配置

请严格按以上顺序执行，不要跳过任何步骤。每个步骤完成后，将结果传递给下一个步骤。

最终输出应为 JSON 格式，包含完整的候选人分析结果和面试配置。"""


def create_interview_agent(db: AsyncSession) -> AgentExecutor:
    """创建面试助手 Agent"""
    llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        base_url=settings.DEEPSEEK_BASE_URL,
        api_key=settings.DEEPSEEK_API_KEY,
        temperature=0.3,
    )

    tools = create_agent_tools(db)

    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
    )

    return agent_executor


async def run_resume_analysis_agent(
    db: AsyncSession,
    resume_id: int
) -> Dict:
    """通过 Agent 自动执行简历分析 → 画像提取 → 岗位匹配 → 面试配置"""
    agent_executor = create_interview_agent(db)

    try:
        result = await agent_executor.ainvoke({
            "input": f"请分析 resume_id={resume_id} 的简历，提取候选人画像，匹配岗位模板，并准备面试配置。"
        })
        return {
            "success": True,
            "output": result.get("output", ""),
            "intermediate_steps": result.get("intermediate_steps", [])
        }
    except Exception as e:
        logger.error(f"Agent 执行失败: {e}")
        return {
            "success": False,
            "output": str(e),
            "intermediate_steps": []
        }
