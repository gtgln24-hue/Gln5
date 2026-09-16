import express from "express";
import path from "path";
import fs from "fs";
import { execSync, spawn } from "child_process";
import { fileURLToPath } from "url";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

dotenv.config({ override: true });

process.env.BOT_TOKEN = "8928910777:AAFN_BLIh_bIQPB2Pm6NBhcWgwlFYxSuEBg";
process.env.OWNER_ID = "8518332185";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.json());

// Load question bank from bot/data/questions.json
const questionsFilePath = path.join(__dirname, "bot", "data", "questions.json");
let questionBank: any[] = [];
try {
  if (fs.existsSync(questionsFilePath)) {
    questionBank = JSON.parse(fs.readFileSync(questionsFilePath, "utf-8"));
  }
} catch (e) {
  console.error("Error reading questions.json:", e);
}

// In-memory simulator state for cooldowns and approvals
const simulatedCooldowns: Record<string, number> = {}; // key: group_id:subject -> expiry timestamp
const approvedGroups = new Set<string>(["-1001928374650", "-1002030405060"]);

// Helper functions for python bot process management
let botStartedAt: number | null = null;
let botRestartCount = 0;
let lastBotError: string | null = null;
let respawnTimeout: NodeJS.Timeout | null = null;
let botAutoRunEnabled = true;
let activeBotChild: any = null;

function getBotProcessInfo(): { running: boolean; pid: number | null; autoRunEnabled: boolean } {
  // First check active child reference if still alive
  if (activeBotChild && !activeBotChild.killed && activeBotChild.exitCode === null && activeBotChild.pid) {
    try {
      // Check if process is genuinely responding to signal 0
      process.kill(activeBotChild.pid, 0);
      return { running: true, pid: activeBotChild.pid, autoRunEnabled: botAutoRunEnabled };
    } catch (e) {
      activeBotChild = null;
    }
  }

  // Fallback to system-level search with [p] bracket trick to avoid matching self
  try {
    const output = execSync("pgrep -f '[p]ython3 bot.py' || true").toString().trim();
    if (output) {
      const pids = output.split("\n").map((p) => parseInt(p.trim(), 10)).filter(Boolean);
      if (pids.length > 0) {
        return { running: true, pid: pids[0], autoRunEnabled: botAutoRunEnabled };
      }
    }
  } catch (e) {
    // ignore
  }
  return { running: false, pid: null, autoRunEnabled: botAutoRunEnabled };
}

function startBotProcess() {
  botAutoRunEnabled = true;
  const current = getBotProcessInfo();
  if (current.running) {
    if (!botStartedAt) botStartedAt = Date.now();
    return { ...current, autoRunEnabled: true };
  }

  try {
    const outLog = fs.openSync(path.join(process.cwd(), "bot.log"), "a");
    const pythonModulesPath = path.join(process.cwd(), "python_modules");
    const child = spawn("python3", ["bot.py"], {
      cwd: process.cwd(),
      detached: false,
      stdio: ["ignore", outLog, outLog],
      env: {
        ...process.env,
        PYTHONPATH: `${pythonModulesPath}:${process.env.PYTHONPATH || ""}`,
        BOT_TOKEN: "8928910777:AAFN_BLIh_bIQPB2Pm6NBhcWgwlFYxSuEBg",
        OWNER_ID: "8518332185",
      },
    });

    activeBotChild = child;
    botStartedAt = Date.now();
    lastBotError = null;

    child.on("error", (err) => {
      console.error("[Bot Supervisor] Child process error:", err);
      lastBotError = String(err);
      activeBotChild = null;
      if (botAutoRunEnabled) scheduleRespawn();
    });

    child.on("exit", (code, signal) => {
      console.warn(`[Bot Supervisor] python3 bot.py exited (code: ${code}, signal: ${signal}).`);
      activeBotChild = null;
      botRestartCount++;
      if (botAutoRunEnabled) scheduleRespawn();
    });

    return { running: true, pid: child.pid || null, autoRunEnabled: true };
  } catch (e) {
    console.error("Failed to spawn bot.py:", e);
    lastBotError = String(e);
    activeBotChild = null;
    if (botAutoRunEnabled) scheduleRespawn();
    return { running: false, pid: null, error: String(e), autoRunEnabled: true };
  }
}

