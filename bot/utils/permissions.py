"""
GLN Quiz Bot - Permissions & Security Utility
Verifies admin, owner, and bot privileges in Telegram groups.
"""

import logging
from aiogram import Bot
from aiogram.types import ChatMemberOwner, ChatMemberAdministrator
from bot.config import settings

logger = logging.getLogger(__name__)

def is_bot_owner(user_id: int) -> bool:
    """Verifies whether the given user is the designated Bot Owner."""
    return settings.OWNER_ID > 0 and user_id == settings.OWNER_ID

async def is_group_admin_or_owner(bot: Bot, chat_id: int, user_id: int) -> bool:
    """
    Checks if a user is an Administrator or Owner in the specified group chat.
    Also returns True if the user is the Bot Owner.
    """
    if is_bot_owner(user_id):
        return True

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return isinstance(member, (ChatMemberOwner, ChatMemberAdministrator))
    except Exception as e:
        logger.warning(f"Could not verify chat member permissions for user {user_id} in {chat_id}: {e}")
        return False

async def is_bot_admin(bot: Bot, chat_id: int) -> bool:
    """
    Verifies if GLN Quiz Bot itself is an Administrator in the chat.
    """
    try:
        bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
        return isinstance(bot_member, (ChatMemberOwner, ChatMemberAdministrator))
    except Exception as e:
        logger.warning(f"Could not check bot admin status in {chat_id}: {e}")
        return False

async def check_bot_can_send(bot: Bot, chat_id: int) -> bool:
    """Checks if the bot has permission to post and edit messages."""
    try:
        bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
        if isinstance(bot_member, ChatMemberAdministrator):
            return True
        return False
    except Exception:
        return False
