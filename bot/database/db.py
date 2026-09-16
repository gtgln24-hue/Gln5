"""
GLN Quiz Bot - Database Connection & Initialization
Handles async engine creation, schema migration, and initial question seeding.
"""

import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.config import settings
from bot.database.models import Base, QuestionBank

logger = logging.getLogger(__name__)

# Normalize database URL
db_url = (settings.DATABASE_URL or "").strip() or "sqlite+aiosqlite:///gln_quiz.db"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("sqlite:///") and not db_url.startswith("sqlite+aiosqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

if "postgresql+asyncpg://" in db_url:
    # asyncpg expects ssl=require instead of sslmode=require and does not support channel_binding
    db_url = db_url.replace("sslmode=require", "ssl=require")
    db_url = db_url.replace("&channel_binding=require", "").replace("channel_binding=require&", "").replace("channel_binding=require", "")

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True if "postgresql" in db_url else False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def _check_and_migrate_schema(conn):
    """Checks if used_questions has the new question_hash column on SQLite; drops old table if necessary."""
    if "sqlite" not in db_url:
        return
    from sqlalchemy import text
    try:
        res = await conn.execute(text("PRAGMA table_info(used_questions)"))
        cols = [row[1] for row in res.fetchall()]
        if cols and "question_hash" not in cols:
            logger.info("Detected legacy used_questions schema. Migrating to new schema with question_hash...")
            await conn.execute(text("DROP TABLE used_questions"))
    except Exception as e:
        logger.debug(f"Table inspection: {e}")

async def init_db():
    """Create all tables and seed default verified Hindi questions if empty."""
    async with engine.begin() as conn:
        await _check_and_migrate_schema(conn)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")

    # Seed initial questions from questions.json
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import select, func
            count_res = await session.execute(select(func.count()).select_from(QuestionBank))
            count = count_res.scalar() or 0

            if count == 0:
                json_path = Path(__file__).resolve().parent.parent / "data" / "questions.json"
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        items = json.load(f)

                    existing_ids_res = await session.execute(select(QuestionBank.question_id))
                    existing_ids = set(existing_ids_res.scalars().all())

                    for item in items:
                        qid = item.get("question_id") or item.get("id")
                        if not qid or qid in existing_ids:
                            continue
                        qb = QuestionBank(
                            question_id=qid,
                            subject=item["subject"],
                            question=item["question"],
                            correct_answer=item["correct_answer"],
                            options_json=json.dumps(item["options"], ensure_ascii=False),
                            exam_name=item.get("exam_name"),
                            exam_year=item.get("exam_year"),
                            topic=item.get("topic"),
                            source_reference=item.get("source_reference"),
                        )
                        session.add(qb)
                        existing_ids.add(qid)
                    await session.commit()
                    logger.info("Verified and updated Hindi question bank.")
        except Exception as e:
            logger.error("Error seeding question bank: %s", e)
            await session.rollback()

async def get_session() -> AsyncSession:
    """Dependency helper for async database sessions."""
    async with AsyncSessionLocal() as session:
        yield session
