import json
import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

JOB_TEMPLATES = [
    {
        "id": "backend_dev",
        "name": "后端开发工程师",
        "keywords": ["Python", "Java", "Go", "数据库", "API", "微服务", "Redis"],
        "interview_focus": ["数据结构与算法", "数据库设计", "系统设计", "API设计", "并发编程"],
        "difficulty_level": "medium",
        "recommended_question_categories": ["Python", "数据库", "Redis", "系统设计", "数据结构与算法"]
    },
    {
        "id": "frontend_dev",
        "name": "前端开发工程师",
        "keywords": ["JavaScript", "React", "Vue", "CSS", "HTML", "TypeScript", "Webpack"],
        "interview_focus": ["JavaScript基础", "框架原理", "CSS布局", "性能优化", "工程化"],
        "difficulty_level": "medium",
        "recommended_question_categories": ["JavaScript", "React/Vue", "CSS", "计算机网络"]
    },
    {
        "id": "fullstack_dev",
        "name": "全栈开发工程师",
        "keywords": ["Python", "JavaScript", "React", "数据库", "Docker", "API"],
        "interview_focus": ["前后端技术栈", "数据库设计", "系统架构", "DevOps", "项目经验"],
        "difficulty_level": "medium",
        "recommended_question_categories": ["Python", "JavaScript", "数据库", "系统设计", "DevOps"]
    },
    {
        "id": "data_engineer",
        "name": "数据工程师",
        "keywords": ["Python", "SQL", "Spark", "Hadoop", "ETL", "数据仓库"],
        "interview_focus": ["SQL能力", "ETL流程", "大数据框架", "数据建模", "Python编程"],
        "difficulty_level": "hard",
        "recommended_question_categories": ["Python", "数据库", "系统设计", "数据结构与算法"]
    },
    {
        "id": "devops_engineer",
        "name": "DevOps工程师",
        "keywords": ["Docker", "Kubernetes", "CI/CD", "Linux", "AWS", "Terraform"],
        "interview_focus": ["容器技术", "CI/CD流程", "基础设施即代码", "监控告警", "Linux"],
        "difficulty_level": "hard",
        "recommended_question_categories": ["DevOps", "操作系统", "系统设计", "计算机网络"]
    },
    {
        "id": "ai_ml_engineer",
        "name": "AI/ML工程师",
        "keywords": ["Python", "PyTorch", "TensorFlow", "机器学习", "深度学习", "NLP", "CV"],
        "interview_focus": ["机器学习基础", "深度学习框架", "数据处理", "模型部署", "算法"],
        "difficulty_level": "hard",
        "recommended_question_categories": ["Python", "数据结构与算法", "系统设计", "数据库"]
    },
    {
        "id": "intern_backend",
        "name": "后端开发实习生",
        "keywords": ["Python", "Java", "Go", "实习", "数据库", "API"],
        "interview_focus": ["编程基础", "数据结构", "学习能力", "项目经验"],
        "difficulty_level": "easy",
        "recommended_question_categories": ["Python", "数据库", "数据结构与算法", "计算机网络"]
    },
    {
        "id": "intern_frontend",
        "name": "前端开发实习生",
        "keywords": ["JavaScript", "React", "Vue", "CSS", "HTML", "实习"],
        "interview_focus": ["JavaScript基础", "CSS理解", "框架了解", "学习能力"],
        "difficulty_level": "easy",
        "recommended_question_categories": ["JavaScript", "CSS", "计算机网络", "数据结构与算法"]
    },
]


async def read_resume(db: AsyncSession, resume_id: int) -> Dict:
    from app.models.resume import Resume

    query = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(query)
    resume = result.scalar_one_or_none()

    if not resume:
        raise ValueError(f"简历不存在: {resume_id}")

    parsed = {}
    if resume.parsed_content:
        try:
            parsed = json.loads(resume.parsed_content)
        except json.JSONDecodeError:
            pass

    return {
        "resume_id": resume.id,
        "file_name": resume.file_name,
        "target_position": resume.target_position,
        "parsed_content": parsed,
        "status": resume.status
    }


