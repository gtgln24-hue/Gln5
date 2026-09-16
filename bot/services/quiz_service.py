"""
GLN Quiz Bot - Core Quiz Lifecycle Service
Coordinates quiz state machine, 15-second question pacing, private answer feedback,
timeout result broadcasts, inactivity auto-pause, resume, and 3-hour cooldown trigger.
Enforces strict concurrency safety with quiz_locks[session_id], single-timer guarantees,
and reliable question progression from 1 to 100 without stopping.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings
from bot.database.models import QuizSession
from bot.database.queries import (
    get_active_session,
    get_session_by_id,
    get_all_running_sessions,
    update_session_status,
    update_session_question,
    get_session_question_by_index,
    has_user_answered,
    record_user_answer,
    get_question_stats,
    get_session_stats,
    update_leaderboard_from_session,
    get_or_create_group,
)
from bot.database.db import AsyncSessionLocal
from bot.services.question_service import QuestionQueueManager
from bot.services.timer_service import timer_manager
from bot.services.cooldown_service import apply_subject_cooldown
from bot.utils.formatters import (
    format_question_message,
    format_question_result_message,
    format_leaderboard_message,
)

logger = logging.getLogger(__name__)

# Global session locks to prevent race conditions during timer callbacks and question dispatch
quiz_locks: Dict[str, asyncio.Lock] = {}

def get_quiz_lock(session_id: str) -> asyncio.Lock:
    """Returns the dedicated asyncio.Lock for a quiz session."""
    if session_id not in quiz_locks:
        quiz_locks[session_id] = asyncio.Lock()
    return quiz_locks[session_id]

class ActiveQuizState:
    """Represents in-memory state of an active quiz session."""
    def __init__(self, session_id: str, group_id: int, subject: str, options_count: int):
        self.session_id = session_id
        self.group_id = group_id
        self.subject = subject
        self.options_count = options_count
        # Question numbering: 1-based (1 to 100)
        self.current_question = 1
        self.total_questions = settings.TOTAL_QUESTIONS
        self.current_question_data: Optional[Dict[str, Any]] = None
        self.message_id: Optional[int] = None
        self.poll_id: Optional[str] = None
        self.is_poll: bool = False
        self.is_accepting_answers = False
        self.consecutive_empty_answers = 0
        self.queue_manager = QuestionQueueManager(session_id, group_id, subject, options_count)

    @property
    def current_index(self) -> int:
        return self.current_question

    @current_index.setter
    def current_index(self, val: int):
        self.current_question = val

class QuizManager:
    def __init__(self):
        # Maps group_id -> ActiveQuizState
        self.active_sessions: Dict[int, ActiveQuizState] = {}
        # Maps session_id -> ActiveQuizState
        self.sessions_by_id: Dict[str, ActiveQuizState] = {}
        # Tracks active timer tasks per session
        self.active_quiz_tasks: Dict[str, asyncio.Task] = {}
        # Maps poll_id -> (session_id, question_id, question_index)
        self.polls_to_session: Dict[str, Any] = {}

    def get_session_lock(self, session_id: str) -> asyncio.Lock:
        return get_quiz_lock(session_id)

    def get_active(self, group_id: int) -> Optional[ActiveQuizState]:
        return self.active_sessions.get(group_id)

    def get_by_session_id(self, session_id: str) -> Optional[ActiveQuizState]:
        return self.sessions_by_id.get(session_id)

    async def start_new_quiz(
        self,
        bot: Bot,
        group_id: int,
        subject: str,
        options_count: int,
    ) -> ActiveQuizState:
        """
        Initializes a fresh 100-question quiz session.
        Prepares and persists the 100 unique questions, records the session in DB,
        and dispatches Question 1/100.
        """
        session_id = f"gln_{uuid.uuid4().hex[:12]}"
        state = ActiveQuizState(session_id, group_id, subject, options_count)
        self.active_sessions[group_id] = state
        self.sessions_by_id[session_id] = state

        logger.info(f"[QUIZ START] session={session_id} question=1/{state.total_questions}")

        # Prepare 100 strictly unique questions in background queue and persist to DB
        await state.queue_manager.initialize()

        # Ensure group is recorded in database
        try:
            await get_or_create_group(group_id=group_id, group_name="Telegram Group")
        except Exception as e:
            logger.debug(f"Group record notice: {e}")

        # Record in database with current_question = 1
        async with AsyncSessionLocal() as session:
            qs = QuizSession(
                session_id=session_id,
                group_id=group_id,
                subject=subject,
                status="RUNNING",
                current_question=1,
                total_questions=state.total_questions,
                options_count=options_count,
                started_at=datetime.utcnow(),
                last_active_at=datetime.utcnow(),
            )
            session.add(qs)
            await session.commit()

        # Dispatch first question (Question 1/100)
        await self.send_next_question(session_id, bot)
        return state

    def build_options_keyboard(self, session_id: str, question_id: str, count: int) -> InlineKeyboardMarkup:
        """
        Creates clean inline buttons for options [A, B] or [A, B, C] or [A, B, C, D].
        """
        letters = ["A", "B", "C", "D"][:count]
        buttons = [
            InlineKeyboardButton(
                text=f"{let}",
                callback_data=f"ans:{session_id}:{question_id}:{let}"
            )
            for let in letters
        ]

        rows = [buttons[:2]]
        if len(buttons) > 2:
            rows.append(buttons[2:])

        return InlineKeyboardMarkup(inline_keyboard=rows)

    async def send_next_question(self, session_id_or_bot: Any, bot_or_target: Any = None):
        """
        THE ONE CENTRAL FUNCTION for question dispatch.
        Responsibilities:
        - Checks if quiz session is still ACTIVE (status == 'RUNNING')
        - Reads current_question index from state/DB
        - If index > total_questions: finishes quiz
        - Loads question data deterministically from pre-generated queue/DB
        - Formats question message with countdown and exam metadata
        - Sends question message to Telegram with safe retry
        - Updates DB with message_id and timestamp
        - Starts the countdown timer and registers task in active_quiz_tasks[session_id]
        """
        # Flexible argument resolution: handles (session_id, bot) or (bot, group_id/session_id)
        if isinstance(session_id_or_bot, Bot):
            bot = session_id_or_bot
            target = bot_or_target
            if isinstance(target, int):
                st = self.get_active(target)
                session_id = st.session_id if st else ""
            else:
                session_id = str(target)
        else:
            session_id = str(session_id_or_bot)
            bot = bot_or_target

        if not session_id:
            logger.error("[QUIZ ERROR] send_next_question called without valid session_id")
            return

        # Fetch state from memory or recover from DB
        state = self.get_by_session_id(session_id)
        if not state:
            db_sess = await get_session_by_id(session_id)
            if db_sess and db_sess.status == "RUNNING":
                state = ActiveQuizState(
                    session_id=db_sess.session_id,
                    group_id=db_sess.group_id,
                    subject=db_sess.subject,
                    options_count=db_sess.options_count,
                )
                state.current_question = db_sess.current_question
                self.active_sessions[db_sess.group_id] = state
                self.sessions_by_id[session_id] = state
            else:
                logger.warning(f"Session {session_id} not found or inactive. Aborting send.")
                return

        lock = self.get_session_lock(session_id)
        async with lock:
            # Cancel any lingering previous timer before sending new question
            timer_manager.cancel_timer(session_id)
            if session_id in self.active_quiz_tasks:
                old_task = self.active_quiz_tasks.pop(session_id, None)
                if old_task and not old_task.done():
                    old_task.cancel()

            # Verify session is still RUNNING in DB
            db_sess = await get_session_by_id(session_id)
            if not db_sess or db_sess.status != "RUNNING":
                logger.info(
                    f"Session {session_id} is '{db_sess.status if db_sess else 'None'}'. Aborting send."
                )
                return

            current_q = state.current_question
            if current_q > state.total_questions:
                logger.info(
                    f"[QUIZ COMPLETE] session={session_id} current_q={current_q} exceeds total={state.total_questions}"
                )
                should_finish = True
            else:
                should_finish = False

        if should_finish:
            await self.finish_quiz(bot, session_id)
            return

        # Fetch question data using deterministic order (1 to 100)
        q_data = await state.queue_manager.get_question_by_order(current_q)
        if not q_data:
            # Fallback to direct DB query
            q_data = await get_session_question_by_index(session_id, current_q)

        if not q_data:
            logger.error(
                f"[QUIZ ERROR] session={session_id} question={current_q}: Failed to load question data."
            )
            await self.finish_quiz(bot, session_id)
            return

        state.current_question_data = q_data

        # Determine timer duration (supports test mode if configured)
        timer_seconds = (
            settings.TEST_TIMER_SECONDS
            if getattr(settings, "TEST_TIMER_SECONDS", None) is not None
            else settings.QUESTION_TIMER_SECONDS
        )

        options = q_data["options"]
        correct_answer = q_data.get("correct_answer", "")
        try:
            correct_idx = options.index(correct_answer)
        except ValueError:
            correct_letter = q_data.get("correct_letter", "A").upper()
            letters = ["A", "B", "C", "D"]
            correct_idx = letters.index(correct_letter) if correct_letter in letters else 0

        # Build clean question text (Telegram poll question limit is 300 chars)
        poll_question = f"[{current_q}/{state.total_questions}] {q_data['question']}".strip()
        if len(poll_question) > 300:
            poll_question = poll_question[:297] + "..."

        # Send native Telegram Quiz Poll (matching Telegram Quiz Bot design)
        sent_msg = None
        is_poll = False
        poll_period = max(5, min(600, timer_seconds))

        for attempt in range(1, 4):
            try:
                # Use native Telegram Quiz Poll
                sent_msg = await bot.send_poll(
                    chat_id=state.group_id,
                    question=poll_question,
                    options=options,
                    type="quiz",
                    correct_option_id=correct_idx,
                    is_anonymous=False,
                    open_period=poll_period,
                    is_closed=False,
                )
                is_poll = True
                break
            except Exception as poll_err:
                logger.warning(
                    f"[NATIVE POLL FALLBACK] session={session_id} question={current_q} attempt {attempt}: {poll_err}"
                )
                try:
                    text = format_question_message(
                        current_index=current_q,
                        total_questions=state.total_questions,
                        subject=state.subject,
                        question_text=q_data["question"],
                        options=q_data["options"],
                        exam_name=q_data.get("exam_name"),
                        exam_year=q_data.get("exam_year"),
                        topic=q_data.get("topic"),
                        source_reference=q_data.get("source_reference"),
                        time_remaining=timer_seconds,
                    )
                    keyboard = self.build_options_keyboard(
                        state.session_id, q_data["question_id"], state.options_count
                    )
                    sent_msg = await bot.send_message(
                        chat_id=state.group_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    is_poll = False
                    break
                except Exception as msg_err:
                    logger.exception(
                        f"[QUIZ ERROR] session={session_id} question={current_q} send attempt {attempt} failed: {msg_err}"
                    )
                    if attempt < 3:
                        await asyncio.sleep(1.5 * attempt)

        if not sent_msg:
            logger.critical(
                f"[QUIZ ERROR] session={session_id} question={current_q}: Failed to dispatch question after 3 attempts."
            )
            return

        state.message_id = sent_msg.message_id
        state.is_poll = is_poll
        if is_poll and hasattr(sent_msg, "poll") and sent_msg.poll:
            state.poll_id = sent_msg.poll.id
            self.polls_to_session[sent_msg.poll.id] = (
                session_id,
                q_data["question_id"],
                current_q,
            )

        state.is_accepting_answers = True

        # Update database with current question and message ID
        await update_session_question(
            session_id=session_id,
            current_question=current_q,
            active_message_id=sent_msg.message_id,
            consecutive_empty=state.consecutive_empty_answers,
        )

        logger.info(
            f"[QUESTION SEND] session={session_id} question={current_q}/{state.total_questions}"
        )

        # Start countdown timer and store task in active_quiz_tasks[session_id]
        task = timer_manager.start_question_timer(
            session_id=session_id,
            question_index=current_q,
            duration_seconds=timer_seconds,
            timeout_coro_fn=lambda: self.handle_question_timeout(session_id, bot, current_q),
        )
        self.active_quiz_tasks[session_id] = task

    async def handle_user_answer(
        self,
        session_id: str,
        question_id: str,
        user_id: int,
        username: Optional[str],
        selected_letter: str,
    ) -> Dict[str, Any]:
        """
        Evaluates user answer:
        - Prevents duplicate answers per user.
        - Delivers private callback popup: 🟢 Correct Answer ✅ or 🔴 Wrong Answer ❌.
        """
        state = self.get_by_session_id(session_id)
        if not state:
            for s in self.active_sessions.values():
                if s.session_id == session_id:
                    state = s
                    break

        if not state or not state.is_accepting_answers:
            return {"status": "expired", "alert": "⏱️ Time has expired for this question."}

        already_answered = await has_user_answered(session_id, question_id, user_id)
        if already_answered:
            return {"status": "duplicate", "alert": "⚠️ You have already answered this question."}

        q_data = state.current_question_data
        if not q_data or q_data.get("question_id") != question_id:
            return {"status": "invalid", "alert": "⚠️ Question no longer active."}

        correct_letter = q_data.get("correct_letter", "A")
        is_correct = (selected_letter.strip().upper() == correct_letter.strip().upper())

        letters = ["A", "B", "C", "D"]
        idx = letters.index(selected_letter) if selected_letter in letters else 0
        options = q_data.get("options", [])
        selected_text = options[idx] if idx < len(options) else selected_letter

        await record_user_answer(
            session_id=session_id,
            question_id=question_id,
            user_id=user_id,
            username=username,
            selected_option=selected_text,
            is_correct=is_correct,
        )

        alert_text = "🟢 Correct Answer\n✅" if is_correct else "🔴 Wrong Answer\n❌"
        return {"status": "recorded", "alert": alert_text, "is_correct": is_correct}

    async def handle_question_timeout(self, session_id_or_bot: Any, bot_or_target: Any, question_index: int):
        """
        Fires automatically after timer expiration:
        1. Acquires quiz_locks[session_id]
        2. Validates session status and question_index to prevent stale callbacks
        3. Locks Question (removes inline reply keyboard from Telegram)
        4. Shows correct answer & statistics broadcast
        5. Advances question index (1 -> 2 -> ... -> 100)
        6. Dispatches send_next_question(session_id, bot)
        """
        # Flexible argument resolution: handles (session_id, bot, question_index) or (bot, group_id, question_index)
        if isinstance(session_id_or_bot, Bot):
            bot = session_id_or_bot
            target = bot_or_target
            if isinstance(target, int):
                st = self.get_active(target)
                session_id = st.session_id if st else ""
            else:
                session_id = str(target)
        else:
            session_id = str(session_id_or_bot)
            bot = bot_or_target

        if not session_id:
            logger.error("[QUIZ ERROR] handle_question_timeout called without valid session_id")
            return

        lock = self.get_session_lock(session_id)
        action = None
        state = None

        async with lock:
            state = self.get_by_session_id(session_id)
            if not state:
                for s in self.active_sessions.values():
                    if s.session_id == session_id:
                        state = s
                        break

            if not state:
                logger.warning(f"Session {session_id} not found in memory during timeout.")
                return

            db_sess = await get_session_by_id(session_id)
            if not db_sess or db_sess.status != "RUNNING":
                logger.info(f"Session {session_id} is no longer RUNNING. Skipping timeout handler.")
                return

            # Prevent stale or duplicate timeout executions
            if state.current_question != question_index or not state.is_accepting_answers:
                logger.info(
                    f"[TIMEOUT SKIP] session={session_id} incoming={question_index} "
                    f"current={state.current_question} accepting={state.is_accepting_answers}"
                )
                return

            # Cancel active timer reference safely
            timer_manager.cancel_timer(session_id)
            self.active_quiz_tasks.pop(session_id, None)

            # Lock Question in Telegram
            state.is_accepting_answers = False
            logger.info(f"[QUESTION LOCKED] session={session_id} question={question_index}")

            # Close poll or remove inline buttons in non-blocking task so next question is dispatched without delay
            if state.message_id:
                old_mid = state.message_id
                gid = state.group_id
                if state.is_poll:
                    async def _close_poll():
                        try:
                            await bot.stop_poll(chat_id=gid, message_id=old_mid)
                        except Exception:
                            pass
                    asyncio.create_task(_close_poll())
                else:
                    async def _remove_markup():
                        try:
                            await bot.edit_message_reply_markup(chat_id=gid, message_id=old_mid, reply_markup=None)
                        except Exception:
                            pass
                    asyncio.create_task(_remove_markup())

            # Step 2: Track statistics and consecutive empty answers
            q_data = state.current_question_data
            if q_data:
                stats = await get_question_stats(session_id, q_data["question_id"])
                total_answers = sum(stats.values())

                if total_answers == 0:
                    state.consecutive_empty_answers += 1
                else:
                    state.consecutive_empty_answers = 0

                is_last = (question_index >= state.total_questions)

                # If question was sent as text message (fallback), send text results
                if not state.is_poll:
                    result_text = format_question_result_message(
                        current_index=question_index,
                        total_questions=state.total_questions,
                        correct_letter=q_data["correct_letter"],
                        correct_text=q_data["correct_answer"],
                        stats=stats,
                        options=q_data["options"],
                        is_last=is_last,
                        question_text=q_data.get("question", ""),
                    )

                    result_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=f"📊 View Votes ({total_answers})",
                                    callback_data=f"view_votes:{session_id}:{q_data['question_id']}"
                                )
                            ]
                        ]
                    ) if total_answers > 0 else None

                    try:
                        await bot.send_message(
                            chat_id=state.group_id,
                            text=result_text,
                            parse_mode="HTML",
                            reply_markup=result_markup,
                        )
                    except Exception as e:
                        logger.exception(
                            f"[QUIZ ERROR] session={session_id} question={question_index} result send failed: {e}"
                        )

                # Check inactivity pause
                if state.consecutive_empty_answers >= settings.MAX_UNANSWERED_QUESTIONS_FOR_PAUSE:
                    action = "PAUSE"

            if not action:
                if question_index >= state.total_questions:
                    action = "FINISH"
                else:
                    action = "ADVANCE"
                    next_q = question_index + 1
                    state.current_question = next_q
                    await update_session_question(
                        session_id=session_id,
                        current_question=next_q,
                        consecutive_empty=state.consecutive_empty_answers,
                    )
                    logger.info(
                        f"[NEXT QUESTION] session={session_id} from={question_index} to={next_q}"
                    )

        # Execute transitions outside the lock to prevent deadlocks
        if action == "PAUSE":
            await self.pause_quiz(bot, state.group_id, reason="No participants are currently answering.")
        elif action == "FINISH":
            await self.finish_quiz(bot, session_id)
        elif action == "ADVANCE":
            # Instant transition to next question without delay
            await self.send_next_question(session_id, bot)

    async def pause_quiz(self, bot: Bot, target: Any, reason: str = "Quiz paused by admin."):
        """Pauses the active quiz session."""
        if isinstance(target, int):
            state = self.get_active(target)
        else:
            state = self.get_by_session_id(str(target))

        if not state:
            return

        timer_manager.cancel_timer(state.session_id)
        self.active_quiz_tasks.pop(state.session_id, None)
        state.is_accepting_answers = False

        await update_session_status(state.session_id, "PAUSED")

        resume_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="▶️ Resume Quiz", callback_data=f"resume:{state.session_id}")
            ]]
        )

        display_num = state.current_question
        pause_text = (
            f"⏸️ <b>Quiz Paused</b>\n\n"
            f"{reason}\n\n"
            f"<i>The quiz will resume from Question {display_num}/{state.total_questions}.</i>"
        )

        try:
            await bot.send_message(
                chat_id=state.group_id,
                text=pause_text,
                parse_mode="HTML",
                reply_markup=resume_keyboard,
            )
        except Exception as e:
            logger.error(f"Error sending pause message in {state.group_id}: {e}")

    async def resume_quiz(self, bot: Bot, group_id: int, session_id: str):
        """Resumes a paused quiz from its current question."""
        state = self.get_by_session_id(session_id)
        if not state:
            state = self.get_active(group_id)

        if not state or state.session_id != session_id:
            return

        state.consecutive_empty_answers = 0
        await update_session_status(state.session_id, "RUNNING")

        display_num = state.current_question
        try:
            await bot.send_message(
                chat_id=group_id,
                text=f"▶️ <b>Resuming quiz from Question {display_num}/{state.total_questions}...</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

        await self.send_next_question(session_id, bot)

    async def stop_quiz(self, bot: Bot, target: Any, stopped_by_username: str = "Admin"):
        """Stops an active quiz session immediately and applies 3-hour cooldown."""
        if isinstance(target, int):
            state = self.get_active(target)
        else:
            state = self.get_by_session_id(str(target))

        if not state:
            return

        timer_manager.cancel_timer(state.session_id)
        self.active_quiz_tasks.pop(state.session_id, None)
        state.is_accepting_answers = False

        stats = await get_session_stats(state.session_id)
        await update_leaderboard_from_session(state.session_id, state.group_id)
        await update_session_status(state.session_id, "STOPPED")

        await apply_subject_cooldown(state.group_id, state.subject)

        result_text = format_leaderboard_message(
            title=f"🏁 <b>QUIZ STOPPED</b>\n<i>Stopped by @{stopped_by_username}</i>",
            total_questions=state.current_question,
            stats=stats,
        )

        cooldown_notice = (
            f"\n\n⏳ <b>Cooldown Applied:</b> {state.subject} is now on cooldown for 3 hours in this group.\n"
            f"<i>Other subjects are immediately available via /Choose.</i>"
        )

        try:
            await bot.send_message(
                chat_id=state.group_id,
                text=result_text + cooldown_notice,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error sending stop leaderboard in {state.group_id}: {e}")
        finally:
            self.active_sessions.pop(state.group_id, None)
            self.sessions_by_id.pop(state.session_id, None)

    async def finish_quiz(self, bot: Bot, target: Any):
        """Concludes a completed quiz session (100 questions) and publishes leaderboard."""
        if isinstance(target, int):
            state = self.get_active(target)
        else:
            state = self.get_by_session_id(str(target))

        if not state:
            return

        timer_manager.cancel_timer(state.session_id)
        self.active_quiz_tasks.pop(state.session_id, None)
        state.is_accepting_answers = False

        stats = await get_session_stats(state.session_id)
        await update_leaderboard_from_session(state.session_id, state.group_id)
        await update_session_status(state.session_id, "COMPLETED")

        await apply_subject_cooldown(state.group_id, state.subject)

        result_text = format_leaderboard_message(
            title="🏆 <b>QUIZ COMPLETED</b>",
            total_questions=state.total_questions,
            stats=stats,
        )

        cooldown_notice = (
            f"\n\n⏳ <b>Cooldown Applied:</b> {state.subject} is now on cooldown for 3 hours.\n"
            f"<i>Other subjects remain immediately available via /Choose.</i>"
        )

        try:
            await bot.send_message(
                chat_id=state.group_id,
                text=result_text + cooldown_notice,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error sending completed leaderboard in {state.group_id}: {e}")
        finally:
            self.active_sessions.pop(state.group_id, None)
            self.sessions_by_id.pop(state.session_id, None)

    async def recover_active_quizzes(self, bot: Bot):
        """
        BOT RESTART RECOVERY:
        Scans database on startup for sessions marked RUNNING:
        - Reconstructs in-memory session state
        - Checks elapsed time for active question
        - If timer expired while offline: triggers transition immediately
        - If timer still valid: resumes remaining timer countdown
        """
        try:
            running_sessions = await get_all_running_sessions()
            if not running_sessions:
                logger.info("No active quiz sessions requiring recovery.")
                return

            logger.info(f"Found {len(running_sessions)} active quiz session(s) to recover.")
            timer_duration = (
                settings.TEST_TIMER_SECONDS
                if getattr(settings, "TEST_TIMER_SECONDS", None) is not None
                else settings.QUESTION_TIMER_SECONDS
            )

            for sess in running_sessions:
                session_id = sess.session_id
                state = ActiveQuizState(
                    session_id=session_id,
                    group_id=sess.group_id,
                    subject=sess.subject,
                    options_count=sess.options_count,
                )
                state.current_question = sess.current_question
                state.message_id = sess.active_message_id
                self.active_sessions[sess.group_id] = state
                self.sessions_by_id[session_id] = state

                # Load question data from DB
                q_data = await get_session_question_by_index(session_id, sess.current_question)
                state.current_question_data = q_data

                last_active = sess.last_active_at or sess.started_at or datetime.utcnow()
                elapsed = (datetime.utcnow() - last_active).total_seconds()
                remaining = timer_duration - elapsed

                if remaining <= 0:
                    logger.info(
                        f"[RECOVERY] session={session_id} question={sess.current_question} "
                        f"timer expired during offline period (elapsed {elapsed:.1f}s). Triggering timeout immediately."
                    )
                    state.is_accepting_answers = True
                    asyncio.create_task(
                        self.handle_question_timeout(session_id, bot, sess.current_question)
                    )
                else:
                    logger.info(
                        f"[RECOVERY] session={session_id} question={sess.current_question} "
                        f"resuming timer with {remaining:.1f}s remaining."
                    )
                    state.is_accepting_answers = True
                    task = timer_manager.start_question_timer(
                        session_id=session_id,
                        question_index=sess.current_question,
                        duration_seconds=int(remaining),
                        timeout_coro_fn=lambda s=session_id, q=sess.current_question: self.handle_question_timeout(s, bot, q),
                    )
                    self.active_quiz_tasks[session_id] = task

        except Exception as e:
            logger.exception(f"Error during recover_active_quizzes: {e}")

quiz_manager = QuizManager()
