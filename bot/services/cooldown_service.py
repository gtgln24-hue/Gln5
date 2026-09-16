"""
GLN Quiz Bot - Subject Cooldown Service
Enforces strict 3-hour cooldown per subject per group, preserving availability of other subjects.
"""

from datetime import datetime
from typing import Optional, Tuple
from bot.database.queries import get_subject_cooldown, set_subject_cooldown
from bot.utils.formatters import format_cooldown_time
from bot.config import settings

async def check_subject_availability(group_id: int, subject: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if the given subject is available in the specified group.
    Returns (is_available, error_message_or_none).
    """
    cooldown_until = await get_subject_cooldown(group_id, subject)
    if cooldown_until and cooldown_until > datetime.utcnow():
        formatted_time = format_cooldown_time(cooldown_until)
        subject_display = settings.SUBJECT_DISPLAY_NAMES.get(subject, subject)
        error_msg = (
            f"⚠️ <b>{subject_display} is currently on cooldown.</b>\n\n"
            f"⏳ <b>Available again in:</b> {formatted_time}.\n\n"
            f"<i>You can choose any other subject that is not on cooldown.</i>"
        )
        return False, error_msg

    return True, None

async def apply_subject_cooldown(group_id: int, subject: str):
    """
    Applies the mandatory 3-hour cooldown to this specific subject for this group.
    """
    await set_subject_cooldown(
        group_id=group_id,
        subject=subject,
        duration_seconds=settings.COOLDOWN_SECONDS,
    )
