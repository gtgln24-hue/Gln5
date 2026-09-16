"""
GLN Quiz Bot - Configuration module
Validates environment variables, sets constants, and defines subject mappings.
"""

import os
from typing import Dict, List, Optional

# Load .env file with override=True to prioritize configured credentials
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if not os.path.exists(env_path):
    env_path = ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                os.environ[k.strip()] = v

try:
    from pydantic_settings import BaseSettings
except ImportError:
    class BaseSettings:
        pass

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8928910777:AAFN_BLIh_bIQPB2Pm6NBhcWgwlFYxSuEBg")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "8518332185")) if os.getenv("OWNER_ID", "8518332185").lstrip("-").isdigit() else 8518332185
    DATABASE_URL: str = (os.getenv("DATABASE_URL") or "").strip() or "sqlite+aiosqlite:///gln_quiz.db"

    @property
    def AI_API_KEY(self) -> str:
        gemini = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini:
            return gemini
        ai = os.getenv("AI_API_KEY", "").strip()
        if ai and not ai.startswith("sk-"):
            return ai
        return ""

    @property
    def GEMINI_API_KEY(self) -> str:
        return self.AI_API_KEY

    # Quiz Rules
    COOLDOWN_HOURS: int = 3
    COOLDOWN_SECONDS: int = 3 * 3600  # 10,800 seconds (3 hours)
    QUESTION_TIMER_SECONDS: int = 15
    TEST_TIMER_SECONDS: Optional[int] = None
    TOTAL_QUESTIONS: int = 100
    MAX_UNANSWERED_QUESTIONS_FOR_PAUSE: int = 2

    # Subject definitions
    SUBJECTS: List[str] = [
        "Hindi",
        "Samajik Vigyan",
        "Itihas",
        "Science",
        "Botany",
        "Zoology",
        "Mathematics",
        "Chemistry"
    ]

    SUBJECT_DISPLAY_NAMES: Dict[str, str] = {
        "Hindi": "हिंदी (Hindi)",
        "Samajik Vigyan": "सामाजिक विज्ञान (Social Science)",
        "Itihas": "इतिहास (History)",
        "Science": "विज्ञान (Science)",
        "Botany": "वनस्पति विज्ञान (Botany)",
        "Zoology": "जंतु विज्ञान (Zoology)",
        "Mathematics": "गणित (Maths)",
        "Chemistry": "रसायन विज्ञान (Chemistry)"
    }

    SUBJECT_ICONS: Dict[str, str] = {
        "Hindi": "📖",
        "Samajik Vigyan": "🌍",
        "Itihas": "🏛️",
        "Science": "🔬",
        "Botany": "🌿",
        "Zoology": "🦁",
        "Mathematics": "📐",
        "Chemistry": "🧪"
    }

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
