"""
全流程 ASGI 直连测试：种子用户 → 登录 → 上传简历 → 面试 → 评分 → 报告
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TEST_EMAIL = "testuser@ai-interview.com"
TEST_PASSWORD = "Test@123456"
RESUME_PDF_PATH = os.path.join(os.path.dirname(__file__), "test_resume.pdf")


def create_resume_pdf():
    if os.path.exists(RESUME_PDF_PATH):
        return RESUME_PDF_PATH
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    c = rl_canvas.Canvas(RESUME_PDF_PATH, pagesize=A4)
    c.setFont("Helvetica", 18)
    c.drawString(50, 780, "Test User - Resume")
    c.setFont("Helvetica", 12)
    y = 750
    for line in [
        "Phone: 13800138000 | Email: test@example.com", "",
        "Education: 2020-2024 CS Bachelor XX University", "",
        "Skills: Python, JavaScript, SQL, FastAPI, Django, PostgreSQL, Redis, Docker", "",
        "Experience: 2023-2024 XX Tech Backend Intern",
        "- Built RESTful APIs with FastAPI + PostgreSQL",
        "- Optimized SQL queries, reduced slow queries by 60%",
        "- Implemented Redis caching, improved QPS by 3x", "",
        "Projects: Online Exam System (FastAPI+Vue+PostgreSQL)",
    ]:
        c.drawString(50, y, line)
        y -= 18
    c.showPage()
    c.save()
    print("[PDF] Created")
    return RESUME_PDF_PATH


async def seed_user():
    from app.core.config import settings
    from app.models.user import User
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select

    db_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        existing = await db.execute(select(User).where(User.email == TEST_EMAIL))
        user = existing.scalar_one_or_none()
        if user:
            print(f"[Seed] User exists: id={user.id}")
        else:
            user = User(
                email=TEST_EMAIL,
                hashed_password=User.get_password_hash(TEST_PASSWORD),
                first_name="TestUser",
                last_name="Test",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"[Seed] User created: id={user.id}")

    await engine.dispose()


async def test_flow():
    from httpx import AsyncClient, ASGITransport
    from app.route import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    BASE = "/api/v1"

    print("=" * 70)
    print("  AI Interview System - Full Flow Test")
    print("=" * 70)

    await seed_user()

    async with AsyncClient(transport=transport, base_url="http://test") as c:

        # ── Login ──
        print("\n-- Step 1: Login --")
        resp = await c.post(f"{BASE}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["data"]["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        print(f"  OK token={token[:20]}...")

        # ── Upload ──
        print("\n-- Step 2: Upload Resume --")
        pdf_path = create_resume_pdf()
        with open(pdf_path, "rb") as f:
            resp = await c.post(
                f"{BASE}/resumes/upload",
                data={"target_position": "Python Backend Developer"},
                files={"file": ("resume.pdf", f, "application/pdf")},
                headers=H, timeout=180
            )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        data = resp.json()["data"]
        resume_id = data["resume_id"]
        print(f"  ResumeID={resume_id} status={data['status']}")
        res = None

        # ── Poll ──
        print("\n-- Step 3: Resume Parsing --")
        agent_profile = job_match = None
        for i in range(20):
            await asyncio.sleep(3)
            resp = await c.get(f"{BASE}/resumes/{resume_id}", headers=H)
            res = resp.json()["data"]
            status = res["status"]
            print(f"  [{i+1}/20] {status}")
            if status == "completed":
                analysis = res.get("analysis") or {}
                agent_profile = analysis.get("agent_profile")
                job_match = analysis.get("job_match")
                if agent_profile:
                    print(f"  [Module2] Profile: {json.dumps(agent_profile, ensure_ascii=False)[:200]}")
                if job_match:
                    print(f"  [Module2] Match: {json.dumps(job_match, ensure_ascii=False)[:200]}")
                break
            elif status == "failed":
                print(f"  FAILED! Check app logs")
                return

        if not res or res["status"] != "completed":
            print("  TIMEOUT!")
            return

        # ── Interview ──
        print("\n-- Step 4: Start Interview (RAG) --")
        resp = await c.post(f"{BASE}/interviews/start", json={
            "resume_id": resume_id,
            "target_position": "Python Backend Developer",
            "difficulty": "medium",
            "total_questions": 3
        }, headers=H, timeout=180)
        assert resp.status_code == 200, f"Start failed: {resp.text}"
        d = resp.json()["data"]
        iid = d["interview_id"]
        print(f"  InterviewID={iid}")
        print(f"  Q1: {d['first_question'][:100]}...")

        # ── Answer ──
        answers = [
            "I am a CS graduate with 1 year backend internship. I worked with Python, FastAPI, PostgreSQL and Redis. I built an online exam system as a personal project.",
            "Deep copy recursively copies the entire object tree, creating fully independent copies via copy.deepcopy(). Shallow copy only copies top-level, nested objects share references, via copy.copy(). Use deep copy for isolated nested mutations, shallow for top-level independence only.",
            "RESTful API principles: 1) Resource-oriented URLs with noun plurals; 2) HTTP methods map to CRUD; 3) Stateless with auth per request; 4) Proper HTTP status codes; 5) Pagination/filtering/sorting; 6) API versioning."
        ]

        for qi, ans in enumerate(answers, 1):
            print(f"\n-- Answer Q{qi} --")
            resp = await c.post(f"{BASE}/interviews/{iid}/answer", json={"answer": ans}, headers=H, timeout=180)
            assert resp.status_code == 200, f"Submit Q{qi} failed: {resp.text}"
            d = resp.json()["data"]
            print(f"  Score={d.get('score')} feedback={d.get('feedback','')[:80]}...")
            if d.get("next_question"):
                print(f"  Next: {d['next_question'][:80]}...")
            if d.get("is_finished"):
                print(f"  >>> Interview COMPLETED!")

        # ── Messages (Module 3) ──
        print("\n-- Step 6: Messages (Module 3) --")
        resp = await c.get(f"{BASE}/interviews/{iid}/messages", headers=H)
        msgs = resp.json()["data"]
        has_ref = any(m.get("reference_answer") for m in msgs)
        has_kp = any(m.get("key_points") for m in msgs)
        print(f"  Total: {len(msgs)} messages")
        for m in msgs:
            ri = "INTV" if m["role"] == "interviewer" else "CAND"
            ref = " [REF]" if m.get("reference_answer") else ""
            kp = " [KP]" if m.get("key_points") else ""
            sc = f" s={m['score']}" if m.get("score") else ""
            print(f"  [{ri}] Q{m.get('question_index','?')}: {m['content'][:60]}...{sc}{ref}{kp}")
        print(f"  Module3 ref_answer={'OK' if has_ref else 'MISSING'}")
        print(f"  Module3 key_points={'OK' if has_kp else 'MISSING'}")

        # ── Report ──
        print("\n-- Step 7: Report --")
        resp = await c.get(f"{BASE}/interviews/{iid}/report", headers=H)
        r = resp.json()["data"]
        rep = r.get("report", {})
        print(f"  Overall: {r['overall_score']}")
        print(f"  Summary: {rep.get('summary','N/A')[:120]}")
        print(f"  Hire: {rep.get('hire_recommendation','N/A')}")

        # ── Summary ──
        print("\n" + "=" * 70)
        print("  TEST RESULTS")
        print("=" * 70)
        print(f"  Resume Parsing:          PASS")
        print(f"  Agent Profile (Module2): {'PASS' if agent_profile else 'SKIP'}")
        print(f"  RAG Interview (Module1): PASS")
        print(f"  Scoring+Ref (Module3):   {'PASS' if has_ref and has_kp else 'FAIL'}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_flow())
