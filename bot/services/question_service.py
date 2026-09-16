"""
GLN Quiz Bot - Question Preparation & Queue Service
Manages unique question selection, non-repetition database checks, option count adaptation,
randomized correct answer positioning, and background question pre-fetching queue.
"""

import json
import random
import logging
from typing import List, Dict, Any, Optional, Set
from bot.database.db import AsyncSessionLocal
from bot.database.models import QuestionBank, UsedQuestion
from bot.database.queries import (
    get_used_question_hashes,
    get_used_question_texts,
    insert_used_question_if_unique,
    is_question_hash_used,
)
from bot.utils.question_hash import (
    normalize_question_text,
    generate_question_hash,
    is_semantically_similar,
)
from bot.services.question_generator import question_generator

logger = logging.getLogger(__name__)

class QuestionQueueManager:
    """
    Manages an in-memory queue of 100 verified strictly UNIQUE questions.
    Prepares exactly 100 unique questions before quiz start and verifies DB uniqueness.
    """
    def __init__(self, session_id: str, group_id: int, subject: str, options_count: int):
        self.session_id = session_id
        self.group_id = group_id
        self.subject = subject
        self.options_count = options_count
        self.queue: List[Dict[str, Any]] = []
        self.used_hashes: Set[str] = set()
        self.used_texts: List[str] = []
        self.prepared_hashes_in_queue: Set[str] = set()

    async def initialize(self):
        """
        Loads used question history from database for this group and subject,
        then prepares exactly 100 unique questions and persists the explicit order to DB.
        """
        db_hashes = await get_used_question_hashes(self.group_id, self.subject)
        self.used_hashes = set(db_hashes)
        self.used_texts = await get_used_question_texts(self.group_id, self.subject, limit=500)
        await self.prepare_100_unique_questions(target_count=100)

        # Persist full 100-question ordered queue to database
        try:
            from bot.database.queries import save_session_questions
            await save_session_questions(self.session_id, self.queue)
            logger.info(
                f"Session ID: {self.session_id} | Successfully persisted {len(self.queue)} ordered questions to database."
            )
        except Exception as e:
            logger.exception(f"Error persisting session questions to database: {e}")

    async def prepare_100_unique_questions(self, target_count: int = 100):
        """
        Strict 100 unique question requirement:
        Before starting the quiz, prepare exactly 100 UNIQUE questions.
        For every generated question:
        - Check duplicates inside question_queue.
        - Check duplicates in current quiz session.
        - Check duplicates in database.
        - Semantic similarity check.
        - Add only unique questions.
        """
        logger.info(
            f"Group ID: {self.group_id} | Session ID: {self.session_id} | "
            f"Subject: {self.subject} | Initializing queue of {target_count} unique questions..."
        )

        question_queue: List[Dict[str, Any]] = []
        self.prepared_hashes_in_queue.clear()
        attempts = 0
        max_attempts = 20

        while len(question_queue) < target_count and attempts < max_attempts:
            attempts += 1
            needed = target_count - len(question_queue)
            candidates = await question_generator.get_candidate_questions(
                subject=self.subject,
                needed_count=needed,
                used_texts=self.used_texts + [q["question"] for q in question_queue],
                used_hashes=self.used_hashes.union(self.prepared_hashes_in_queue),
            )

            if not candidates:
                logger.warning(f"No more candidates generated on attempt {attempts}")
                break

            for cand in candidates:
                if len(question_queue) >= target_count:
                    break

                q_text = cand.get("question", "").strip()
                if not q_text:
                    continue

                q_hash = generate_question_hash(q_text)
                index_num = len(question_queue)

                # 1. Check duplicates inside question_queue
                if q_hash in self.prepared_hashes_in_queue:
                    logger.debug(
                        f"Group ID: {self.group_id} | Session ID: {self.session_id} | "
                        f"Question Number: {index_num} | Question Text: {q_text[:40]} | "
                        f"Hash: {q_hash[:12]} | Status: REJECTED (Duplicate in Queue)"
                    )
                    continue

                # 2. Check duplicates in current quiz session & in-memory used hashes (pre-loaded from DB)
                if q_hash in self.used_hashes:
                    logger.debug(
                        f"Group ID: {self.group_id} | Session ID: {self.session_id} | "
                        f"Question Number: {index_num} | Question Text: {q_text[:40]} | "
                        f"Hash: {q_hash[:12]} | Status: REJECTED (Already in Used Hashes/DB)"
                    )
                    continue

                # 4. Semantic duplicate check
                existing_recent_texts = [q["question"] for q in question_queue[-30:]] + self.used_texts[-40:]
                is_semantic_dup = False
                for prev_text in existing_recent_texts:
                    if is_semantically_similar(q_text, prev_text):
                        is_semantic_dup = True
                        break

                if is_semantic_dup:
                    logger.debug(
                        f"Group ID: {self.group_id} | Session ID: {self.session_id} | "
                        f"Question Number: {index_num} | Question Text: {q_text[:40]} | "
                        f"Hash: {q_hash[:12]} | Status: REJECTED (Semantic Duplicate)"
                    )
                    continue

                # Accepted!
                prepared = self._prepare_single_question(cand, self.options_count, q_hash)
                question_queue.append(prepared)
                self.prepared_hashes_in_queue.add(q_hash)

                logger.info(
                    f"Group ID: {self.group_id} | Session ID: {self.session_id} | "
                    f"Question Number: {index_num} | Question Text: {q_text[:40]} | "
                    f"Hash: {q_hash[:12]} | Status: ACCEPTED"
                )

        self.queue = question_queue
        logger.info(
            f"Group ID: {self.group_id} | Session ID: {self.session_id} | "
            f"Subject: {self.subject} | Queue prepared with {len(self.queue)}/{target_count} unique questions."
        )

    def _prepare_single_question(self, raw_q: Dict[str, Any], options_count: int, q_hash: str) -> Dict[str, Any]:
        """
        Formats a question for presentation:
        - Guarantees correct answer is always included.
        - Randomly shuffles options.
        - Identifies correct letter (A, B, C, D).
        """
        options = raw_q.get("options", [])
        correct_answer = raw_q.get("correct_answer", "")

        distractors = [opt for opt in options if opt != correct_answer]
        random.shuffle(distractors)

        needed_distractors = max(1, options_count - 1)
        selected_distractors = distractors[:needed_distractors]

        final_options = [correct_answer] + selected_distractors
        random.shuffle(final_options)

        letters = ["A", "B", "C", "D"]
        correct_index = final_options.index(correct_answer)
        correct_letter = letters[correct_index] if correct_index < len(letters) else "A"

        return {
            "question_id": f"q_{q_hash[:16]}",
            "question_hash": q_hash,
            "subject": self.subject,
            "question": raw_q["question"],
            "correct_answer": correct_answer,
            "correct_letter": correct_letter,
            "options": final_options,
            "exam_name": raw_q.get("exam_name", "General Competition"),
            "exam_year": raw_q.get("exam_year", 2023),
            "topic": raw_q.get("topic", "सामान्य अध्ययन"),
            "source_reference": raw_q.get("source_reference", "NCERT / State Board"),
        }

    async def get_question_by_order(self, order_num: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves the question with explicit order_num (1 to 100).
        First checks in-memory queue at index (order_num - 1).
        If not in memory (e.g. after a restart), queries the database.
        Ensures the question hash is securely recorded in used_questions.
        """
        candidate = None
        idx = order_num - 1
        if 0 <= idx < len(self.queue):
            candidate = self.queue[idx]
        else:
            from bot.database.queries import get_session_question_by_index
            candidate = await get_session_question_by_index(self.session_id, order_num)

        if not candidate:
            return None

        q_hash = candidate.get("question_hash", "")
        q_text = candidate.get("question", "")

        if q_hash and q_text:
            await insert_used_question_if_unique(
                group_id=self.group_id,
                subject=self.subject,
                question_hash=q_hash,
                question_text=q_text,
                quiz_session_id=self.session_id,
            )

        candidate["question_index"] = order_num
        return candidate

    async def pop_next_question(self, question_index: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves the next strictly unique question using explicit order.
        """
        # Supports 1-based order index
        order = question_index if question_index >= 1 else 1
        return await self.get_question_by_order(order)
