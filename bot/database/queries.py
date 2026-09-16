"""
GLN Quiz Bot - Database Queries
High-performance asynchronous queries for groups, approvals, sessions, answers, and leaderboard.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, delete, and_, desc, func, Integer, cast, case
from bot.database.db import AsyncSessionLocal
from bot.database.models import (
    Group,
    ApprovedGroup,
    User,
    QuizSession,
    QuizQuestion,
    UserAnswer,
    SubjectCooldown,
    QuestionBank,
    UsedQuestion,
    GroupLeaderboard,
)
from bot.config import settings

async def get_or_create_group(
    group_id: int,
    group_name: str,
    group_username: Optional[str] = None,
    member_count: int = 0,
    added_by_user: Optional[str] = None,
    is_admin: bool = False,
) -> Group:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Group).where(Group.group_id == group_id))
        group = result.scalar_one_or_none()

        if not group:
            # Check if pre-approved
            app_res = await session.execute(
                select(ApprovedGroup).where(ApprovedGroup.group_id == group_id)
            )
            is_approved = app_res.scalar_one_or_none() is not None

            group = Group(
                group_id=group_id,
                group_name=group_name,
                group_username=group_username,
                member_count=member_count,
                added_by_user=added_by_user,
                is_admin=is_admin,
                is_approved=is_approved,
                added_at=datetime.utcnow(),
            )
            session.add(group)
            await session.commit()
            await session.refresh(group)
        else:
            # Update current attributes
            group.group_name = group_name
            if group_username:
                group.group_username = group_username
            if member_count > 0:
                group.member_count = member_count
            group.is_admin = is_admin
            await session.commit()
            await session.refresh(group)
        return group

async def is_group_approved(group_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ApprovedGroup).where(ApprovedGroup.group_id == group_id)
        )
        return result.scalar_one_or_none() is not None

async def approve_group(group_id: int, owner_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        # Add to approved_groups
        existing = await session.execute(
            select(ApprovedGroup).where(ApprovedGroup.group_id == group_id)
        )
        if not existing.scalar_one_or_none():
            app = ApprovedGroup(
                group_id=group_id,
                approved_at=datetime.utcnow(),
                approved_by_owner=owner_id,
            )
            session.add(app)

        # Update group table if present
        grp_res = await session.execute(select(Group).where(Group.group_id == group_id))
        group = grp_res.scalar_one_or_none()
        if group:
            group.is_approved = True
            group.approved_at = datetime.utcnow()
            group.approved_by_owner = owner_id
        await session.commit()
        return True

async def set_group_admin_status(group_id: int, is_admin: bool):
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Group).where(Group.group_id == group_id).values(is_admin=is_admin)
        )
        await session.commit()

async def get_subject_cooldown(group_id: int, subject: str) -> Optional[datetime]:
    """Returns the cooldown_until datetime if on cooldown, else None."""
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        res = await session.execute(
            select(SubjectCooldown).where(
                and_(
                    SubjectCooldown.group_id == group_id,
                    SubjectCooldown.subject == subject,
                    SubjectCooldown.cooldown_until > now,
                )
            )
        )
        row = res.scalar_one_or_none()
        return row.cooldown_until if row else None

async def set_subject_cooldown(group_id: int, subject: str, duration_seconds: int = 10800):
    """Sets 3-hour cooldown for group and subject."""
    async with AsyncSessionLocal() as session:
        cooldown_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        res = await session.execute(
            select(SubjectCooldown).where(
                and_(
                    SubjectCooldown.group_id == group_id,
                    SubjectCooldown.subject == subject,
                )
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            existing.cooldown_until = cooldown_until
        else:
            entry = SubjectCooldown(
                group_id=group_id,
                subject=subject,
                cooldown_until=cooldown_until,
            )
            session.add(entry)
        await session.commit()

async def get_used_question_hashes(group_id: int, subject: str) -> List[str]:
    """Retrieves all question hashes previously shown in this group for this subject."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UsedQuestion.question_hash).where(
                and_(
                    UsedQuestion.group_id == group_id,
                    UsedQuestion.subject == subject,
                )
            )
        )
        return [row[0] for row in res.all()]

