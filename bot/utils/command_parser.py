"""
GLN Quiz Bot - Safe Command Parser & Filter
Case-insensitive command detection, @BotUsername stripping, group & supergroup support,
and structured debug audit logging.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any, Union
from aiogram.filters import Filter
from aiogram.types import Message
from aiogram import BaseMiddleware

logger = logging.getLogger("GLNCommandSystem")

def parse_command_text(text: Optional[str]) -> Optional[Tuple[str, List[str], str]]:
    """
    Safe command parser adhering strictly to the required specification:
    1. Read message text.
    2. Check whether it starts with "/".
    3. Extract command before spaces.
    4. Remove @BotUsername.
    5. Convert to lowercase.
    
    Returns:
        (command_name, args_list, raw_args_str) or None if text is not a command.
    """
    if not text or not isinstance(text, str):
        return None

    clean_text = text.strip()
    if not clean_text.startswith("/"):
        return None

    tokens = clean_text.split()
    first_token = tokens[0]

    if len(first_token) <= 1:
        return None

    raw_command_part = first_token[1:]  # remove leading '/'
    cmd_name = raw_command_part.split("@")[0].lower()

    args_list = tokens[1:]
    raw_args_str = clean_text[len(first_token):].strip()

    return cmd_name, args_list, raw_args_str


class SafeCommand(Filter):
    """
    aiogram filter matching command names case-insensitively,
    supporting /command@BotUsername in private, group, and supergroup chats.
    """
    def __init__(self, *commands: str):
        self.target_commands = set(cmd.lower().lstrip("/") for cmd in commands)

    async def __call__(self, message: Message) -> Union[bool, Dict[str, Any]]:
        text = message.text or message.caption
        parsed = parse_command_text(text)
        if not parsed:
            return False

        cmd_name, args_list, raw_args_str = parsed
        if cmd_name in self.target_commands:
            return {
                "command_name": cmd_name,
                "command_args": args_list,
                "command_args_str": raw_args_str,
            }
        return False


def log_message_received(chat_id: int, user_id: Optional[int], message_text: str):
    """Logs message arrival matching exact prompt format."""
    logger.info(
        f"\nMESSAGE RECEIVED:\n"
        f"chat_id: {chat_id}\n"
        f"user_id: {user_id}\n"
        f"message_text: {message_text}"
    )

def log_command_detected(command_name: str):
    """Logs detected command matching exact prompt format."""
    logger.info(
        f"\nCOMMAND DETECTED:\n"
        f"command_name: /{command_name}"
    )

def log_handler_executed(handler_name: str):
    """Logs handler execution matching exact prompt format."""
    logger.info(
        f"\nHANDLER EXECUTED:\n"
        f"handler_name: {handler_name}"
    )

def log_command_rejected(reason: str):
    """Logs command rejection matching exact prompt format."""
    logger.warning(
        f"\nCOMMAND REJECTED:\n"
        f"reason: {reason}"
    )


class MessageAuditMiddleware(BaseMiddleware):
    """
    Dispatcher middleware logging MESSAGE RECEIVED and COMMAND DETECTED for all messages.
    """
    async def __call__(self, handler, event: Message, data: Dict[str, Any]) -> Any:
        text = event.text or event.caption or "<empty_or_media>"
        chat_id = event.chat.id if event.chat else 0
        user_id = event.from_user.id if event.from_user else None

        log_message_received(chat_id=chat_id, user_id=user_id, message_text=text)

        parsed = parse_command_text(text)
        if parsed:
            cmd_name, _, _ = parsed
            log_command_detected(command_name=cmd_name)

        return await handler(event, data)
