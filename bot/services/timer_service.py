"""
GLN Quiz Bot - Async Timer Service
Handles exact 15-second question countdown timers, auto-lock, and safe cancellation.
Guarantees timers never self-cancel during callback execution, prevents duplicate timers,
and maintains robust session-level locking.
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Coroutine, Any

logger = logging.getLogger(__name__)

class AsyncTimerManager:
    """
    Manages active countdown asyncio timers per quiz session.
    Provides session-level locking and guarantees that:
    1. Only ONE timer runs per session at any time.
    2. An expired timer never cancels itself during callback execution.
    3. Old timers are cleanly cancelled when advancing to a new question.
    """
    def __init__(self):
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}

    def get_session_lock(self, session_id: str) -> asyncio.Lock:
        """Returns the dedicated asyncio.Lock for a quiz session."""
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    def start_question_timer(
        self,
        session_id: str,
        question_index: int,
        duration_seconds: int,
        timeout_coro_fn: Callable[[], Coroutine[Any, Any, None]],
    ) -> asyncio.Task:
        """
        Starts an exact countdown timer for a question.
        Safely cancels any prior timer for this session.
        """
        # Cancel any previous timer
        self.cancel_timer(session_id)

        async def _timer_worker():
            current_task = asyncio.current_task()
            try:
                logger.info(
                    f"[TIMER START] session={session_id} question={question_index} duration={duration_seconds}"
                )
                await asyncio.sleep(duration_seconds)
                logger.info(
                    f"[TIMER EXPIRED] session={session_id} question={question_index}"
                )
                await timeout_coro_fn()
            except asyncio.CancelledError:
                logger.info(
                    f"[TIMER CANCELLED] session={session_id} question={question_index}"
                )
                raise
            except Exception as e:
                logger.exception(
                    f"[QUIZ ERROR] session={session_id} question={question_index} error={e}"
                )
            finally:
                if self._active_tasks.get(session_id) is current_task:
                    self._active_tasks.pop(session_id, None)

        task = asyncio.create_task(_timer_worker())
        self._active_tasks[session_id] = task
        return task

    def cancel_timer(self, session_id: str):
        """
        Cancels any running timer for this session.
        CRITICAL: Never cancels the calling task if invoked from within the timer worker itself.
        """
        task = self._active_tasks.get(session_id)
        current = asyncio.current_task()
        if task and task is not current and not task.done():
            task.cancel()
        if task is not current:
            self._active_tasks.pop(session_id, None)

    def has_active_timer(self, session_id: str) -> bool:
        """Checks if a timer is currently active and running for a session."""
        task = self._active_tasks.get(session_id)
        return task is not None and not task.done()

timer_manager = AsyncTimerManager()

