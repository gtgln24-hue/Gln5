"""
GLN Quiz Bot - Database Models
SQLAlchemy Declarative Models compatible with both PostgreSQL and SQLite.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Group(Base):
    __tablename__ = "groups"

    group_id = Column(BigInteger, primary_key=True, index=True)
    group_name = Column(String(255), nullable=False, default="Unnamed Group")
    group_username = Column(String(255), nullable=True)
    member_count = Column(Integer, default=0)
    added_by_user = Column(String(255), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by_owner = Column(BigInteger, nullable=True)

class ApprovedGroup(Base):
    __tablename__ = "approved_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, unique=True, index=True, nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow)
    approved_by_owner = Column(BigInteger, nullable=False)

class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    total_points = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    wrong_answers = Column(Integer, default=0)
    quizzes_participated = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BotDMUser(Base):
    """Stores every user who has initiated a private conversation with the bot."""
    __tablename__ = "bot_dm_users"

    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    group_id = Column(BigInteger, index=True, nullable=False)
    subject = Column(String(64), nullable=False)
    status = Column(String(32), default="WAITING", nullable=False)  # WAITING, PREPARING, RUNNING, PAUSED, STOPPED, COMPLETED
    current_question = Column(Integer, default=0)
    total_questions = Column(Integer, default=100)
    options_count = Column(Integer, default=4)
    active_message_id = Column(Integer, nullable=True)
    consecutive_empty_answers = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False)
    question_index = Column(Integer, nullable=False)  # 1 to 100
    question_id = Column(String(64), nullable=False)
    question_text = Column(Text, nullable=False)
    shuffled_options = Column(Text, nullable=False)  # JSON string of options
    correct_answer = Column(Text, nullable=False)
    exam_name = Column(String(128), nullable=True)
    exam_year = Column(Integer, nullable=True)
    topic = Column(String(255), nullable=True)
    source_reference = Column(Text, nullable=True)

class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False)
    question_id = Column(String(64), index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    selected_option = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, default=0)
    answered_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", "user_id", name="uq_user_question_answer"),
    )

class SubjectCooldown(Base):
    __tablename__ = "subject_cooldowns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, index=True, nullable=False)
    subject = Column(String(64), nullable=False)
    cooldown_until = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "subject", name="uq_group_subject_cooldown"),
    )

class QuestionBank(Base):
    __tablename__ = "question_bank"

    question_id = Column(String(64), primary_key=True)
    subject = Column(String(64), index=True, nullable=False)
    question = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)  # JSON string of all candidate options
    exam_name = Column(String(128), nullable=True)
    exam_year = Column(Integer, nullable=True)
    topic = Column(String(255), nullable=True)
    source_reference = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UsedQuestion(Base):
    __tablename__ = "used_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, index=True, nullable=False)
    subject = Column(String(64), index=True, nullable=False)
    question_hash = Column(String(64), index=True, nullable=False)
    question_text = Column(Text, nullable=False)
    quiz_session_id = Column(String(64), index=True, nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("group_id", "subject", "question_hash", name="uq_group_subject_question_hash"),
    )

class GroupLeaderboard(Base):
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    points = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    quizzes_played = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user_leaderboard"),
    )