async def extract_candidate_profile(resume_data: Dict) -> Dict:
    from app.core.config import settings
    from openai import AsyncOpenAI

    parsed_content = resume_data.get("parsed_content", {})
    target_position = resume_data.get("target_position", "未指定")

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的简历分析师。请从简历数据中提取候选人画像。\n"
                "必须返回纯JSON格式（不要markdown代码块）：\n"
                '{"name": "候选人姓名", "skills": ["Python", "FastAPI", "PostgreSQL"], '
                '"experience_years": 3, "education": "本科/硕士/博士", '
                '"summary": "一句话总结候选人背景和技术特长"}'
            )
        },
        {
            "role": "user",
            "content": (
                f"目标岗位：{target_position}\n"
                f"简历数据：{json.dumps(parsed_content, ensure_ascii=False)}"
            )
        }
    ]

    client = AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL
    )

    response = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=500
    )
    result_text = response.choices[0].message.content.strip()

    if result_text.startswith("```"):
        lines = result_text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        result_text = "\n".join(lines)

    try:
        profile = json.loads(result_text)
    except json.JSONDecodeError:
        profile = {"raw_output": result_text, "skills": [], "experience_years": 0}

    profile["_resume_id"] = resume_data.get("resume_id")
    profile["_target_position"] = target_position
    return profile


def match_job_template(skills: List[str], target_position: str) -> Dict:
    skills_lower = [s.lower() for s in skills]
    position_lower = target_position.lower()
    is_intern = "实习" in target_position or "intern" in position_lower

    best_match = None
    best_score = -1

    for template in JOB_TEMPLATES:
        if is_intern and "intern" not in template["id"] and "实习" not in template["name"]:
            continue
        if not is_intern and ("intern" in template["id"] or "实习" in template["name"]):
            continue

        score = 0
        for keyword in template["keywords"]:
            kw_lower = keyword.lower()
            if kw_lower in position_lower:
                score += 3
            for skill in skills_lower:
                if kw_lower in skill or skill in kw_lower:
                    score += 2

        if score > best_score:
            best_score = score
            best_match = template

    if not best_match:
        best_match = {
            "id": "general",
            "name": "通用技术面试",
            "interview_focus": ["编程基础", "数据结构", "项目经验"],
            "difficulty_level": "medium",
            "recommended_question_categories": ["Python", "数据库", "数据结构与算法", "系统设计"]
        }

    return {
        "job_template_id": best_match["id"],
        "job_template_name": best_match["name"],
        "interview_focus": best_match["interview_focus"],
        "difficulty_level": best_match["difficulty_level"],
        "recommended_question_categories": best_match["recommended_question_categories"],
        "match_score": best_score
    }


async def run_agent_pipeline(db: AsyncSession, resume_id: int) -> Dict:
    """
    按序执行：读取简历 → 提取画像 → 岗位匹配 → 生成面试配置
    直接调用函数链，不依赖 LangChain Agent
    """
    resume_data = await read_resume(db, resume_id)
    logger.info(f"[Agent] Step1: 简历读取成功, status={resume_data['status']}")

    profile = await extract_candidate_profile(resume_data)
    logger.info(f"[Agent] Step2: 画像提取成功, skills={profile.get('skills', [])}")

    skills = profile.get("skills", [])
    target = resume_data.get("target_position", "Python后端开发")

    job_match = match_job_template(skills, target)
    logger.info(f"[Agent] Step3: 岗位匹配成功, template={job_match['job_template_name']}")

    interview_config = {
        "difficulty_level": job_match["difficulty_level"],
        "recommended_question_categories": job_match["recommended_question_categories"],
        "interview_focus": job_match["interview_focus"],
        "suggested_question_count": 5
    }
    logger.info(f"[Agent] Step4: 面试配置生成成功, difficulty={interview_config['difficulty_level']}")

    return {
        "success": True,
        "resume_data": resume_data,
        "candidate_profile": profile,
        "job_match": job_match,
        "interview_config": interview_config
    }


def create_agent_tools(db: AsyncSession):
    """
    保留 LangChain Tool 定义，供未来 Agent 模式使用
    """
    from langchain.tools import tool

    @tool
    def read_resume_tool(resume_id: str) -> str:
        import asyncio
        result = asyncio.run(read_resume(db, int(resume_id)))
        return json.dumps(result, ensure_ascii=False)

    @tool
    def extract_profile_tool(resume_text: str) -> str:
        import asyncio
        data = json.loads(resume_text) if resume_text.startswith("{") else {"parsed_content": {}, "target_position": "未指定"}
        result = asyncio.run(extract_candidate_profile(data))
        return json.dumps(result, ensure_ascii=False)

    @tool
    def match_template_tool(skills: str, target_position: str) -> str:
        try:
            if skills.startswith("["):
                skills_list = json.loads(skills)
            else:
                skills_list = [s.strip() for s in skills.split(",")]
        except (json.JSONDecodeError, AttributeError):
            skills_list = [skills]
        result = match_job_template(skills_list, target_position)
        return json.dumps(result, ensure_ascii=False)

    return [read_resume_tool, extract_profile_tool, match_template_tool]
