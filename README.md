# GLN Quiz Bot 🎓

> **Production-ready Telegram Group Quiz Bot for Hindi Language Questions across 8 Competitive Exam Subjects.**

GLN Quiz Bot is an asynchronous, high-concurrency Telegram Bot specifically engineered for large Telegram study groups, competitive exam coaching communities, and state/national level aspirants (UPSC, UPPSC, SSC, NEET, JEE, Railway, and State PCS).

---

## 📑 Table of Contents
1. [Project Overview & Key Highlights](#project-overview--key-highlights)
2. [Supported Subjects](#supported-subjects)
3. [Bot Architecture & Folder Structure](#bot-architecture--folder-structure)
4. [Database Schema](#database-schema)
5. [Complete Bot Flow](#complete-bot-flow)
6. [Commands Reference](#commands-reference)
7. [Installation & Setup](#installation--setup)
8. [Configuration (.env)](#configuration-env)
9. [Running in Production](#running-in-production)
10. [Troubleshooting & Security](#troubleshooting--security)

---

## 🌟 Project Overview & Key Highlights

- **100 Unique Questions Per Session**: Automatically schedules 100 questions per quiz without repeating questions already served to that group.
- **Strict 15-Second Timer**: Real-time asynchronous timer per question. Automatically locks questions, calculates votes, reveals the correct option, and triggers the next question.
- **Private User Answer Feedback**: Group members receive instant private callback alerts (`🟢 Correct Answer ✅` or `🔴 Wrong Answer ❌`) without exposing answers publicly before the 15-second timer concludes.
- **Flexible Answer Options**: Group Admins choose between **2 Options, 3 Options, or 4 Options** per question. Correct answer positions are randomly shuffled on every question.
- **Subject Cooldown System**: Once a quiz finishes or is stopped with `/Stopgln`, that specific subject enters a **3-Hour Cooldown** in that group. Other 7 subjects remain immediately accessible.
- **Bot Owner Approval Gate**: Strict access control via `/Approvegln`. The bot alerts the owner whenever it is added to a new group. Quizzes remain locked until explicitly approved by the Bot Owner.
- **Inactivity Auto-Pause & Resume**: If group members stop responding, the quiz auto-pauses and provides a `▶️ Resume Quiz` button for admins to continue from the exact question.
- **Verified Exam Metadata**: Displays authentic competitive exam origins (UPSC, UPPSC, SSC CGL/CHSL, NEET, JEE, BPSC) without hallucinated claims.

---

## 📚 Supported Subjects

1. **Hindi (हिंदी)**: व्याकरण, संधि, समास, मुहावरे, वर्तनी शुद्धि, साहित्य
2. **Samajik Vigyan (सामाजिक विज्ञान)**: संविधान, राजव्यवस्था, भूगोल, अर्थव्यवस्था, नागरिक शास्त्र
3. **Itihas (इतिहास)**: प्राचीन भारत, सिंधु सभ्यता, मध्यकालीन भारत, आधुनिक स्वतंत्रता संग्राम
4. **Science (सामान्य विज्ञान)**: भौतिकी, रसायन, ऊर्जा, तरंग, पर्यावरण, मापन
5. **Botany (वनस्पति विज्ञान)**: पादप शारीरिकी, प्रकाश संश्लेषण, कोशिका संरचना, आनुवंशिकी, पादप हॉर्मोन
6. **Zoology (जंतु विज्ञान)**: मानव शरीर क्रिया विज्ञान, परिसंचरण तंत्र, अंतःस्रावी ग्रंथियाँ, पाचन, उत्सर्जन
7. **Mathematics (गणित)**: लाभ-हानि, प्रतिशत, त्रिकोणमिति, औसत, बीजगणित, क्षेत्रमिति
8. **Chemistry (रसायन विज्ञान)**: आवर्त सारणी, परमाणु संरचना, अम्ल-क्षार-लवण, कार्बनिक रसायन, रासायनिक संयोग

---

## 📁 Bot Architecture & Folder Structure

```
gln-quiz-bot/
├── bot.py                     # Main application entry point & dispatcher
├── requirements.txt           # Python dependencies (aiogram, SQLAlchemy, aiosqlite, asyncpg)
├── .env.example               # Template for environment variables
├── README.md                  # Complete documentation and setup guide
├── bot/
│   ├── __init__.py
│   ├── config.py              # Environment configuration, subject constants, limits
│   ├── data/
│   │   └── questions.json     # Curated Hindi question bank with verified exam metadata
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy async ORM models
│   │   ├── db.py              # Engine creation, connection pooling, seed initializer
│   │   └── queries.py         # Asynchronous CRUD queries (sessions, answers, cooldowns)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── approval.py        # Bot addition detection, admin verification, /Approvegln
│   │   ├── commands.py        # /Choose, /Stopgln, /leaderboard, /start, permission checks
│   │   └── quiz.py            # Inline callbacks: subject selection, options count, answer clicks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── quiz_service.py    # State machine, question dispatcher, 15s timer transitions
│   │   ├── question_service.py# Pre-fetch queue manager, option adapter, non-repetition
│   │   ├── cooldown_service.py# 3-hour per-group per-subject cooldown manager
│   │   ├── timer_service.py   # Asyncio non-blocking 15-second timer manager
│   │   └── ai_service.py      # Optional Gemini AI assistance for Hindi explanations
│   └── utils/
│       ├── __init__.py
│       ├── permissions.py     # Admin, group owner, and bot owner checks
│       └── formatters.py      # Telegram HTML message & leaderboard formatters
```

---

## 🗄️ Database Schema

The database supports both **PostgreSQL (production)** and **SQLite (development)** via SQLAlchemy async ORM:

### 1. `groups`
- `group_id` (BigInteger, PK): Telegram group ID (e.g. `-100xxxxxxxxxx`)
- `group_name` (String): Group title
- `group_username` (String): Public handle if available
- `member_count` (Integer): Total group members
- `is_admin` (Boolean): Whether bot has administrator rights
- `is_approved` (Boolean): Whether approved by Bot Owner
- `added_at` (DateTime): Timestamp when bot joined

### 2. `approved_groups`
- `group_id` (BigInteger, PK): Whitelisted Telegram group ID
- `approved_at` (DateTime): Timestamp of approval
- `approved_by_owner` (BigInteger): Bot Owner's Telegram ID

### 3. `quiz_sessions`
- `session_id` (String, PK): Unique session ID
- `group_id` (BigInteger, FK): Target Telegram group
- `subject` (String): Selected subject
- `status` (String): `WAITING` | `PREPARING` | `RUNNING` | `PAUSED` | `STOPPED` | `COMPLETED`
- `current_question` (Integer): Active question index (1-100)
- `options_count` (Integer): 2, 3, or 4 options
- `started_at` (DateTime), `finished_at` (DateTime)

### 4. `user_answers`
- `id` (Integer, PK): Auto-increment
- `session_id` (String), `question_id` (String)
- `user_id` (BigInteger), `username` (String)
- `selected_option` (Text): The chosen answer
- `is_correct` (Boolean): True if correct, False otherwise
- `answered_at` (DateTime)
- *Constraint: Unique(`session_id`, `question_id`, `user_id`)*

### 5. `subject_cooldowns`
- `id` (Integer, PK)
- `group_id` (BigInteger), `subject` (String)
- `cooldown_until` (DateTime): Expiry time (Current time + 3 hours)
- *Constraint: Unique(`group_id`, `subject`)*

### 6. `question_bank`
- `question_id` (String, PK)
- `subject` (String): One of the 8 supported subjects
- `question` (Text): Question in Hindi
- `correct_answer` (Text): Verified correct answer
- `options_json` (Text): JSON list of all distractors
- `exam_name` (String): e.g., "UPSC CSE", "SSC CGL", "NEET UG"
- `exam_year` (Integer): e.g., 2022
- `topic` (String): Syllabus topic

### 7. `used_questions`
- `group_id` (BigInteger), `question_id` (String), `used_at` (DateTime)
- *Guarantees questions do not repeat in the same group.*

### 8. `leaderboard`
- `group_id` (BigInteger), `user_id` (BigInteger), `username` (String)
- `points` (Integer), `correct_count` (Integer), `wrong_count` (Integer), `quizzes_played` (Integer)

---

## 🔄 Complete Bot Flow

1. **Bot added to group**:
   - The bot detects addition and checks if it was granted Admin status.
   - If NOT admin: sends `⚠️ PLEASE MAKE ME ADMIN IN YOUR GROUP`.
   - Sends private notification to Bot Owner:
     ```
     🚨 NEW GROUP DETECTED
     Group Name: Aspirants Study Club
     Group ID: -1001982736451
     Added By: @moderator_user
     ```
2. **Owner Approval**:
   - Bot Owner sends `/Approvegln -1001982736451` in private chat.
   - The bot records the approval and sends confirmation to the group.
3. **Starting Quiz (`/Choose`)**:
   - Only Group Admins / Owners can run `/Choose`.
   - If a normal member attempts: `❌ Only Group Admins or Owners can start a quiz.`
   - Bot displays inline keyboard with the 8 subjects.
4. **Subject Cooldown Verification**:
   - When an admin taps a subject, the bot checks if it is on a 3-hour cooldown in this group.
   - If on cooldown: `⚠️ Science is currently on cooldown. Available again in: 2 hours 15 minutes.` Other subjects remain ready.
5. **Option Count Selection**:
   - Admin picks `[ 2 Options ]`, `[ 3 Options ]`, or `[ 4 Options ]`.
   - Bot pre-fetches 100 unique questions, filters out already used IDs, randomizes the correct answer position, and begins Question 1.
6. **Active 15-Second Question Loop**:
   - Bot sends question text, exam metadata, options, and countdown timer.
   - Any group member can tap an option.
   - User receives immediate private Telegram popup: `🟢 Correct Answer ✅` or `🔴 Wrong Answer ❌`.
   - If user attempts to answer again: `⚠️ You have already answered this question.`
7. **Timeout Result & Next Question**:
   - At 15 seconds, buttons are locked.
   - Bot broadcasts correct option and vote breakdown:
     ```
     Question 1/100 completed.
     ✅ Correct Answer: B. New Delhi
     A — 4 users | B — 18 users | C — 2 users
     Next question starting...
     ```
8. **Inactivity Pause**:
   - If 2 consecutive questions receive zero answers, bot auto-pauses: `⏸️ Quiz Paused`.
   - Any admin can tap `▶️ Resume Quiz` to resume from the exact question.
9. **Quiz Finish or `/Stopgln`**:
   - Automatically finishes after Question 100/100, or when an admin sends `/Stopgln`.
   - Bot posts final leaderboard with medals 🥇🥈🥉, total correct/wrong stats, and participant accuracy %.
   - Applies the 3-hour cooldown to that subject in this group.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Your Telegram User ID from [@userinfobot](https://t.me/userinfobot)

### 1. Clone & Install Dependencies
```bash
git clone <repo-url>
cd gln-quiz-bot

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
OWNER_ID="987654321"
DATABASE_URL="sqlite+aiosqlite:///gln_quiz.db"
# Or for production PostgreSQL:
# DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/glnquiz"
AI_API_KEY=""  # Optional: Gemini API key for Hindi explanations
```

### 3. Run the Bot
```bash
python bot.py
```

---

## 🤖 Telegram BotFather Setup Instructions

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and name it: `GLN Quiz Bot`.
3. Choose a username ending in `bot`, e.g. `gln_quiz_bot`.
4. Copy the HTTP API token into `BOT_TOKEN` in `.env`.
5. Disable Group Privacy Mode so the bot can process group commands:
   - Send `/setprivacy` to @BotFather
   - Select your bot
   - Choose **Disable**
6. Enable Group Admin rights:
   - Send `/setjoingroups` -> **Enable**

---

## 📜 License
Apache-2.0 License. Designed and maintained for competitive examination preparation communities.
