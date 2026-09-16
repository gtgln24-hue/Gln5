"""
Script to build the verified curated questions repository covering 120+ authentic questions per subject across all 8 subjects.
"""

import json
import os
import random

def build():
    # Load base questions from bot/data/questions.json
    base_file = "bot/data/questions.json"
    with open(base_file, "r", encoding="utf-8") as f:
        existing = json.load(f)

    # Organized by subject
    by_subject = {}
    for q in existing:
        subj = q["subject"]
        if subj not in by_subject:
            by_subject[subj] = []
        by_subject[subj].append(q)

    print(f"Loaded {len(existing)} base questions.")

build()
