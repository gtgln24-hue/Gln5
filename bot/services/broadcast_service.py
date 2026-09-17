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
from bot.database.queries import get_all_broadcast_destinations, register_or_update_group

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
        1. Collects unique group (approved & unapproved) and user destinations from database.
        2. Applies rate-limiting (0.05s delay between messages).
        3. Catches flood-wait (TelegramRetryAfter), respects wait time, and resumes.
        4. Handles group migration to supergroups automatically.
        5. Falls back to plain text if HTML entities are malformed.
        6. Logs audit details strictly without exposing secrets.
        """
        async with self._broadcast_lock:
            self.is_broadcasting = True
            try:
                destinations = await get_all_broadcast_destinations()
                group_ids = destinations.get("groups", [])
                user_ids = destinations.get("users", [])

                # Merge and deduplicate all destinations (groups first, then users)
                all_targets = list(dict.fromkeys(group_ids + user_ids))
                total = len(all_targets)

                logger.info(
                    f"\n[BROADCAST AUDIT]\n"
                    f"event: broadcast started\n"
                    f"owner ID: {owner_id}\n"
                    f"total destinations: {total} (groups: {len(group_ids)}, users: {len(user_ids)})\n"
                )

                sent = 0
                failed = 0
                groups_sent = 0
                groups_failed = 0
                users_sent = 0
                users_failed = 0

                for target_id in all_targets:
                    is_group = (target_id < 0)
                    # Controlled rate limiting to stay well within Telegram limits (max ~20-30 msg/sec)
                    await asyncio.sleep(0.05)

                    success = False
                    for attempt in range(3):
                        try:
                            # 1. Attempt sending with HTML formatting first
                            try:
                                await bot.send_message(
                                    chat_id=target_id,
                                    text=message_text,
                                    parse_mode="HTML",
                                    disable_web_page_preview=True,
                                )
                            except TelegramBadRequest as b_err:
                                err_str = str(b_err).lower()
                                # Handle group upgraded to supergroup
                                if hasattr(b_err, "parameters") and b_err.parameters and b_err.parameters.migrate_to_chat_id:
                                    migrated_id = b_err.parameters.migrate_to_chat_id
                                    logger.info(f"[BROADCAST MIGRATE] Group {target_id} upgraded to supergroup {migrated_id}")
                                    try:
                                        await register_or_update_group(
                                            group_id=migrated_id,
                                            group_name=f"Migrated Supergroup {migrated_id}",
                                        )
                                    except Exception:
                                        pass
                                    # Send to new supergroup ID
                                    await bot.send_message(
                                        chat_id=migrated_id,
                                        text=message_text,
                                        parse_mode="HTML",
                                        disable_web_page_preview=True,
                                    )
                                # Fallback to plain text on ANY entity or markup error
                                else:
                                    await bot.send_message(
                                        chat_id=target_id,
                                        text=message_text,
                                        parse_mode=None,
                                        disable_web_page_preview=True,
                                    )

                            success = True
                            sent += 1
                            if is_group:
                                groups_sent += 1
                            else:
                                users_sent += 1
                            break

                        except TelegramRetryAfter as e:
                            wait_time = getattr(e, "retry_after", 5)
                            logger.warning(
                                f"[BROADCAST RATE LIMIT] Telegram flood wait. Sleeping {wait_time}s before resuming..."
                            )
                            await asyncio.sleep(wait_time + 1)
                            continue

                        except TelegramForbiddenError as f_err:
                            logger.warning(
                                f"[BROADCAST FORBIDDEN] target_id={target_id} (is_group={is_group}): {f_err}"
                            )
                            break

                        except (TelegramNotFound, TelegramBadRequest) as chat_err:
                            logger.warning(
                                f"[BROADCAST CHAT ERROR] target_id={target_id} (is_group={is_group}): {chat_err}"
                            )
                            break

                        except TelegramAPIError as api_err:
                            logger.warning(
                                f"[BROADCAST API ERROR] target_id={target_id}: {api_err}"
                            )
                            break

                        except Exception as unexpected:
                            logger.error(
                                f"[BROADCAST UNEXPECTED ERROR] target_id={target_id}: {unexpected}"
                            )
                            break

                    if not success:
                        failed += 1
                        if is_group:
                            groups_failed += 1
                        else:
                            users_failed += 1

                logger.info(
                    f"\n[BROADCAST COMPLETED AUDIT]\n"
                    f"event: broadcast completed\n"
                    f"owner ID: {owner_id}\n"
                    f"total destinations: {total}\n"
                    f"groups sent: {groups_sent}/{len(group_ids)}\n"
                    f"users sent: {users_sent}/{len(user_ids)}\n"
                    f"successful sends: {sent}\n"
                    f"failed sends: {failed}\n"
                )

                return {
                    "total": total,
                    "sent": sent,
                    "failed": failed,
                    "groups_count": len(group_ids),
                    "groups_sent": groups_sent,
                    "groups_failed": groups_failed,
                    "users_count": len(user_ids),
                    "users_sent": users_sent,
                    "users_failed": users_failed,
                    "approved_groups_count": destinations.get("approved_count", 0),
                    "unapproved_groups_count": destinations.get("unapproved_count", 0),
                }

            finally:
                self.is_broadcasting = False

broadcast_service = BroadcastService()
