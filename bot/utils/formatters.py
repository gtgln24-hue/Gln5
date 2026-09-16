"""
GLN Quiz Bot - Message Formatting Utility
Generates clean, aesthetic Telegram messages matching exact prompt specifications.
"""

from datetime import datetime
import html
from typing import Dict, List, Any, Optional

def format_cooldown_time(cooldown_until: datetime) -> str:
    """Calculates remaining time and formats into 'X hours Y minutes'."""
    remaining = (cooldown_until - datetime.utcnow()).total_seconds()
    if remaining <= 0:
        return "Ready now"

    hours = int(remaining // 3600)
    minutes = int((remaining % 3600) // 60)
    seconds = int(remaining % 60)

    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} second{'s' if seconds != 1 else ''}"
    return f"{seconds} seconds"

def format_question_message(
    current_index: int,
    total_questions: int,
    subject: str,
    question_text: str,
    options: List[str],
    exam_name: Optional[str] = None,
    exam_year: Optional[int] = None,
    topic: Optional[str] = None,
    source_reference: Optional[str] = None,
    time_remaining: int = 15,
    tagline: str = "!!🖤🌹B ⓐ dshah🌹🖤!!",
) -> str:
    """
    Formats the active quiz question with [current/total] prefix, stylized tagline,
    exam metadata, options, and countdown timer.
    """
    letters = ["A", "B", "C", "D"]
    metadata_lines = []

    if exam_name:
        metadata_lines.append(f"📚 <b>Exam:</b> {html.escape(str(exam_name))}")
    if exam_year:
        metadata_lines.append(f"📅 <b>Year:</b> {exam_year}")
    if topic:
        metadata_lines.append(f"📖 <b>Topic:</b> {html.escape(str(topic))}")
    if source_reference:
        metadata_lines.append(f"ℹ️ <b>Source:</b> <i>{html.escape(str(source_reference))}</i>")

    meta_str = "\n".join(metadata_lines)
    if meta_str:
        meta_str = f"{meta_str}\n\n"

    options_str = "\n".join([f"<b>{letters[i]}.</b> {html.escape(str(opt))}" for i, opt in enumerate(options)])

    msg = (
        f"<b>[{current_index}/{total_questions}]</b> <b>{html.escape(str(question_text))}</b>\n"
        f"<i>{html.escape(tagline)}</i>\n\n"
        f"🏷️ <i>Subject: {html.escape(str(subject))}</i>\n"
        f"{meta_str}"
        f"{options_str}\n\n"
        f"⏱️ <b>Time Remaining:</b> {time_remaining} seconds"
    )
    return msg

def format_question_result_message(
    current_index: int,
    total_questions: int,
    correct_letter: str,
    correct_text: str,
    stats: Dict[str, int],
    options: List[str],
    is_last: bool = False,
    question_text: Optional[str] = None,
    tagline: str = "!!🖤🌹B ⓐ dshah🌹🖤!!",
) -> str:
    """
    Formats the post-question result message matching the Telegram Quiz Poll result design:
    - [Index/Total] Question
    - Stylized Tagline: !!🖤🌹B ⓐ dshah🌹🖤!!
    - Final Results 📊
    - Visual percentage bar breakdown with correct answer marked (💡)
    - Total Votes & Next Question indicator
    """
    letters = ["A", "B", "C", "D"]
    total_votes = sum(stats.values())
    poll_lines = []

    for i, opt in enumerate(options):
        count = stats.get(opt, 0)
        pct = int(round((count / total_votes) * 100)) if total_votes > 0 else 0
        
        # Build 10-segment visual progress bar
        filled_blocks = int(round(pct / 10))
        empty_blocks = max(0, 10 - filled_blocks)
        bar = ("▰" * filled_blocks) + ("▱" * empty_blocks)
        
        is_correct = (opt == correct_text)
        bulb = " 💡" if is_correct else ""
        letter_prefix = f"<b>{letters[i]}.</b> " if i < len(letters) else ""
        
        answer_label = "answer" if count == 1 else "answers"
        poll_lines.append(
            f"<b>{pct}%</b> • {letter_prefix}{html.escape(str(opt))}{bulb}\n"
            f"<code>{bar}</code> <i>({count} {answer_label})</i>"
        )

    poll_str = "\n\n".join(poll_lines)

    status_footer = (
        "🏁 <b>Quiz completed! Preparing final rankings...</b>"
        if is_last
        else f"<i>Next question starting...</i>\n\n<b>[{current_index + 1}/{total_questions}]</b>"
    )

    header_title = (
        f"<b>[{current_index}/{total_questions}] {html.escape(str(question_text))}</b>\n"
        if question_text
        else f"<b>[{current_index}/{total_questions}] Question Result</b>\n"
    )

    msg = (
        f"{header_title}"
        f"<i>{html.escape(tagline)}</i>\n\n"
        f"<b>Final Results 📊</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{poll_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <b>सही उत्तर (Correct Answer):</b> <b>{correct_letter}.</b> {html.escape(str(correct_text))}\n"
        f"👥 <b>Total Votes:</b> {total_votes}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_footer}"
    )
    return msg

def format_leaderboard_message(
    title: str,
    total_questions: int,
    stats: Dict[str, Any],
) -> str:
    """
    Formats the final quiz results or stop summary with medals and accuracy statistics.
    """
    rankings = stats.get("rankings", [])
    total_answers = stats.get("total_answers", 0)
    total_correct = stats.get("total_correct", 0)
    total_wrong = stats.get("total_wrong", 0)
    participants_count = stats.get("participants_count", 0)

    medals = ["🥇", "🥈", "🥉"]
    rankings_str = ""

    if not rankings:
        rankings_str = "<i>No answers were recorded during this session.</i>"
    else:
        lines = []
        for i, u in enumerate(rankings[:15]):  # Display top 15
            badge = medals[i] if i < len(medals) else f"<b>{i+1}.</b>"
            user_tag = f"@{html.escape(str(u['username']))}" if u['username'] and not u['username'].startswith("User_") else html.escape(str(u['username']))
            lines.append(
                f"{badge} {user_tag} — <b>{u['correct']} Correct</b> | {u['wrong']} Wrong ({u['accuracy']}%)"
            )
        rankings_str = "\n".join(lines)

    msg = (
        f"{title}\n\n"
        f"📊 <b>FINAL RESULTS</b>\n\n"
        f"{rankings_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Total Questions Asked:</b> {total_questions}\n"
        f"🟢 <b>Correct Answers:</b> {total_correct}\n"
        f"🔴 <b>Wrong Answers:</b> {total_wrong}\n"
        f"👥 <b>Total Participants:</b> {participants_count}"
    )
    return msg
