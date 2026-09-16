"""
GLN Quiz Bot - Owner Broadcast Service
Provides safe, rate-limited, asynchronous message broadcasting to database destinations
with Telegram flood-wait handling, error resilience, and structured owner auditing.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import (
    TelegramRetryAfter,
    TelegramForbiddenError,
    TelegramBadRequest,
    TelegramNotFound,
    TelegramAPIError,
)
from bot.database.queries import get_all_broadcast_destinations

logger = logging.getLogger("GLNBroadcastSystem")

class BroadcastService:
    """
    Manages pending broadcast confirmations and asynchronous delivery.
    Enforces rate limits, retry-after backoff, and destination error handling.
    """
    def __init__(self):
        # In-memory storage for pending previews: preview_id -> {owner_id, message_text, created_at}
        self.pending_previews: Dict[str, Dict[str, Any]] = {}
        # Concurrency lock so multiple broadcasts don't run at once
        self._broadcast_lock = asyncio.Lock()
        self.is_broadcasting = False

    def create_preview(self, owner_id: int, message_text: str) -> str:
        """Stores a pending broadcast message and returns a unique preview ID."""
        preview_id = uuid.uuid4().hex[:12]
        self.pending_previews[preview_id] = {
            "owner_id": owner_id,
            "message_text": message_text,
            "created_at": datetime.utcnow(),
        }
        return preview_id

    def get_preview(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves pending preview data."""
        return self.pending_previews.get(preview_id)

    def cancel_preview(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """Removes a pending preview on cancellation."""
        return self.pending_previews.pop(preview_id, None)

    async def execute_broadcast(self, bot: Bot, owner_id: int, message_text: str) -> Dict[str, Any]:
        """
        Executes asynchronous broadcasting to all valid database destinations:
        1. Collects unique group and user destinations from existing database.
        2. Applies rate-limiting (0.05s delay between messages).
        3. Catches flood-wait (TelegramRetryAfter), respects wait time, and resumes.
        4. Catches individual chat errors (blocked, kicked, deleted) without stopping.
        5. Logs audit details strictly without exposing secrets.
        """
        async with self._broadcast_lock:
            self.is_broadcasting = True
            try:
                destinations = await get_all_broadcast_destinations()
                group_ids = destinations.get("groups", [])
                user_ids = destinations.get("users", [])

                # Merge and deduplicate all valid destinations
                all_targets = list(dict.fromkeys(group_ids + user_ids))
                total = len(all_targets)

                # Required Audit Logging
                logger.info(
                    f"\n[BROADCAST AUDIT]\n"
                    f"event: broadcast started\n"
                    f"owner ID: {owner_id}\n"
                    f"total destinations: {total} (groups: {len(group_ids)}, users: {len(user_ids)})\n"
                )

                sent = 0
                failed = 0

                for target_id in all_targets:
                    # Controlled rate limiting to stay well within Telegram limits (max ~20-30 msg/sec)
                    await asyncio.sleep(0.05)

                    success = False
                    for attempt in range(2):
                        try:
                            # Try HTML formatting first
                            try:
                                await bot.send_message(
                                    chat_id=target_id,
                                    text=message_text,
                                    parse_mode="HTML",
                                    disable_web_page_preview=True,
                                )
                            except TelegramBadRequest as b_err:
                                # If HTML tags were malformed in owner's raw text, fallback to plain text
                                if "can't parse entities" in str(b_err).lower() or "unsupported start tag" in str(b_err).lower():
                                    await bot.send_message(
                                        chat_id=target_id,
                                        text=message_text,
                                        parse_mode=None,
                                        disable_web_page_preview=True,
                                    )
                                else:
                                    raise b_err

                            success = True
                            sent += 1
                            break

                        except TelegramRetryAfter as e:
                            # Telegram flood wait - respect requested sleep time and continue
                            wait_time = getattr(e, "retry_after", 5)
                            logger.warning(
                                f"[BROADCAST RATE LIMIT] Telegram flood wait received. Sleeping for {wait_time}s before resuming..."
                            )
                            await asyncio.sleep(wait_time + 1)
                            # Retry after waiting
                            continue

                        except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest) as chat_err:
                            # Chat blocked, deleted, or bot kicked out. Log and continue with next destination.
                            logger.warning(
                                f"[BROADCAST FAILED DESTINATION] chat_id={target_id} reason={chat_err}"
                            )
                            break

                        except TelegramAPIError as api_err:
                            logger.warning(
                                f"[BROADCAST API ERROR] chat_id={target_id} reason={api_err}"
                            )
                            break

                        except Exception as unexpected:
                            logger.error(
                                f"[BROADCAST UNEXPECTED ERROR] chat_id={target_id} reason={unexpected}"
                            )
                            break

                    if not success:
                        failed += 1

                # Required Audit Logging at completion
                logger.info(
                    f"\n[BROADCAST COMPLETED AUDIT]\n"
                    f"event: broadcast completed\n"
                    f"owner ID: {owner_id}\n"
                    f"total destinations: {total}\n"
                    f"successful sends: {sent}\n"
                    f"failed sends: {failed}\n"
                )

                return {
                    "total": total,
                    "sent": sent,
                    "failed": failed,
                    "groups_count": len(group_ids),
                    "users_count": len(user_ids),
                }

            finally:
                self.is_broadcasting = False

broadcast_service = BroadcastService()
