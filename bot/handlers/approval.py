"""
GLN Quiz Bot - Approval & Group Registration Handler
Handles bot joining groups, admin checks, owner notifications, and /Approvegln commands.
"""

import logging
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, KICKED, LEFT, RESTRICTED, MEMBER, ADMINISTRATOR
from bot.config import settings
from bot.database.queries import (
    register_or_update_group,
    get_or_create_group,
    is_group_approved,
    approve_group,
    set_group_admin_status,
)
from bot.utils.permissions import is_bot_owner, is_bot_admin

logger = logging.getLogger(__name__)
approval_router = Router()

@approval_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def on_bot_promoted_admin(event: ChatMemberUpdated, bot: Bot):
    """Fired when the bot is promoted to administrator in a group."""
    chat = event.chat
    if chat.type not in ["group", "supergroup"]:
        return

    logger.info(f"Bot promoted to admin in group {chat.id} ({chat.title})")
    await register_or_update_group(
        group_id=chat.id,
        group_name=chat.title or "Unnamed Group",
        group_username=chat.username,
        is_admin=True,
    )

    # Check if approved
    approved = await is_group_approved(chat.id)
    if not approved:
        await bot.send_message(
            chat_id=chat.id,
            text=(
                "⚠️ <b>PLEASE CONTACT MY OWNER AND GET YOUR GROUP APPROVED.</b>\n\n"
                f"📋 <b>Group ID:</b> <code>{chat.id}</code>\n"
                "<i>Until the owner approves this group, quizzes cannot be started.</i>"
            ),
            parse_mode="HTML",
        )

@approval_router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def on_bot_added_as_member(event: ChatMemberUpdated, bot: Bot):
    """Fired when the bot is added as a regular member (not yet admin)."""
    chat = event.chat
    if chat.type not in ["group", "supergroup"]:
        return

    adder_username = event.from_user.username or event.from_user.first_name
    member_count = 0
    try:
        member_count = await bot.get_chat_member_count(chat.id)
    except Exception:
        pass

    # Record in database
    await get_or_create_group(
        group_id=chat.id,
        group_name=chat.title or "Unnamed Group",
        group_username=chat.username,
        member_count=member_count,
        added_by_user=adder_username,
        is_admin=False,
    )

    # Send request to group
    await bot.send_message(
        chat_id=chat.id,
        text=(
            "⚠️ <b>PLEASE MAKE ME ADMIN IN YOUR GROUP</b>\n\n"
            "I require administrator permissions to manage 15-second timers, inline quiz options, "
            "and scoring properly."
        ),
        parse_mode="HTML",
    )

    # Notify Bot Owner privately
    if settings.OWNER_ID:
        owner_notification = (
            "🚨 <b>NEW GROUP DETECTED</b>\n\n"
            f"<b>Group Name:</b> {chat.title}\n"
            f"<b>Group ID:</b> <code>{chat.id}</code>\n"
            f"<b>Username:</b> @{chat.username or 'None'}\n"
            f"<b>Members:</b> {member_count}\n"
            f"<b>Added By:</b> @{adder_username}\n"
            f"<b>Date:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"<i>To approve this group, send:</i>\n"
            f"<code>/Approvegln {chat.id}</code>"
        )
        try:
            await bot.send_message(
                chat_id=settings.OWNER_ID,
                text=owner_notification,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not notify bot owner {settings.OWNER_ID}: {e}")
