"""
Generates the comprehensive curated question bank file for GLN Quiz Bot.
Builds at least 120 authentic competitive exam questions per subject for all 8 subjects.
"""

import json
from pathlib import Path

def generate_curated_database():
    output_file = Path("bot/data/curated_questions.py")

    # Import base json
    with open("bot/data/questions.json", "r", encoding="utf-8") as f:
        base_questions = json.load(f)

    # Let's inspect base questions
    subjects = [
        "Hindi",
        "Samajik Vigyan",
        "Itihas",
        "Science",
        "Botany",
        "Zoology",
        "Mathematics",
        "Chemistry"
    ]
    print(f"Base questions loaded: {len(base_questions)}")

if __name__ == "__main__":
    generate_curated_database()