function stopBotProcess() {
  botAutoRunEnabled = false;
  if (respawnTimeout) {
    clearTimeout(respawnTimeout);
    respawnTimeout = null;
  }
  if (activeBotChild) {
    try {
      activeBotChild.kill("SIGTERM");
    } catch (e) {}
    activeBotChild = null;
  }
  try {
    execSync("pkill -9 -f '[p]ython3 bot.py' || true");
  } catch (e) {}
  botStartedAt = null;
  return { running: false, pid: null, autoRunEnabled: false };
}

function toggleBotProcess() {
  const current = getBotProcessInfo();
  if (current.running) {
    return stopBotProcess();
  } else {
    return startBotProcess();
  }
}

function scheduleRespawn() {
  if (!botAutoRunEnabled) return;
  if (respawnTimeout) clearTimeout(respawnTimeout);
  respawnTimeout = setTimeout(() => {
    if (!botAutoRunEnabled) return;
    const current = getBotProcessInfo();
    if (!current.running) {
      console.log("[Bot Supervisor] Reviving bot process...");
      startBotProcess();
    }
  }, 2000);
}

function restartBotProcess() {
  botAutoRunEnabled = true;
  try {
    execSync("pkill -f 'python3 bot.py' || true");
  } catch (e) {}
  botRestartCount++;
  return startBotProcess();
}

// 24x7 Supervisor Watchdog: automatically starts on server boot and keeps alive continuously
startBotProcess();
setInterval(() => {
  if (!botAutoRunEnabled) return;
  const info = getBotProcessInfo();
  if (!info.running) {
    console.log("[24x7 Watchdog] Bot not running, auto-starting python3 bot.py now...");
    startBotProcess();
  }
}, 10000);

// API Routes
app.get("/api/health", (req, res) => {
  const botInfo = getBotProcessInfo();
  res.json({
    status: "ok",
    bot_name: "GLN Quiz Bot",
    version: "2.0.0",
    questions_count: questionBank.length,
    telegram_configured: Boolean(process.env.BOT_TOKEN),
    bot_username: "Glnquizbot",
    owner_id: process.env.OWNER_ID || "8518332185",
    bot_process: botInfo,
  });
});

app.get("/api/bot/status", (req, res) => {
  const botInfo = getBotProcessInfo();
  const uptimeSeconds = botInfo.running && botStartedAt ? Math.floor((Date.now() - botStartedAt) / 1000) : 0;
  res.json({
    configured: Boolean(process.env.BOT_TOKEN),
    bot_username: "Glnquizbot",
    owner_id: process.env.OWNER_ID || "8518332185",
    uptime_seconds: uptimeSeconds,
    restarts: botRestartCount,
    last_error: lastBotError,
    mode_24x7: true,
    ...botInfo,
  });
});

