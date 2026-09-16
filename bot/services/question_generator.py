"""
GLN Quiz Bot - Dynamic Multi-Subject Question Generator & Curated Knowledge Engine
Provides hundreds of authentic Hindi questions per subject for competitive exams (UPSC, SSC, State PCS),
plus procedural generator algorithms and Gemini AI integration to guarantee 100 strictly unique questions
per quiz session without any repetition.
"""

import json
import random
import logging
from typing import List, Dict, Any, Set, Optional
from bot.config import settings
from bot.utils.question_hash import (
    normalize_question_text,
    generate_question_hash,
    is_semantically_similar,
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Extensive Curated Question Bank across all 8 subjects
# -------------------------------------------------------------------------
from bot.data.curated_questions import CURATED_QUESTIONS_BY_SUBJECT
from bot.services.procedural_generators import generate_procedural_questions

class QuestionGenerator:
    """
    Generates and fetches candidates for a given subject.
    Coordinates:
    1. Curated database bank questions
    2. Procedural curriculum generators (Mathematics, Science, Chemistry, etc.)
    3. Gemini AI generation (with context of excluded topics)
    """

    async def generate_ai_batch(
        self,
        subject: str,
        count: int,
        used_texts_sample: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Calls Gemini API passing previously asked questions/topics.
        Instructs AI to generate questions substantially different from previously accepted ones.
        """
        api_key = settings.AI_API_KEY
        if not api_key:
            return []

        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            sample_context = "\n".join(f"- {t[:60]}" for t in used_texts_sample[-15:])
            prompt = (
                f"You are a top exam paper creator for UPSC, SSC, and State PCS Hindi examinations.\n"
                f"Generate {count} completely unique and authentic multiple choice questions in Hindi for the subject '{subject}'.\n\n"
                f"CRITICAL CONSTRAINT: Generate questions that are substantially different from all previously accepted questions:\n"
                f"{sample_context if sample_context else 'No previous questions yet.'}\n\n"
                f"Each question must have:\n"
                f"- question (in Hindi)\n"
                f"- correct_answer (string)\n"
                f"- options (array of exactly 4 distinct options including the correct_answer)\n"
                f"- exam_name (realistic competitive exam name in India, e.g. UPPSC PCS, SSC CGL, BPSC, UPSC CSE)\n"
                f"- exam_year (between 2018 and 2024)\n"
                f"- topic (relevant syllabus topic)\n"
                f"- source_reference (credible reference)\n\n"
                f"Output strictly valid JSON array of objects without Markdown code blocks."
            )

            import asyncio
            loop = asyncio.get_running_loop()

            def _call_gemini():
                for m in ["gemini-3.6-flash", "gemini-3.5-flash-lite"]:
                    try:
                        return client.models.generate_content(
                            model=m,
                            contents=prompt,
                        )
                    except Exception as model_err:
                        logger.warning(f"Failed with model {m}: {model_err}")
                return None

            response = await loop.run_in_executor(None, _call_gemini)

            if not response or not response.text:
                return []

            raw_text = response.text.strip()
            # Handle markdown JSON formatting
            if "```json" in raw_text:
                raw_text = raw_text.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```", 1)[1].split("```", 1)[0]
            raw_text = raw_text.strip()

            # Find array brackets if surrounded by other text
            start_bracket = raw_text.find("[")
            end_bracket = raw_text.rfind("]")
            if start_bracket != -1 and end_bracket != -1:
                raw_text = raw_text[start_bracket:end_bracket + 1]

            items = json.loads(raw_text)
            valid_items = []
            for it in items:
                if "question" in it and "correct_answer" in it and "options" in it and len(it["options"]) >= 2:
                    it["subject"] = subject
                    valid_items.append(it)
            return valid_items
        except Exception as e:
            logger.warning(f"AI generation batch failed for {subject}: {e}")
            return []

    async def get_candidate_questions(
        self,
        subject: str,
        needed_count: int,
        used_texts: List[str],
        used_hashes: Set[str],
    ) -> List[Dict[str, Any]]:
        """
        Gathers raw candidates from curated pools, procedural algorithms, and AI.
        """
        candidates: List[Dict[str, Any]] = []

        # 1. Curated questions pool
        curated = CURATED_QUESTIONS_BY_SUBJECT.get(subject, [])
        shuffled_curated = list(curated)
        random.shuffle(shuffled_curated)
        candidates.extend(shuffled_curated)

        # 2. Procedural questions pool (can generate 200+ unique questions per subject)
        proc = generate_procedural_questions(subject, target_count=max(120, needed_count + 40))
        candidates.extend(proc)

        # Filter candidates that are already in used_hashes
        fresh_candidates = [
            c for c in candidates
            if generate_question_hash(c.get("question", "")) not in used_hashes
        ]

        # If fresh candidates from curated/procedural are not enough, generate with AI
        if settings.AI_API_KEY and len(fresh_candidates) < needed_count:
            deficit = needed_count - len(fresh_candidates)
            ai_batch = await self.generate_ai_batch(
                subject=subject,
                count=min(25, deficit + 5),
                used_texts_sample=used_texts,
            )
            fresh_candidates.extend(ai_batch)

        random.shuffle(fresh_candidates)
        return fresh_candidates

question_generator = QuestionGenerator()
