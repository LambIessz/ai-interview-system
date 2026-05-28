import json
import logging
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# DeepSeek 使用 OpenAI 兼容 API
client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL
)


class AIService:
    """DeepSeek AI 服务 - 面试模拟核心"""

    @staticmethod
    async def _chat(messages: list, temperature: float = 0.7) -> str:
        """基础对话补全调用"""
        try:
            response = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise

    @staticmethod
    async def _chat_stream(messages: list, temperature: float = 0.7):
        """流式对话补全调用，逐块返回文本"""
        try:
            stream = await client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DeepSeek 流式 API 调用失败: {e}")
            raise

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 AI 响应中提取 JSON，处理 markdown 代码块包裹的情况"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # 移除开头的 ```json 行
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return json.loads(text)

    @staticmethod
    async def parse_resume(resume_text: str) -> dict:
        """解析简历文本，提取结构化信息（姓名、学历、技能、经历等）"""
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的简历分析师。请解析简历内容，提取结构化信息。"
                    "必须返回纯JSON格式（不要markdown代码块），包含以下字段：\n"
                    '{"name": "姓名", "education": "学历信息", '
                    '"skills": ["技能列表"], "experience": ["工作/实习经历"], '
                    '"projects": ["项目经历"], "summary": "一句话总结候选人背景"}'
                )
            },
            {
                "role": "user",
                "content": f"请解析以下简历内容：\n\n{resume_text}"
            }
        ]
        result = await AIService._chat(messages, temperature=0.3)
        return AIService._extract_json(result)

    @staticmethod
    async def analyze_resume(parsed_resume: dict, target_position: str) -> dict:
        """分析简历质量，给出评分、优劣势和改进建议"""
        # 判断是否为实习岗位，调整评价标准
        is_intern = any(kw in target_position.lower() for kw in ["实习", "intern"])
        if is_intern:
            level_hint = (
                "【重要】目标岗位是实习岗位，候选人是在校学生，请严格按实习生标准评价。\n"
                "禁止事项：\n"
                "- 禁止在weaknesses中提及'缺少实习经验'、'缺少工作经验'、'没有实际工作经验'等类似表述\n"
                "- 禁止因为项目是个人项目或校内项目而扣分，这对实习生来说是正常的\n"
                "- 禁止要求候选人具备线上生产环境经验\n"
                "评价重点：技术基础扎实度、项目完成度和技术深度、学习能力、编码能力。\n"
                "个人项目和校内项目同样能体现技术能力，请公正评价项目质量本身。\n"
            )
        else:
            level_hint = (
                "目标岗位是正式岗位，请按社招标准评价。\n"
                "重点关注：工作经验、项目深度、技术广度、解决复杂问题的能力。\n"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个资深HR和职业规划师，请针对{target_position}岗位分析这份简历。\n"
                    f"{level_hint}"
                    "必须返回纯JSON格式（不要markdown代码块），包含以下字段：\n"
                    '{"overall_score": 7.5, '
                    '"strengths": ["优势1", "优势2", "优势3"], '
                    '"weaknesses": ["不足1", "不足2", "不足3"], '
                    '"suggestions": ["具体改进建议1", "具体改进建议2", "具体改进建议3"], '
                    '"keyword_match": ["匹配的关键技能1", "匹配的关键技能2"], '
                    '"missing_keywords": ["缺少的关键技能1", "缺少的关键技能2"], '
                    '"summary": "一段话总结简历质量和改进方向，100字以内"}'
                    "\n评分标准：9-10优秀，7-8良好，5-6一般，3-4较差，1-2很差"
                )
            },
            {
                "role": "user",
                "content": (
                    f"目标岗位：{target_position}\n"
                    f"简历内容：{json.dumps(parsed_resume, ensure_ascii=False)}"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.4)
        return AIService._extract_json(result)

    @staticmethod
    async def generate_questions(
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        count: int
    ) -> list:
        """根据简历和目标岗位生成面试题目，每道题包含参考答案和考察要点"""
        difficulty_map = {
            "easy": "初级，侧重基础知识和简单项目经验",
            "medium": "中级，涵盖技术深度和项目设计思路",
            "hard": "高级，深入系统设计、性能优化和技术原理"
        }
        difficulty_desc = difficulty_map.get(difficulty, difficulty_map["medium"])

        is_intern = any(kw in target_position for kw in ["实习", "intern", "Intern"])
        position_hint = ""
        if is_intern:
            position_hint = (
                "\n注意：这是实习岗位面试，候选人可能是在校学生，请适当降低难度：\n"
                "- 侧重基础知识（语言基础、数据结构、常用框架）\n"
                "- 项目经验题以学习过程和思路为主，不要求生产级方案\n"
                "- 不要出过于深入的系统设计和高并发优化题\n"
                "- 可以考察学习能力和成长潜力\n"
            )
        else:
            position_hint = (
                "\n注意：这是正式岗位面试，请按正常标准出题：\n"
                "- 要求候选人有扎实的技术基础和实际项目经验\n"
                "- 可以涉及系统设计、性能优化、线上问题排查等\n"
                "- 考察解决实际问题的能力和技术深度\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个资深技术面试官，正在面试{target_position}岗位。\n"
                    f"面试难度：{difficulty_desc}\n"
                    f"{position_hint}\n"
                    "请根据候选人背景生成面试题。要求：\n"
                    "1. 结合候选人的项目经验和技术栈提问\n"
                    "2. 第一题是自我介绍\n"
                    "3. 覆盖技术深度、项目经验、基础知识\n"
                    "4. 返回纯JSON数组格式（不要markdown代码块）\n"
                    '格式：[{"index": 0, "question": "题目内容", "category": "分类", '
                    '"reference_answer": "详细参考答案（100-300字）", '
                    '"key_points": ["考察要点1", "考察要点2", "考察要点3"]}]\n'
                    "分类包括：self-intro, project, technical, coding, system-design\n"
                    "key_points 应包含3-5个具体考察点，如：是否掌握核心概念、能否举出实际应用场景、是否了解底层原理等"
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人简历信息：{json.dumps(parsed_resume, ensure_ascii=False)}\n"
                    f"目标岗位：{target_position}\n"
                    f"请生成{count}道面试题。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.7)
        return AIService._extract_json(result)

    @staticmethod
    async def generate_questions_with_pool(
        parsed_resume: dict,
        target_position: str,
        difficulty: str,
        count: int,
        question_pool: list
    ) -> list:
        """根据 RAG 检索的候选题池，让 LLM 选题并个性化改写生成面试题"""
        pool_text = ""
        for i, q in enumerate(question_pool):
            pool_text += (
                f"[{i}] {q.get('question_text', q.get('question', ''))} "
                f"| 分类: {q.get('category', '')} | 难度: {q.get('difficulty', '')}\n"
            )

        difficulty_map = {
            "easy": "初级，侧重基础知识和简单项目经验",
            "medium": "中级，涵盖技术深度和项目设计思路",
            "hard": "高级，深入系统设计、性能优化和技术原理"
        }
        difficulty_desc = difficulty_map.get(difficulty, difficulty_map["medium"])

        is_intern = any(kw in target_position for kw in ["实习", "intern", "Intern"])
        position_hint = ""
        if is_intern:
            position_hint = (
                "\n注意：这是实习岗位面试，候选人可能是在校学生，请适当降低难度。\n"
            )
        else:
            position_hint = (
                "\n注意：这是正式岗位面试，请按正常标准出题。\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个资深技术面试官，正在面试{target_position}岗位。\n"
                    f"面试难度：{difficulty_desc}\n"
                    f"{position_hint}\n"
                    "请从候选题库中选取最合适的题目，结合候选人背景进行个性化改写。要求：\n"
                    "1. 第一题固定为自我介绍\n"
                    "2. 从候选题库中挑选与候选人技能和岗位最相关的题目\n"
                    "3. 可以结合候选人项目经验对题目进行微调\n"
                    "4. 覆盖技术深度、项目经验、基础知识\n"
                    "5. 返回纯JSON数组格式（不要markdown代码块）\n"
                    '格式：[{"index": 0, "question": "题目内容", "category": "分类", '
                    '"reference_answer": "详细参考答案（100-300字）", '
                    '"key_points": ["考察要点1", "考察要点2", "考察要点3"], '
                    '"source_question_id": 候选题库中的题目ID（可选）}]\n'
                    "分类包括：self-intro, project, technical, coding, system-design"
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人简历信息：{json.dumps(parsed_resume, ensure_ascii=False)}\n"
                    f"目标岗位：{target_position}\n"
                    f"\n===== 候选题库（从中选题）=====\n{pool_text}\n"
                    f"\n请从候选题库中挑选{count}道最合适的面试题并个性化改写。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.7)
        return AIService._extract_json(result)

    @staticmethod
    async def evaluate_answer(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        reference_answer: Optional[str] = None,
        key_points: Optional[list] = None,
        next_question: Optional[str] = None
    ) -> dict:
        """评估候选人的回答，返回评分、覆盖要点、缺失要点和反馈"""
        history_text = ""
        for msg in chat_history[-6:]:
            role = "面试官" if msg["role"] == "interviewer" else "候选人"
            history_text += f"{role}: {msg['content']}\n"

        ref_section = ""
        if reference_answer and reference_answer.strip():
            ref_section += f"\n【参考答案】{reference_answer}\n"

        kp_section = ""
        if key_points and len(key_points) > 0:
            kp_list = "\n".join([f"  - {kp}" for kp in key_points])
            kp_section += f"\n【考察要点】\n{kp_list}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一名专业面试评估官。请根据以下信息对候选人回答进行评分。\n"
                    "请返回纯JSON格式（不要markdown代码块）：\n"
                    '{"score": 7.5, "covered_points": ["已覆盖的考察要点1"], '
                    '"missing_points": ["未覆盖的考察要点1"], '
                    '"comment": "详细点评80字以内", "follow_up": false}\n'
                    "\n评分标准：\n"
                    "- 对照考察要点逐项检查候选人是否覆盖\n"
                    "- 结合参考答案判断回答深度和准确性\n"
                    "- 9-10: 回答非常出色，有深度有见解，覆盖所有要点\n"
                    "- 7-8: 回答良好，基本正确，覆盖大部分要点\n"
                    "- 5-6: 回答一般，有明显不足，覆盖部分要点\n"
                    "- 3-4: 回答较差，理解有误，很少覆盖要点\n"
                    "- 1-2: 基本没有回答到点上"
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人背景：{json.dumps(resume_context, ensure_ascii=False)}\n"
                    f"对话历史：\n{history_text}\n"
                    f"【面试题目】{question}\n"
                    f"{ref_section}"
                    f"{kp_section}"
                    f"【候选人回答】{answer}\n"
                    "请评估这个回答，逐项检查考察要点的覆盖情况。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.5)
        parsed = AIService._extract_json(result)
        if "feedback" not in parsed and "comment" in parsed:
            parsed["feedback"] = parsed["comment"]
        if "feedback" not in parsed:
            parsed["feedback"] = parsed.get("comment", "")
        return parsed

    @staticmethod
    async def evaluate_answer_stream(
        question: str,
        answer: str,
        resume_context: dict,
        chat_history: list,
        reference_answer: Optional[str] = None,
        key_points: Optional[list] = None
    ):
        """流式版本：评估回答并逐块输出评语，注入参考答案和考察要点"""
        history_text = ""
        for msg in chat_history[-6:]:
            role = "面试官" if msg["role"] == "interviewer" else "候选人"
            history_text += f"{role}: {msg['content']}\n"

        ref_section = ""
        if reference_answer and reference_answer.strip():
            ref_section += f"\n【参考答案】{reference_answer}\n"

        kp_section = ""
        if key_points and len(key_points) > 0:
            kp_list = "\n".join([f"  - {kp}" for kp in key_points])
            kp_section += f"\n【考察要点】\n{kp_list}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一名专业面试评估官，正在评估候选人的回答。\n"
                    "请对照考察要点和参考答案，先用自然语言给出详细点评（100字左右），"
                    "逐项检查候选人是否覆盖考察要点，然后换行输出评分JSON。\n"
                    "格式要求：\n"
                    "先输出点评文字，然后另起一行输出：\n"
                    '```json\n{"score": 7.5, "covered_points": ["已覆盖要点"], '
                    '"missing_points": ["未覆盖要点"]}\n```'
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人背景：{json.dumps(resume_context, ensure_ascii=False)}\n"
                    f"对话历史：\n{history_text}\n"
                    f"【面试题目】{question}\n"
                    f"{ref_section}"
                    f"{kp_section}"
                    f"【候选人回答】{answer}\n"
                    "请评估这个回答，逐项检查考察要点的覆盖情况。"
                )
            }
        ]
        async for chunk in AIService._chat_stream(messages, temperature=0.5):
            yield chunk

    @staticmethod
    async def generate_report(
        parsed_resume: dict,
        target_position: str,
        questions_and_scores: list
    ) -> dict:
        """根据面试记录生成综合评估报告"""
        qa_text = ""
        for item in questions_and_scores:
            qa_text += (
                f"问题：{item['question']}\n"
                f"回答：{item.get('answer', '未回答')}\n"
                f"得分：{item.get('score', 'N/A')}\n\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个资深技术面试官，请根据面试记录生成综合评估报告。\n"
                    "返回纯JSON格式（不要markdown代码块）：\n"
                    '{"summary": "总体评价100字以内", '
                    '"strengths": ["优势1", "优势2"], '
                    '"weaknesses": ["不足1", "不足2"], '
                    '"suggestions": ["建议1", "建议2"], '
                    '"hire_recommendation": "建议录用/待定/不建议录用"}'
                )
            },
            {
                "role": "user",
                "content": (
                    f"候选人背景：{json.dumps(parsed_resume, ensure_ascii=False)}\n"
                    f"目标岗位：{target_position}\n"
                    f"面试记录：\n{qa_text}\n"
                    "请生成综合评估报告。"
                )
            }
        ]
        result = await AIService._chat(messages, temperature=0.5)
        return AIService._extract_json(result)