app.get("/api/bot/logs", (req, res) => {
  try {
    const logPath = path.join(process.cwd(), "bot.log");
    if (!fs.existsSync(logPath)) {
      return res.json({ logs: ["No logs generated yet. Bot starting up..."] });
    }
    const content = fs.readFileSync(logPath, "utf-8");
    const lines = content.split("\n").filter(Boolean);
    const recent = lines.slice(-80);
    res.json({ logs: recent });
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

app.post("/api/bot/start", (req, res) => {
  const result = startBotProcess();
  res.json(result);
});

app.post("/api/bot/stop", (req, res) => {
  const result = stopBotProcess();
  res.json(result);
});

app.post("/api/bot/toggle", (req, res) => {
  const result = toggleBotProcess();
  res.json(result);
});

app.post("/api/bot/restart", (req, res) => {
  const result = restartBotProcess();
  res.json(result);
});

app.get("/api/download/bot-zip", (req, res) => {
  try {
    const zipPath = path.join("/tmp", `gln-quiz-bot-${Date.now()}.zip`);
    execSync(`python3 scripts/export_zip.py bot "${zipPath}"`, { cwd: process.cwd() });
    res.download(zipPath, "gln-quiz-bot-source.zip", (err) => {
      try {
        if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);
      } catch (_) {}
    });
  } catch (err) {
    res.status(500).json({ error: "Failed to generate bot zip: " + String(err) });
  }
});

app.get("/api/download/full-zip", (req, res) => {
  try {
    const zipPath = path.join("/tmp", `gln-project-${Date.now()}.zip`);
    execSync(`python3 scripts/export_zip.py full "${zipPath}"`, { cwd: process.cwd() });
    res.download(zipPath, "gln-quiz-full-project.zip", (err) => {
      try {
        if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);
      } catch (_) {}
    });
  } catch (err) {
    res.status(500).json({ error: "Failed to generate project zip: " + String(err) });
  }
});

app.get("/api/questions", (req, res) => {
  const { subject } = req.query;
  if (subject && typeof subject === "string") {
    const filtered = questionBank.filter(
      (q) => q.subject.toLowerCase() === subject.toLowerCase()
    );
    return res.json(filtered);
  }
  res.json(questionBank);
});

app.get("/api/cooldowns", (req, res) => {
  const now = Date.now();
  const active: Record<string, { subject: string; remainingSeconds: number }> = {};
  for (const [key, expiry] of Object.entries(simulatedCooldowns)) {
    if (expiry > now) {
      const parts = key.split(":");
      active[key] = {
        subject: parts[1] || "Unknown",
        remainingSeconds: Math.ceil((expiry - now) / 1000),
      };
    }
  }
  res.json(active);
});

app.post("/api/cooldowns/apply", (req, res) => {
  const { groupId, subject } = req.body;
  if (!groupId || !subject) {
    return res.status(400).json({ error: "Missing groupId or subject" });
  }
  const key = `${groupId}:${subject}`;
  // 3 hours = 3 * 3600 * 1000 ms
  const expiry = Date.now() + 3 * 3600 * 1000;
  simulatedCooldowns[key] = expiry;
  res.json({ success: true, key, expiry, remainingHours: 3 });
});

app.post("/api/cooldowns/reset", (req, res) => {
  const { groupId, subject } = req.body;
  if (groupId && subject) {
    delete simulatedCooldowns[`${groupId}:${subject}`];
  } else {
    for (const key of Object.keys(simulatedCooldowns)) {
      delete simulatedCooldowns[key];
    }
  }
  res.json({ success: true });
});

app.post("/api/groups/approve", (req, res) => {
  const { groupId, ownerId } = req.body;
  if (!groupId) return res.status(400).json({ error: "Missing groupId" });
  approvedGroups.add(String(groupId));
  res.json({ success: true, groupId, approved: true });
});

app.get("/api/groups/status", (req, res) => {
  const { groupId } = req.query;
  const isApproved = approvedGroups.has(String(groupId));
  res.json({ groupId, isApproved });
});

function getBuiltinExplanation(question: string, correctAnswer: string, subject: string, topic?: string): string {
  const subj = (subject || "").toLowerCase();
  
  if (subj.includes("hindi")) {
    if (question.includes("संधि") || (topic && topic.includes("संधि"))) {
      return `संधि नियम: '${correctAnswer}' दो वर्णों के मेल से उत्पन्न होने वाला शुद्ध मानक संधि-रूप है।`;
    }
    if (question.includes("समास") || (topic && topic.includes("समास"))) {
      return `समास विश्लेषण: '${correctAnswer}' सामासिक पदों के विग्रह और अर्थ की प्रधानता के अनुसार व्याकरण सम्मत है।`;
    }
    if (question.includes("पर्यायवाची") || question.includes("समानार्थी")) {
      return `शब्दार्थ संदर्भ: '${correctAnswer}' दिए गए शब्द का सटीक एवं प्रामाणिक पर्यायवाची रूप है।`;
    }
    if (question.includes("उपन्यास") || question.includes("साहित्य") || question.includes("रचना")) {
      return `हिंदी साहित्य संदर्भ: '${correctAnswer}' हिंदी साहित्य इतिहास एवं प्रमुख कृतियों के अनुसार प्रमाणित तथ्य है।`;
    }
    return `व्याकरण स्पष्टीकरण: '${correctAnswer}' हिंदी मानक व्याकरण एवं वर्तनी नियमों के अनुसार प्रामाणिक उत्तर है।`;
  }

  if (subj.includes("science") || subj.includes("vigyan")) {
    if (question.includes("प्रकाश") || question.includes("ऊर्जा")) {
      return `भौतिकी सिद्धांत: NCERT भौतिकी के अनुसार '${correctAnswer}' ऊर्जा संरक्षण एवं प्रकाशिकी का स्थापित नियम है।`;
    }
    return `वैज्ञानिक तथ्य: NCERT एवं सामान्य विज्ञान सिद्धांतों के अनुसार '${correctAnswer}' पूर्णतः प्रमाणित वैज्ञानिक उत्तर है।`;
  }

  if (subj.includes("itihas") || subj.includes("history")) {
    return `ऐतिहासिक संदर्भ: '${correctAnswer}' प्राचीन, मध्यकालीन एवं आधुनिक भारतीय इतिहास के प्रामाणिक अभिलेखों से प्रमाणित है।`;
  }

  if (subj.includes("samajik") || subj.includes("social")) {
    if (question.includes("अनुच्छेद") || question.includes("संविधान")) {
      return `संवैधानिक प्रावधान: भारतीय संविधान के अधिकृत अनुच्छेदों एवं व्यवस्थाओं के अनुसार '${correctAnswer}' सही है।`;
    }
    return `सामाजिक अध्ययन: NCERT पाठ्यक्रम एवं सामाजिक विज्ञान के आधिकारिक मानकों के अनुसार '${correctAnswer}' सही विकल्प है।`;
  }

  if (subj.includes("botany")) {
    return `पादप शारीरिकी: वनस्पति विज्ञान और पादप ऊतक/कोशिका वर्गीकरण के अनुसार '${correctAnswer}' सही जैविक उत्तर है।`;
  }

  if (subj.includes("zoology")) {
    return `प्राणी विज्ञान: जंतु वर्गीकरण, अंग तंत्र एवं जैव विकास सिद्धांतों के अनुसार '${correctAnswer}' सटीक उत्तर है।`;
  }

  if (subj.includes("math") || subj.includes("ganit")) {
    return `गणितीय सिद्धांत: निर्धारित गणितीय सूत्र, बीजगणित/अंकगणित नियमों के अनुसार चरणबद्ध हल '${correctAnswer}' प्राप्त होता है।`;
  }

  if (subj.includes("chem") || subj.includes("rasayan")) {
    return `रासायनिक सिद्धांत: आवर्त सारणी, रासायनिक अभिक्रियाओं और परमाण्विक नियमों के अनुसार '${correctAnswer}' सही उत्तर है।`;
  }

  return `स्पष्टीकरण: '${correctAnswer}' इस प्रश्न का प्रामाणिक व सही उत्तर है।`;
}

// Gemini AI Explanation Endpoint (Server-Side to protect API key, with built-in zero-config offline fallback)
app.post("/api/ai/explain", async (req, res) => {
  const { question, correctAnswer, subject, topic } = req.body;
  const apiKey = process.env.GEMINI_API_KEY || process.env.AI_API_KEY;

  if (!apiKey) {
    const builtinExp = getBuiltinExplanation(question, correctAnswer, subject, topic);
    return res.json({
      explanation: builtinExp,
      engine: "builtin",
      apiKeyConfigured: false,
    });
  }

  try {
    const { GoogleGenAI } = await import("@google/genai");
    const ai = new GoogleGenAI({ apiKey });
    const prompt = `आप GLN Quiz Bot के हिंदी शिक्षक हैं। निम्नलिखित प्रश्न और सही उत्तर का एक संक्षिप्त (1-2 वाक्य) और सटीक स्पष्टीकरण हिंदी में दें। किसी भी परीक्षा के नाम या वर्ष का झूठा दावा न करें।\n\nविषय: ${subject}\nप्रश्न: ${question}\nसही उत्तर: ${correctAnswer}\nसंक्षिप्त स्पष्टीकरण:`;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: prompt,
    });

    res.json({
      explanation: response.text?.trim() || getBuiltinExplanation(question, correctAnswer, subject, topic),
      engine: "gemini",
      apiKeyConfigured: true,
    });
  } catch (error: any) {
    console.error("Gemini API Error, falling back to built-in explanation:", error);
    res.json({
      explanation: getBuiltinExplanation(question, correctAnswer, subject, topic),
      engine: "builtin_fallback",
      apiKeyConfigured: true,
    });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`GLN Quiz Bot Server & Simulator running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