async def is_question_hash_used(group_id: int, subject: str, question_hash: str) -> bool:
    """Checks if a normalized question hash exists in the database for this group and subject."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UsedQuestion.question_hash).where(
                and_(
                    UsedQuestion.group_id == group_id,
                    UsedQuestion.subject == subject,
                    UsedQuestion.question_hash == question_hash,
                )
            )
        )
        return res.scalar_one_or_none() is not None

async def get_used_question_texts(group_id: int, subject: str, limit: int = 200) -> List[str]:
    """Retrieves recent question texts used for semantic comparison and AI prompt context."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UsedQuestion.question_text)
            .where(
                and_(
                    UsedQuestion.group_id == group_id,
                    UsedQuestion.subject == subject,
                )
            )
            .order_by(desc(UsedQuestion.used_at))
            .limit(limit)
        )
        return [row[0] for row in res.all()]

async def insert_used_question_if_unique(
    group_id: int,
    subject: str,
    question_hash: str,
    question_text: str,
    quiz_session_id: str,
) -> bool:
    """
    Inserts question into used_questions FIRST.
    Enforces UNIQUE(group_id, subject, question_hash) constraint.
    Returns True if successfully inserted; False if duplicate or constraint violation.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Check existing first
            existing = await session.execute(
                select(UsedQuestion.id).where(
                    and_(
                        UsedQuestion.group_id == group_id,
                        UsedQuestion.subject == subject,
                        UsedQuestion.question_hash == question_hash,
                    )
                )
            )
            if existing.scalar_one_or_none() is not None:
                return False

            uq = UsedQuestion(
                group_id=group_id,
                subject=subject,
                question_hash=question_hash,
                question_text=question_text,
                quiz_session_id=quiz_session_id,
                used_at=datetime.utcnow(),
            )
            session.add(uq)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

async def get_used_question_ids(group_id: int) -> List[str]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UsedQuestion.question_hash).where(UsedQuestion.group_id == group_id)
        )
        return [row[0] for row in res.all()]

async def mark_question_used(group_id: int, question_id: str):
    pass

async def get_active_session(group_id: int) -> Optional[QuizSession]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(QuizSession).where(
                and_(
                    QuizSession.group_id == group_id,
                    QuizSession.status.in_(["WAITING", "PREPARING", "RUNNING", "PAUSED"]),
                )
            ).order_by(desc(QuizSession.started_at))
        )
        return res.scalars().first()

async def get_session_by_id(session_id: str) -> Optional[QuizSession]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(QuizSession).where(QuizSession.session_id == session_id)
        )
        return res.scalar_one_or_none()

async def update_session_status(session_id: str, status: str, active_message_id: Optional[int] = None):
    async with AsyncSessionLocal() as session:
        values = {"status": status, "last_active_at": datetime.utcnow()}
        if active_message_id is not None:
            values["active_message_id"] = active_message_id
        if status in ["COMPLETED", "STOPPED"]:
            values["finished_at"] = datetime.utcnow()
        await session.execute(
            update(QuizSession).where(QuizSession.session_id == session_id).values(**values)
        )
        await session.commit()

async def update_session_question(
    session_id: str,
    current_question: int,
    active_message_id: Optional[int] = None,
    consecutive_empty: int = 0,
):
    async with AsyncSessionLocal() as session:
        values: Dict[str, Any] = {
            "current_question": current_question,
            "consecutive_empty_answers": consecutive_empty,
            "last_active_at": datetime.utcnow(),
        }
        if active_message_id is not None:
            values["active_message_id"] = active_message_id
        await session.execute(
            update(QuizSession)
            .where(QuizSession.session_id == session_id)
            .values(**values)
        )
        await session.commit()

async def save_session_questions(session_id: str, questions: List[Dict[str, Any]]):
    """
    Persists pre-generated ordered questions for this quiz session (order: 1..100).
    Ensures question queue order is completely preserved in database.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(delete(QuizQuestion).where(QuizQuestion.session_id == session_id))
        for idx, q in enumerate(questions, start=1):
            options_payload = json.dumps({
                "options": q.get("options", []),
                "correct_letter": q.get("correct_letter", "A"),
                "question_hash": q.get("question_hash", ""),
            })
            qq = QuizQuestion(
                session_id=session_id,
                question_index=idx,
                question_id=q.get("question_id", f"q_{session_id}_{idx}"),
                question_text=q.get("question", ""),
                shuffled_options=options_payload,
                correct_answer=q.get("correct_answer", ""),
                exam_name=q.get("exam_name", "General Competition"),
                exam_year=q.get("exam_year", 2023),
                topic=q.get("topic", "सामान्य अध्ययन"),
                source_reference=q.get("source_reference", "NCERT / State Board"),
            )
            session.add(qq)
        await session.commit()

