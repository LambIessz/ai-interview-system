# AI-Interview — 基于 RAG 与 Agent 的智能模拟面试系统

面向求职场景的 AI 模拟面试平台，围绕**简历解析 → 岗位匹配 → RAG 出题 → AI 评分 → 面试报告**构建完整闭环。

## 项目结构

```
ai-interview/
├── ai-interview-backend/    # FastAPI 后端（Python）
├── ai-interview-frontend/   # 用户端前端（Vue 3 + Vite）
└── ai-interview-admin/      # 管理后台（Vue 3 + Vite）
```

## 核心功能

| 模块 | 描述 |
|------|------|
| 📄 **简历解析** | 上传 PDF 简历，DeepSeek API 自动提取姓名、技能、学历、项目经验等结构化信息，并给出优劣势分析 |
| 🧠 **岗位匹配 Agent** | 提取候选人画像后，与 8 个预置岗位模板（后端/前端/全栈/数据/DevOps/AI/实习生）进行关键词加权匹配，自动推荐面试方案 |
| 📚 **RAG 题库检索** | 32 道预置面试题（11 个技术分类）通过 DashScope Embedding 向量化存入 pgvector 数据库，出题时通过 Cosine 相似度检索，让 LLM 从题库中选题并个性化改写 |
| 🤖 **AI 模拟面试** | DeepSeek API 驱动多轮对话面试，支持 SSE 流式输出，状态机控制 in_progress → completed 流程 |
| 📊 **稳定评分** | 评分阶段注入 reference_answer（参考答案）与 key_points（考察要点），LLM 逐条对照打分，输出 covered_points / missing_points 细粒度评估 |
| 📝 **面试报告** | 面试完成后自动生成综合评估报告，含总体评分、优劣势分析、录用建议 |
| 🔐 **认证系统** | JWT 登录/注册/邮箱验证，Backoffice 管理后台独立认证 |
| 📨 **邮件通知** | 验证码邮件、密码重置邮件（支持 Brevo / SMTP） |
| ⏱ **异步任务** | Celery + Redis 处理邮件发送等后台任务 |

## 技术栈

### 后端

- **框架**：FastAPI（异步路由、SSE 流式、依赖注入）
- **数据库**：PostgreSQL + pgvector（Cosine 向量检索、ivfflat 索引）
- **ORM**：SQLAlchemy async + Alembic 迁移
- **缓存/队列**：Redis + Celery
- **AI**：DeepSeek API（简历解析/画像提取/出题/评分/报告）、DashScope Embedding（text-embedding-v2）
- **Agent**：LangChain Tool Calling Agent（岗位匹配流水线）
- **认证**：JWT（python-jose + passlib）
- **部署**：Docker Compose（postgres + pgvector + redis + nginx）

### 前端 / 管理后台

- **框架**：Vue 3（Composition API）
- **路由**：Vue Router 4
- **状态管理**：Pinia
- **HTTP**：Axios
- **构建**：Vite 5

## 快速开始

### 环境要求

- Python 3.10+
- Docker & Docker Compose
- Node.js 18+（前端开发）

### 1. 克隆仓库

```bash
git clone https://github.com/LambIessz/ai-interview-system.git
cd ai-interview-system/ai-interview-backend
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填写必需配置：

```ini
# DeepSeek AI 配置（必填）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# DashScope Embedding 配置（必填 - RAG 题库向量化）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v2

# 数据库
POSTGRES_PORT=5434
POSTGRES_HOST=localhost
```

### 3. 启动后端服务

```bash
# 启动 PostgreSQL（pgvector）+ Redis
docker compose up -d postgres redis

# 安装 Python 依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 初始化题库（生成向量嵌入）
python scripts/init_question_bank.py

# 启动后端
python main.py
```

服务运行在 `http://localhost:8006`，API 文档自动生成在 `http://localhost:8006/docs`。

### 4. 启动前端（可选）

```bash
cd ai-interview-frontend
npm install
npm run dev
```

### 5. 启动管理后台（可选）

```bash
cd ai-interview-admin
npm install
npm run dev
```

## API 概览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/resumes/upload` | POST | 上传 PDF 简历 |
| `/api/v1/resumes/{id}` | GET | 查看简历解析结果 |
| `/api/v1/interviews/start` | POST | 开始面试（RAG出题） |
| `/api/v1/interviews/{id}/answer` | POST | 提交回答 + AI 评分 |
| `/api/v1/interviews/{id}/answer/stream` | POST | SSE 流式评分 |
| `/api/v1/interviews/{id}/messages` | GET | 获取对话记录 |
| `/api/v1/interviews/{id}/report` | GET | 获取面试报告 |

## 数据流

```
用户上传 PDF
  → DeepSeek 解析简历 + 画像提取
  → Agent 岗位模板匹配（8 个模板关键词加权）
  → RAG 检索题库（DashScope 向量化 → pgvector Cosine 检索 Top-20）
  → LLM 从候选题库中选题并个性化改写
  → 多轮对话面试（SSE 流式输出）
  → 评分（注入 reference_answer + key_points）
  → 生成综合报告
```

## 项目亮点

- **RAG 向量检索**：出题从"LLM 凭空生成"升级为"题库支撑 + AI 改写"，题目与候选人技能精准匹配
- **Agent 自动化**：8 个岗位模板自动匹配面试方案，无需人工干预
- **评分可解释**：评分关联参考答案和考察要点，输出细粒度 covered / missing points
- **数据库版本管理**：6 个 Alembic 迁移文件覆盖完整表结构演进，可追溯可回滚
- **Docker 一键部署**：PostgreSQL（pgvector）+ Redis + FastAPI + Celery + Nginx

## 常见问题

**Q: pgvector 扩展未安装？**

使用 `pgvector/pgvector:pg16` 镜像替代标准 postgres 镜像即可。若无法拉取 Docker Hub，可通过 DaoCloud 镜像源：

```bash
docker pull docker.m.daocloud.io/pgvector/pgvector:pg16
docker tag docker.m.daocloud.io/pgvector/pgvector:pg16 pgvector/pgvector:pg16
```

**Q: 题库初始化失败？**

确保 `.env` 中 `DASHSCOPE_API_KEY` 已填写真实密钥，且 `PGVECTOR_ENABLED=true`。

**Q: 如何运行测试？**

```bash
cd ai-interview-backend
python scripts/test_full_flow.py
```

该脚本通过 ASGI 直连方式运行全流程测试，无需启动网络服务。

## License

MIT
