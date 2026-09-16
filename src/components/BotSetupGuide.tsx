import React, { useState } from "react";
import {
  Terminal,
  Copy,
  Check,
  ShieldCheck,
  Key,
  Settings,
  Server,
  ExternalLink,
  Download,
  Github,
  FolderArchive,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export const BotSetupGuide: React.FC = () => {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [envMode, setEnvMode] = useState<"minimal" | "full">("minimal");

  const handleCopy = (text: string, sectionId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(sectionId);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const minimalEnv = `# .env for GLN Quiz Bot (Configured for @Glnquizbot)
BOT_TOKEN="8928910777:AAFN_BLIh_bIQPB2Pm6NBhcWgwlFYxSuEBg"
OWNER_ID="8518332185"

# Database automatically uses built-in SQLite (gln_quiz.db)
# Explanations automatically use built-in NCERT Hindi engine!
`;

  const fullEnv = `# .env Configuration for GLN Quiz Bot (@Glnquizbot)
BOT_TOKEN="8928910777:AAFN_BLIh_bIQPB2Pm6NBhcWgwlFYxSuEBg"
OWNER_ID="8518332185"

# Database: Defaults to built-in SQLite (no database URL required!)
DATABASE_URL="sqlite+aiosqlite:///gln_quiz.db"
# Or external PostgreSQL if you ever want:
# DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/glnquiz"

# AI Key: Completely optional! Defaults to built-in NCERT Hindi engine
AI_API_KEY=""
`;

  const envTemplate = envMode === "minimal" ? minimalEnv : fullEnv;

  const runCommands = `# 1. Clone repository and setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 2. Install async dependencies
pip install -r requirements.txt

# 3. Configure environment variables (Only BOT_TOKEN and OWNER_ID needed!)
cp .env.example .env
nano .env

# 4. Start GLN Quiz Bot
python bot.py
`;

  const gitCommands = `# If you want to push directly to your own GitHub repository:
# 1. Create an empty repository on https://github.com/new (e.g., named "gln-quiz-bot")
# 2. Run these commands:
git remote add origin https://github.com/YOUR_USERNAME/gln-quiz-bot.git
git push -u origin main
`;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* 1-Click Direct ZIP Download & GitHub Resolution Card */}
      <div className="bg-gradient-to-br from-indigo-900/90 via-indigo-950/95 to-slate-950 rounded-3xl p-6 border-2 border-amber-400/60 shadow-2xl space-y-5 text-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-indigo-700/60">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-amber-400 text-indigo-950 flex items-center justify-center shadow-lg font-black shrink-0">
              <FolderArchive className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-black text-white flex items-center gap-2">
                <span>Download Complete Bot Source Code</span>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  Fixed & Ready
                </span>
              </h2>
              <p className="text-xs text-indigo-200 mt-0.5">
                पूरी फाइल्स के साथ 1-क्लिक में डाउनलोड करें (सभी 8 विषय, टाइमर इंजन, NCERT प्रश्न बैंक और हैंडलर्स शामिल हैं)
              </p>
            </div>
          </div>

          {/* Quick Action Download Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            <a
              id="btn-download-bot-zip"
              href="/api/download/bot-zip"
              download="gln-quiz-bot-source.zip"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-amber-400 hover:bg-amber-300 text-indigo-950 font-black text-xs sm:text-sm shadow-lg shadow-amber-400/20 transition-all hover:scale-102 active:scale-98 cursor-pointer"
            >
              <Download className="w-4 h-4 text-indigo-950" />
              <span>Download Bot ZIP (~250 KB)</span>
            </a>

            <a
              id="btn-download-full-zip"
              href="/api/download/full-zip"
              download="gln-quiz-full-project.zip"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-indigo-800 hover:bg-indigo-700 text-white font-bold text-xs sm:text-sm border border-indigo-600 shadow-md transition-all hover:scale-102 active:scale-98 cursor-pointer"
            >
              <Download className="w-4 h-4 text-indigo-300" />
              <span>Full Project ZIP (Bot + Web UI)</span>
            </a>
          </div>
        </div>

        {/* Why was download failing & what was fixed */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
          <div className="p-4 bg-indigo-950/70 rounded-2xl border border-indigo-700/60 space-y-2">
            <div className="flex items-center gap-2 text-amber-300 font-bold">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>डाउनलोड में पहले क्या समस्या थी?</span>
            </div>
            <p className="text-indigo-200 text-[11px] leading-relaxed">
              प्रोजेक्ट में बैकएंड पैकेज डायरेक्टरी (<code className="text-white bg-indigo-900 px-1 py-0.5 rounded font-mono">python_modules</code>) 250MB+ की हो गई थी। इसलिए AI Studio या ब्राउज़र से डाउनलोड करते समय फाइल बीच में ही रुक जाती थी और पूरी फाइल नहीं आ रही थी।
            </p>
            <p className="text-emerald-300 text-[11px] font-semibold">
              ✔ अब हमने अतिरिक्त बाइनरी फाइल्स को हटाकर और <code className="text-white font-mono">.gitignore</code> को ठीक करके बिल्कुल शुद्ध और पूरा कोडबंडल तैयार कर दिया है (सिर्फ ~250 KB)।
            </p>
          </div>

          <div className="p-4 bg-indigo-950/70 rounded-2xl border border-indigo-700/60 space-y-2">
            <div className="flex items-center gap-2 text-amber-300 font-bold">
              <Github className="w-4 h-4 text-indigo-300 shrink-0" />
              <span>GitHub रिपॉजिटरी में पुश करने का तरीका</span>
            </div>
            <p className="text-indigo-200 text-[11px] leading-relaxed">
              हमने गिट रिपॉजिटरी (<code className="text-white font-mono">main</code> branch) पहले ही इनिशियलाइज़ करके कमिट कर दी है। आप इस कोड को किसी भी नए GitHub रेपो में 1 कमांड से भेज सकते हैं:
            </p>
            <div className="relative mt-1 bg-slate-950 p-2 rounded-xl font-mono text-[10px] text-amber-200 border border-indigo-800">
              <pre className="overflow-x-auto whitespace-pre-wrap">{`git remote add origin https://github.com/USER/REPO.git\ngit push -u origin main`}</pre>
              <button
                onClick={() => handleCopy(gitCommands, "git-cmd")}
                className="absolute top-1.5 right-1.5 p-1 rounded bg-indigo-800 hover:bg-indigo-700 text-indigo-200"
                title="Copy Git Commands"
              >
                {copiedSection === "git-cmd" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Introduction Card */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-3xl p-6 border border-indigo-700/80 shadow-xl space-y-4 text-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-amber-400 text-indigo-950 flex items-center justify-center shadow-md font-black">
            <Terminal className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-black text-white">
              GLN Quiz Bot Production Deployment Guide
            </h2>
            <p className="text-xs text-indigo-300">
              Complete setup guide for hosting GLN Quiz Bot on any Linux VPS, Docker container, or cloud server.
            </p>
          </div>
        </div>

        {/* Zero-Config Assurance Box */}
        <div className="p-4 bg-gradient-to-r from-amber-500/20 via-indigo-950 to-indigo-950 rounded-2xl border border-amber-400/40 space-y-2.5 text-xs">
          <div className="flex items-center gap-2 text-amber-300 font-bold uppercase tracking-wider text-xs">
            <ShieldCheck className="w-4 h-4 text-amber-400" />
            <span>डेटाबेस URL और AI API Key की आवश्यकता नहीं है (100% Zero-Setup Ready)</span>
          </div>
          <p className="text-indigo-200 leading-relaxed">
            अगर आपके पास <b className="text-white">Database URL</b> और <b className="text-white">AI API Key</b> नहीं है, तो बिल्कुल चिंता न करें! GLN Quiz Bot में ये दोनों चीज़ें पहले से इन-बिल्ट हैं:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
            <div className="p-2.5 bg-indigo-900/80 rounded-xl border border-indigo-700/60">
              <div className="font-bold text-amber-300 flex items-center gap-1.5">
                📁 1. Built-in Local SQLite Database
              </div>
              <p className="text-indigo-300 text-[11px] mt-1">
                बॉट अपने फोल्डर में स्वतः <code className="text-white font-mono">gln_quiz.db</code> बनाता है। किसी भी PostgreSQL या क्लाउड सर्वर की जरूरत नहीं है।
              </p>
            </div>
            <div className="p-2.5 bg-indigo-900/80 rounded-xl border border-indigo-700/60">
              <div className="font-bold text-amber-300 flex items-center gap-1.5">
                🧠 2. Built-in NCERT Hindi Explanations
              </div>
              <p className="text-indigo-300 text-[11px] mt-1">
                सभी 8 विषयों के लिए मानक हिंदी व्याख्या इंजन इन-बिल्ट है। किसी भी Gemini या AI API Key की जरूरत नहीं है।
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-xs">
          <div className="p-3.5 bg-indigo-950/80 rounded-2xl border border-indigo-800">
            <div className="font-bold text-amber-300">Framework</div>
            <div className="text-indigo-300 mt-1">Python 3.10+ & aiogram v3</div>
          </div>
          <div className="p-3.5 bg-indigo-950/80 rounded-2xl border border-indigo-800">
            <div className="font-bold text-amber-300">Database Layer</div>
            <div className="text-indigo-300 mt-1">Built-in SQLite (Zero-Config) or PostgreSQL</div>
          </div>
          <div className="p-3.5 bg-indigo-950/80 rounded-2xl border border-indigo-800">
            <div className="font-bold text-amber-300">Explanation Engine</div>
            <div className="text-indigo-300 mt-1">Built-in NCERT Engine (AI Key Optional)</div>
          </div>
        </div>
      </div>

      {/* Step 1: Telegram BotFather Setup */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-3xl p-6 border border-indigo-700/80 shadow-xl space-y-4 text-slate-100">
        <div className="flex items-center gap-2.5">
          <span className="w-7 h-7 rounded-xl bg-amber-400 text-indigo-950 flex items-center justify-center text-xs font-black shadow-sm">
            1
          </span>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Create Bot with Telegram @BotFather
          </h3>
        </div>

        <div className="text-xs text-indigo-200 space-y-3 leading-relaxed">
          <p>
            Follow these steps inside the official Telegram app to create the bot:
          </p>
          <ol className="list-decimal list-inside space-y-2 pl-2">
            <li>
              Open Telegram and search for{" "}
              <a
                href="https://t.me/BotFather"
                target="_blank"
                rel="noreferrer"
                className="text-amber-400 font-bold underline inline-flex items-center gap-0.5"
              >
                @BotFather <ExternalLink className="w-3 h-3" />
              </a>
              .
            </li>
            <li>
              Send command: <code className="text-amber-300 bg-indigo-950 px-1.5 py-0.5 rounded font-mono">/newbot</code>
            </li>
            <li>
              Enter Bot Name: <b className="text-white">GLN Quiz Bot</b>
            </li>
            <li>
              Enter Username (must end in <code className="text-amber-300 font-mono">bot</code>), e.g.: <code className="text-amber-300 bg-indigo-950 px-1.5 py-0.5 rounded font-mono">gln_quiz_bot</code>
            </li>
            <li>Copy the generated HTTP API Bot Token.</li>
            <li>
              <b className="text-amber-300">Crucial Step:</b> Disable Group Privacy so the bot can see commands in groups:
              <ul className="list-disc list-inside pl-4 mt-1 space-y-1 text-indigo-300">
                <li>Send <code className="text-amber-300 bg-indigo-950 px-1 py-0.5 rounded font-mono">/setprivacy</code> to @BotFather</li>
                <li>Select <code className="text-amber-300 bg-indigo-950 px-1 py-0.5 rounded font-mono">@gln_quiz_bot</code></li>
                <li>Choose <b className="text-white">Disable</b></li>
              </ul>
            </li>
          </ol>
        </div>
      </div>

      {/* Step 2: Environment Configuration */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-3xl p-6 border border-indigo-700/80 shadow-xl space-y-4 text-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded-xl bg-amber-400 text-indigo-950 flex items-center justify-center text-xs font-black shadow-sm">
              2
            </span>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Configure .env File
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <div className="inline-flex bg-indigo-950 p-1 rounded-xl border border-indigo-800 text-xs">
              <button
                onClick={() => setEnvMode("minimal")}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  envMode === "minimal"
                    ? "bg-amber-400 text-indigo-950 shadow-xs"
                    : "text-indigo-300 hover:text-white"
                }`}
              >
                ⚡ Minimal (No DB / No AI Key)
              </button>
              <button
                onClick={() => setEnvMode("full")}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                  envMode === "full"
                    ? "bg-amber-400 text-indigo-950 shadow-xs"
                    : "text-indigo-300 hover:text-white"
                }`}
              >
                ⚙️ Full (.env)
              </button>
            </div>

            <button
              onClick={() => handleCopy(envTemplate, "env")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-400 hover:bg-amber-300 text-indigo-950 transition-colors cursor-pointer"
            >
              {copiedSection === "env" ? (
                <>
                  <Check className="w-3.5 h-3.5 text-indigo-950" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-indigo-950" />
                  <span>Copy .env</span>
                </>
              )}
            </button>
          </div>
        </div>

        <pre className="bg-indigo-950 text-indigo-200 p-4 rounded-2xl text-xs font-mono overflow-x-auto border border-indigo-800/80 leading-relaxed">
          {envTemplate}
        </pre>

        <p className="text-xs text-indigo-300">
          Tip: You can retrieve your numerical Telegram User ID by sending any message to <code className="text-amber-300 font-mono">@userinfobot</code> in Telegram. Set this as <code className="text-amber-300 font-mono">OWNER_ID</code>.
        </p>
      </div>

      {/* Step 3: Run the Bot */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-3xl p-6 border border-indigo-700/80 shadow-xl space-y-4 text-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded-xl bg-amber-400 text-indigo-950 flex items-center justify-center text-xs font-black shadow-sm">
              3
            </span>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Install Dependencies & Launch
            </h3>
          </div>

          <button
            onClick={() => handleCopy(runCommands, "run")}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-950 hover:bg-indigo-800 text-amber-300 border border-indigo-800 transition-colors cursor-pointer"
          >
            {copiedSection === "run" ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-amber-400" />
                <span>Copy Commands</span>
              </>
            )}
          </button>
        </div>

        <pre className="bg-indigo-950 text-indigo-200 p-4 rounded-2xl text-xs font-mono overflow-x-auto border border-indigo-800/80 leading-relaxed">
          {runCommands}
        </pre>
      </div>

      {/* Commands Summary Table */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-3xl p-6 border border-indigo-700/80 shadow-xl space-y-3 text-slate-100">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          Bot Commands Reference
        </h3>

        <div className="overflow-x-auto rounded-2xl border border-indigo-800">
          <table className="w-full text-xs text-left text-indigo-200 border-collapse">
            <thead>
              <tr className="border-b border-indigo-800 text-amber-400 font-bold uppercase tracking-wider text-[11px] bg-indigo-950">
                <th className="py-3 px-4">Command</th>
                <th className="py-3 px-4">Access Level</th>
                <th className="py-3 px-4">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-indigo-800/60 bg-indigo-900/40">
              <tr>
                <td className="py-3 px-4 font-mono font-black text-amber-400">/Choose</td>
                <td className="py-3 px-4 font-bold text-indigo-200">Group Admin / Owner</td>
                <td className="py-3 px-4">
                  Shows inline keyboard with all 8 subjects and prompts for options count.
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-mono font-black text-rose-400">/Stopgln</td>
                <td className="py-3 px-4 font-bold text-indigo-200">Group Admin / Owner</td>
                <td className="py-3 px-4">
                  Stops active quiz immediately, shows final rankings, and triggers 3h subject cooldown.
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-mono font-black text-purple-400">/Approvegln &lt;id&gt;</td>
                <td className="py-3 px-4 font-bold text-amber-300">Bot Owner Only</td>
                <td className="py-3 px-4">
                  Approves a new Telegram group to host quizzes after bot is added.
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-mono font-black text-emerald-400">/leaderboard</td>
                <td className="py-3 px-4 font-bold text-indigo-200">All Group Members</td>
                <td className="py-3 px-4">
                  Displays all-time top group performers with points, accuracy, and medals.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