async def get_session_question_by_index(session_id: str, question_index: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves the exact question with given question_index (1 to 100) for this session.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(QuizQuestion).where(
                and_(
                    QuizQuestion.session_id == session_id,
                    QuizQuestion.question_index == question_index,
                )
            )
        )
        row = res.scalar_one_or_none()
        if not row:
            return None

        options = []
        correct_letter = "A"
        question_hash = ""
        try:
            parsed = json.loads(row.shuffled_options)
            if isinstance(parsed, dict):
                options = parsed.get("options", [])
                correct_letter = parsed.get("correct_letter", "A")
                question_hash = parsed.get("question_hash", "")
            elif isinstance(parsed, list):
                options = parsed
        except Exception:
            options = []

        return {
            "question_id": row.question_id,
            "question_hash": question_hash,
            "question_index": row.question_index,
            "question": row.question_text,
            "options": options,
            "correct_answer": row.correct_answer,
            "correct_letter": correct_letter,
            "exam_name": row.exam_name,
            "exam_year": row.exam_year,
            "topic": row.topic,
            "source_reference": row.source_reference,
        }

async def get_all_running_sessions() -> List[QuizSession]:
    """Retrieves all sessions currently marked RUNNING for restart recovery."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(QuizSession).where(QuizSession.status == "RUNNING").order_by(QuizSession.started_at)
        )
        return list(res.scalars().all())

async def has_user_answered(session_id: str, question_id: str, user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserAnswer).where(
                and_(
                    UserAnswer.session_id == session_id,
                    UserAnswer.question_id == question_id,
                    UserAnswer.user_id == user_id,
                )
            )
        )
        return res.scalar_one_or_none() is not None

async def record_user_answer(
    session_id: str,
    question_id: str,
    user_id: int,
    username: Optional[str],
    selected_option: str,
    is_correct: bool,
    response_time_ms: int = 0,
) -> bool:
    async with AsyncSessionLocal() as session:
        try:
            answer = UserAnswer(
                session_id=session_id,
                question_id=question_id,
                user_id=user_id,
                username=username,
                selected_option=selected_option,
                is_correct=is_correct,
                response_time_ms=response_time_ms,
                answered_at=datetime.utcnow(),
            )
            session.add(answer)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False

async def get_question_stats(session_id: str, question_id: str) -> Dict[str, int]:
    """Returns distribution of votes for each option."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserAnswer.selected_option, func.count(UserAnswer.id))
            .where(
                and_(
                    UserAnswer.session_id == session_id,
                    UserAnswer.question_id == question_id,
                )
            )
            .group_by(UserAnswer.selected_option)
        )
        return {row[0]: row[1] for row in res.all()}

async def get_question_voters(session_id: str, question_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Returns voter details grouped by option for View Votes modal/sheet breakdown."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                UserAnswer.selected_option,
                UserAnswer.username,
                UserAnswer.user_id,
                UserAnswer.answered_at,
            )
            .where(
                and_(
                    UserAnswer.session_id == session_id,
                    UserAnswer.question_id == question_id,
                )
            )
            .order_by(UserAnswer.answered_at)
        )
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in res.all():
            opt = row[0]
            if opt not in grouped:
                grouped[opt] = []
            grouped[opt].append({
                "username": row[1] or f"User_{row[2]}",
                "user_id": row[2],
                "answered_at": row[3],
            })
        return grouped

