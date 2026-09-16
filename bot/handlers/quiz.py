"""
GLN Quiz Bot - Interactive Callback Handlers
Processes subject selection, option count selection, individual user answers, and pause/resume.
"""

import logging
import html
from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PollAnswer
from bot.services.quiz_service import quiz_manager
from bot.services.cooldown_service import check_subject_availability
from bot.utils.permissions import is_group_admin_or_owner
from bot.config import settings
from bot.database.queries import get_question_voters, get_question_stats, record_user_answer

logger = logging.getLogger(__name__)
quiz_router = Router()

def normalize_subject_name(raw: str) -> str:
    """Normalize callback subject to standard configuration casing."""
    clean = raw.strip().upper()
    mapping = {
        "HINDI": "Hindi",
        "SAMAJIK VIGYAN": "Samajik Vigyan",
        "SAMAJIK_VIGYAN": "Samajik Vigyan",
        "ITIHAS": "Itihas",
        "SCIENCE": "Science",
        "BOTANY": "Botany",
        "ZOOLOGY": "Zoology",
        "MATHS": "Mathematics",
        "MATHEMATICS": "Mathematics",
        "CHEMISTRY": "Chemistry",
    }
    return mapping.get(clean, raw.strip())

@quiz_router.callback_query(F.data.startswith("choose_subject:") | F.data.startswith("subj:"))
async def on_subject_selected(call: CallbackQuery, bot: Bot):
    """
    Fires when an admin selects a subject from /Choose keyboard.
    Checks 3-hour cooldown and prompts for number of options.
    """
    raw_subject = call.data.split(":", 1)[1]
    subject = normalize_subject_name(raw_subject)
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    # Verify admin permissions
    is_admin = await is_group_admin_or_owner(bot, chat_id, user_id)
    if not is_admin:
        await call.answer("❌ Only Group Admins or Owners can configure the quiz.", show_alert=True)
        return

    # Check 3-hour subject cooldown
    is_available, error_msg = await check_subject_availability(chat_id, subject)
    if not is_available:
        await call.answer()
        await call.message.edit_text(error_msg, parse_mode="HTML")
        return

    # Show Options Count Selection
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="2 Options", callback_data=f"options_count:{subject}:2"),
                InlineKeyboardButton(text="3 Options", callback_data=f"options_count:{subject}:3"),
                InlineKeyboardButton(text="4 Options", callback_data=f"options_count:{subject}:4"),
            ]
        ]
    )

    display_name = settings.SUBJECT_DISPLAY_NAMES.get(subject, subject)
    await call.answer()
    await call.message.edit_text(
        f"🎯 <b>SELECT NUMBER OF OPTIONS</b>\n\n"
        f"Subject: <b>{display_name}</b>\n\n"
        f"How many options should each question have?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )

@quiz_router.callback_query(F.data.startswith("options_count:") | F.data.startswith("opts:"))
async def on_options_count_selected(call: CallbackQuery, bot: Bot):
    """
    Fires when an admin selects 2, 3, or 4 options.
    Prepares 100 questions and starts the quiz session.
    """
    parts = call.data.split(":")
    if len(parts) == 3:
        raw_subject = parts[1]
        subject = normalize_subject_name(raw_subject)
        options_count = int(parts[2])
    elif len(parts) == 2:
        # options_count:4 (default to last subject or Hindi)
        subject = "Hindi"
        options_count = int(parts[1])
    else:
        subject = "Hindi"
        options_count = 4

    chat_id = call.message.chat.id
    user_id = call.from_user.id

    is_admin = await is_group_admin_or_owner(bot, chat_id, user_id)
    if not is_admin:
        await call.answer("❌ Only Group Admins or Owners can start the quiz.", show_alert=True)
        return

    # Final cooldown check
    is_available, error_msg = await check_subject_availability(chat_id, subject)
    if not is_available:
        await call.answer()
        await call.message.edit_text(error_msg, parse_mode="HTML")
        return

    display_name = settings.SUBJECT_DISPLAY_NAMES.get(subject, subject)
    await call.answer("Preparing 100 questions...")
    await call.message.edit_text(
        f"⏳ <b>PREPARING 100 UNIQUE QUESTIONS...</b>\n\n"
        f"📚 <b>Subject:</b> {display_name}\n"
        f"🎯 <b>Format:</b> {options_count} Options per question\n"
        f"⏱️ <b>Timer:</b> 15 seconds per question\n\n"
        f"<i>Quiz is starting now! Get ready!</i>",
        parse_mode="HTML",
    )

    # Launch quiz
    await quiz_manager.start_new_quiz(
        bot=bot,
        group_id=chat_id,
        subject=subject,
        options_count=options_count,
    )

@quiz_router.callback_query(F.data.startswith("ans:"))
async def on_user_answer(call: CallbackQuery, bot: Bot):
    """
    Handles user answer submissions from any group participant.
    Delivers immediate private feedback popup (🟢 Correct / 🔴 Wrong) without revealing public votes prematurely.
    """
    parts = call.data.split(":")
    session_id = parts[1]
    question_id = parts[2]
    selected_letter = parts[3]

    user = call.from_user
    username = user.username or user.first_name or f"User_{user.id}"

    result = await quiz_manager.handle_user_answer(
        session_id=session_id,
        question_id=question_id,
        user_id=user.id,
        username=username,
        selected_letter=selected_letter,
    )

    # Show private popup alert to user
    await call.answer(text=result.get("alert", "Submitted"), show_alert=True)

@quiz_router.callback_query(F.data.startswith("resume_quiz") | F.data.startswith("resume:"))
async def on_resume_quiz(call: CallbackQuery, bot: Bot):
    """
    Resumes a paused quiz from the current question.
    Only group administrators or owners may resume.
    """
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    is_admin = await is_group_admin_or_owner(bot, chat_id, user_id)
    if not is_admin:
        await call.answer("❌ Only Group Admins can resume the quiz.", show_alert=True)
        return

    active = quiz_manager.get_active(chat_id)
    session_id = active.session_id if active else (data.split(":", 1)[1] if ":" in data else "")

    if not session_id:
        await call.answer("⚠️ No quiz session to resume.", show_alert=True)
        return

    await call.answer("Resuming quiz...")
    try:
        await call.message.delete()
    except Exception:
        pass

    await quiz_manager.resume_quiz(bot, chat_id, session_id)

@quiz_router.callback_query(F.data.startswith("view_votes:"))
async def on_view_votes(call: CallbackQuery, bot: Bot):
    """
    Shows detailed votes breakdown (who answered what and percentages)
    matching the View Votes screen from the video.
    """
    parts = call.data.split(":")
    if len(parts) < 3:
        await call.answer("Data error", show_alert=True)
        return

    session_id = parts[1]
    question_id = parts[2]

    try:
        voters_by_opt = await get_question_voters(session_id, question_id)
        stats = await get_question_stats(session_id, question_id)
        total_votes = sum(stats.values())

        if total_votes == 0:
            await call.answer("📊 Abhi tak koi votes nahi mile.", show_alert=True)
            return

        lines = ["📊 <b>VOTES BREAKDOWN (परिणाम विवरण):</b>\n"]
        for opt, count in stats.items():
            pct = int(round((count / total_votes) * 100)) if total_votes > 0 else 0
            voters = voters_by_opt.get(opt, [])
            voter_names = ", ".join([html.escape(v.get("username", "User")) for v in voters[:6]])
            if len(voters) > 6:
                voter_names += f" +{len(voters) - 6} more"
            
            lines.append(f"• <b>{html.escape(str(opt))}</b> — <b>{pct}%</b> ({count} answer{'s' if count != 1 else ''})")
            if voter_names:
                lines.append(f"  👤 <i>{voter_names}</i>")
            lines.append("")

        breakdown_text = "\n".join(lines)
        await call.message.reply(breakdown_text, parse_mode="HTML")
        await call.answer()
    except Exception as e:
        logger.exception(f"Error handling view_votes: {e}")
        await call.answer("❌ Error loading votes breakdown", show_alert=True)

@quiz_router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer, bot: Bot):
    """
    Handles native Telegram Poll answers (non-anonymous quiz polls).
    Records user's vote and score in the database.
    """
    poll_id = poll_answer.poll_id
    info = quiz_manager.polls_to_session.get(poll_id)
    if not info:
        return
    session_id, question_id, question_index = info
    state = quiz_manager.get_by_session_id(session_id)
    if not state or not state.is_accepting_answers:
        return

    q_data = state.current_question_data
    if not q_data:
        return

    user_id = poll_answer.user.id
    username = poll_answer.user.username or poll_answer.user.full_name or f"User_{user_id}"

    if not poll_answer.option_ids:
        return

    selected_idx = poll_answer.option_ids[0]
    options = q_data.get("options", [])
    selected_option = options[selected_idx] if selected_idx < len(options) else str(selected_idx)
    correct_answer = q_data.get("correct_answer", "")
    try:
        correct_idx = options.index(correct_answer)
    except ValueError:
        correct_letter = q_data.get("correct_letter", "A").upper()
        letters = ["A", "B", "C", "D"]
        correct_idx = letters.index(correct_letter) if correct_letter in letters else 0

    is_correct = (selected_idx == correct_idx)

    await record_user_answer(
        session_id=session_id,
        question_id=question_id,
        user_id=user_id,
        username=username,
        selected_option=selected_option,
        is_correct=is_correct,
    )
    logger.info(
        f"[POLL VOTE] session={session_id} q={question_index} user={username} ({user_id}) opt={selected_option} correct={is_correct}"
    )