async def get_session_stats(session_id: str) -> Dict[str, Any]:
    """Returns leaderboard ranking and stats for a completed or stopped session."""
    async with AsyncSessionLocal() as session:
        # Total answers count
        total_answers_res = await session.execute(
            select(
                func.count(UserAnswer.id),
                func.sum(func.cast(UserAnswer.is_correct, Integer)),
            ).where(UserAnswer.session_id == session_id)
        )
        row = total_answers_res.first()
        total_answers = row[0] or 0
        total_correct = row[1] or 0
        total_wrong = total_answers - total_correct

        # Per-user ranking
        user_res = await session.execute(
            select(
                UserAnswer.user_id,
                UserAnswer.username,
                func.sum(func.cast(UserAnswer.is_correct, Integer)).label("correct"),
                func.count(UserAnswer.id).label("total"),
            )
            .where(UserAnswer.session_id == session_id)
            .group_by(UserAnswer.user_id, UserAnswer.username)
            .order_by(desc("correct"), desc("total"))
        )
        users = []
        for r in user_res.all():
            correct = r[2] or 0
            total = r[3] or 0
            wrong = total - correct
            acc = round((correct / total * 100), 1) if total > 0 else 0.0
            users.append({
                "user_id": r[0],
                "username": r[1] or f"User_{r[0]}",
                "correct": correct,
                "wrong": wrong,
                "total": total,
                "accuracy": acc,
            })

        return {
            "total_answers": total_answers,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "participants_count": len(users),
            "rankings": users,
        }

async def update_leaderboard_from_session(session_id: str, group_id: int):
    """Updates group-level persistent leaderboard and global user records."""
    stats = await get_session_stats(session_id)
    async with AsyncSessionLocal() as session:
        for u in stats["rankings"]:
            # Update GroupLeaderboard
            gl_res = await session.execute(
                select(GroupLeaderboard).where(
                    and_(
                        GroupLeaderboard.group_id == group_id,
                        GroupLeaderboard.user_id == u["user_id"],
                    )
                )
            )
            gl = gl_res.scalar_one_or_none()
            if not gl:
                gl = GroupLeaderboard(
                    group_id=group_id,
                    user_id=u["user_id"],
                    username=u["username"],
                    points=u["correct"],
                    correct_count=u["correct"],
                    wrong_count=u["wrong"],
                    quizzes_played=1,
                    last_active=datetime.utcnow(),
                )
                session.add(gl)
            else:
                gl.points += u["correct"]
                gl.correct_count += u["correct"]
                gl.wrong_count += u["wrong"]
                gl.quizzes_played += 1
                gl.username = u["username"]
                gl.last_active = datetime.utcnow()

            # Update User table
            user_res = await session.execute(
                select(User).where(User.user_id == u["user_id"])
            )
            usr = user_res.scalar_one_or_none()
            if not usr:
                usr = User(
                    user_id=u["user_id"],
                    username=u["username"],
                    total_points=u["correct"],
                    correct_answers=u["correct"],
                    wrong_answers=u["wrong"],
                    quizzes_participated=1,
                )
                session.add(usr)
            else:
                usr.total_points += u["correct"]
                usr.correct_answers += u["correct"]
                usr.wrong_answers += u["wrong"]
                usr.quizzes_participated += 1
                usr.username = u["username"]

        await session.commit()


async def get_all_broadcast_destinations() -> Dict[str, List[int]]:
    """
    Collects all unique group and user IDs from existing database tables.
    Groups: Collected from Group and ApprovedGroup tables.
    Users: Collected from User, GroupLeaderboard, and UserAnswer tables.
    Deduplicates IDs and keeps groups and users separately identifiable.
    """
    groups_set = set()
    users_set = set()

    async with AsyncSessionLocal() as session:
        # 1. Collect from Group table
        grp_res = await session.execute(select(Group.group_id))
        for gid in grp_res.scalars().all():
            if gid is not None:
                groups_set.add(int(gid))

        # Collect from ApprovedGroup table
        app_res = await session.execute(select(ApprovedGroup.group_id))
        for gid in app_res.scalars().all():
            if gid is not None:
                groups_set.add(int(gid))

        # 2. Collect from User table
        usr_res = await session.execute(select(User.user_id))
        for uid in usr_res.scalars().all():
            if uid is not None:
                users_set.add(int(uid))

        # Collect from GroupLeaderboard table
        lb_res = await session.execute(select(GroupLeaderboard.user_id))
        for uid in lb_res.scalars().all():
            if uid is not None:
                users_set.add(int(uid))

        # Collect from UserAnswer table
        ans_res = await session.execute(select(UserAnswer.user_id))
        for uid in ans_res.scalars().all():
            if uid is not None:
                users_set.add(int(uid))

    return {
        "groups": sorted(list(groups_set)),
        "users": sorted(list(users_set)),
    }
