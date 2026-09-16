/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import { Bot, RefreshCw, CheckCircle2, AlertTriangle, ExternalLink, Terminal, ShieldCheck, Clock, Power } from "lucide-react";
import { Subject } from "./types";
import { Header } from "./components/Header";
import { TelegramSimulator } from "./components/TelegramSimulator";
import { QuestionBankExplorer } from "./components/QuestionBankExplorer";
import { CooldownManager } from "./components/CooldownManager";
import { BotSetupGuide } from "./components/BotSetupGuide";

export default function App() {
  const [activeTab, setActiveTab] = useState<"simulator" | "questions" | "cooldowns" | "setup">("simulator");

  const groupId = "-1001928374650";

  // Shared cooldowns state (key: `${groupId}:${subject}` => timestamp)
  const [cooldowns, setCooldowns] = useState<Record<string, number>>(() => {
    return {
      [`${groupId}:Science`]: Date.now() + 2.5 * 3600 * 1000,
    };
  });

  // Live Python Bot Process State
  const [botStatus, setBotStatus] = useState<{
    running: boolean;
    pid: number | null;
    bot_username?: string;
    owner_id?: string;
    uptime_seconds?: number;
    restarts?: number;
    mode_24x7?: boolean;
    autoRunEnabled?: boolean;
  }>({ running: true, pid: null, bot_username: "Glnquizbot", owner_id: "8518332185", mode_24x7: true, autoRunEnabled: true });
  const [isRestarting, setIsRestarting] = useState(false);
  const [isTogglingBot, setIsTogglingBot] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const fetchBotStatus = () => {
    fetch("/api/bot/status")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setBotStatus({
            running: Boolean(data.running),
            pid: data.pid || null,
            bot_username: data.bot_username || "Glnquizbot",
            owner_id: data.owner_id || "8518332185",
            uptime_seconds: data.uptime_seconds,
            restarts: data.restarts,
            mode_24x7: data.autoRunEnabled !== false,
            autoRunEnabled: data.autoRunEnabled !== false,
          });
        }
      })
      .catch(() => {});
  };

  const fetchLogs = () => {
    setLoadingLogs(true);
    fetch("/api/bot/logs")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.logs) setLogs(data.logs);
      })
      .finally(() => setLoadingLogs(false));
  };

  useEffect(() => {
    fetchBotStatus();
    const timer = setInterval(fetchBotStatus, 4000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (showLogs) {
      fetchLogs();
      const logTimer = setInterval(fetchLogs, 4000);
      return () => clearInterval(logTimer);
    }
  }, [showLogs]);

  const handleToggleBot = async () => {
    setIsTogglingBot(true);
    try {
      const endpoint = botStatus.running ? "/api/bot/stop" : "/api/bot/start";
      const res = await fetch(endpoint, { method: "POST" });
      const data = await res.json();
      setBotStatus((prev) => ({
        ...prev,
        running: Boolean(data.running),
        pid: data.pid || null,
        mode_24x7: data.autoRunEnabled !== false,
        autoRunEnabled: data.autoRunEnabled !== false,
      }));
      setTimeout(() => {
        fetchBotStatus();
        fetchLogs();
        setIsTogglingBot(false);
      }, 700);
    } catch (e) {
      setIsTogglingBot(false);
    }
  };

  const handleRestartBot = async () => {
    setIsRestarting(true);
    try {
      await fetch("/api/bot/restart", { method: "POST" });
      setTimeout(() => {
        fetchBotStatus();
        fetchLogs();
        setIsRestarting(false);
      }, 1500);
    } catch (e) {
      setIsRestarting(false);
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds || seconds <= 0) return "Starting...";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  // Fetch live cooldowns from API
  useEffect(() => {
    fetch("/api/cooldowns")
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error("API not ready");
      })
      .then((data) => {
        const mapped: Record<string, number> = {};
        const now = Date.now();
        for (const [key, val] of Object.entries(data as Record<string, { remainingSeconds: number }>)) {
          mapped[key] = now + val.remainingSeconds * 1000;
        }
        if (Object.keys(mapped).length > 0) {
          setCooldowns(mapped);
        }
      })
      .catch(() => {});
  }, []);

  const handleApplyCooldown = (subject: Subject) => {
    const expiry = Date.now() + 3 * 3600 * 1000;
    const key = `${groupId}:${subject}`;
    setCooldowns((prev) => ({
      ...prev,
      [key]: expiry,
    }));

    fetch("/api/cooldowns/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ groupId, subject }),
    }).catch(() => {});
  };

  const handleRemoveSingleCooldown = (subject: Subject) => {
    const key = `${groupId}:${subject}`;
    setCooldowns((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });

    fetch("/api/cooldowns/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ groupId, subject }),
    }).catch(() => {});
  };

  const handleResetCooldowns = () => {
    setCooldowns({});
    fetch("/api/cooldowns/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }).catch(() => {});
  };

  const activeCooldownCount = Object.values(cooldowns).filter((exp: number) => exp > Date.now()).length;

  return (
    <div className="min-h-screen bg-indigo-950 text-slate-100 flex flex-col font-sans selection:bg-amber-400 selection:text-indigo-950">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeCooldownCount={activeCooldownCount}
        botRunning={botStatus.running}
        onToggleBot={handleToggleBot}
        isTogglingBot={isTogglingBot}
      />

      {/* Live Telegram Bot Process Banner with Run Switch */}
      <div className="bg-indigo-900/90 border-b border-indigo-800/80 px-4 sm:px-6 lg:px-8 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs">
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Direct Bot Power Switch (User Toggle) */}
            <div
              id="bot-run-switch-pill"
              className="flex items-center gap-2 px-2.5 py-1 rounded-xl bg-indigo-950/90 border border-indigo-700/80 shadow-inner"
            >
              <span className="text-[11px] font-mono font-bold text-amber-300 flex items-center gap-1">
                <Power className="w-3.5 h-3.5 text-amber-400" />
                <span>BOT SWITCH:</span>
              </span>

              <button
                id="bot-run-toggle-button"
                type="button"
                role="switch"
                aria-checked={botStatus.running}
                disabled={isTogglingBot}
                onClick={handleToggleBot}
                className={`relative inline-flex h-6 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-indigo-950 ${
                  botStatus.running ? "bg-emerald-500 hover:bg-emerald-400" : "bg-slate-700 hover:bg-slate-600"
                } ${isTogglingBot ? "opacity-50 cursor-not-allowed" : ""}`}
                title={botStatus.running ? "Bot chalu hai - Click karke band karein" : "Bot band hai - Click karke chalu karein"}
              >
                <span
                  aria-hidden="true"
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out flex items-center justify-center ${
                    botStatus.running ? "translate-x-6" : "translate-x-0"
                  }`}
                >
                  <Power
                    className={`w-3 h-3 ${
                      botStatus.running ? "text-emerald-600" : "text-slate-500"
                    }`}
                  />
                </span>
              </button>

              <span
                className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  botStatus.running
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-rose-500/20 text-rose-300"
                }`}
              >
                {isTogglingBot ? "CHANGING..." : botStatus.running ? "ON (RUNNING)" : "OFF (STOPPED)"}
              </span>
            </div>

            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full font-bold font-mono border ${
                botStatus.running
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                  : "bg-rose-500/20 text-rose-300 border-rose-500/40"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  botStatus.running ? "bg-emerald-400 animate-ping" : "bg-rose-400"
                }`}
              ></span>
              <span>
                {botStatus.running ? "BOT RUNNING (24×7 LIVE)" : "BOT STOPPED"}
              </span>
            </div>

            <div className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-700/60 text-amber-300 font-mono text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>24×7 Auto-Supervisor</span>
            </div>

            <div className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-950/80 border border-indigo-700/60 text-slate-300 font-mono text-[11px]">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>Uptime: {formatUptime(botStatus.uptime_seconds)}</span>
            </div>

            <div className="flex items-center gap-1 text-slate-200 font-mono">
              <Bot className="w-3.5 h-3.5 text-amber-400" />
              <span className="font-bold text-amber-300">@{botStatus.bot_username || "Glnquizbot"}</span>
              {botStatus.pid && (
                <span className="text-indigo-400 text-[11px]">(PID: {botStatus.pid})</span>
              )}
            </div>

            <span className="text-indigo-400 hidden sm:inline">•</span>
            <div className="text-indigo-200">
              Owner: <span className="font-mono text-white font-bold">{botStatus.owner_id || "8518332185"}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl border font-bold text-xs transition-colors cursor-pointer ${
                showLogs
                  ? "bg-amber-400 text-indigo-950 border-amber-400"
                  : "bg-indigo-950 hover:bg-indigo-800 text-indigo-200 border-indigo-700"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>{showLogs ? "Hide Logs" : "Live Logs"}</span>
            </button>

            <button
              onClick={handleRestartBot}
              disabled={isRestarting || !botStatus.running}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-indigo-950 hover:bg-indigo-800 text-amber-300 border border-indigo-700 font-bold text-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isRestarting ? "animate-spin text-amber-400" : ""}`} />
              <span>{isRestarting ? "Restarting..." : "Restart"}</span>
            </button>
            <a
              href={`https://t.me/${botStatus.bot_username || "Glnquizbot"}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-amber-400 hover:bg-amber-300 text-indigo-950 font-bold text-xs transition-colors"
            >
              <span>Open Bot</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Real-time 24x7 Terminal Logs Drawer */}
        {showLogs && (
          <div className="max-w-7xl mx-auto mt-2.5 p-3 rounded-xl bg-black/80 border border-indigo-700/80 font-mono text-[11px] text-emerald-400 shadow-inner">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-indigo-900/80 text-xs text-slate-300">
              <span className="flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-amber-400" />
                <span className="font-bold text-white">Live 24×7 Telegram Polling Stream</span>
                {loadingLogs && <span className="text-[10px] text-indigo-400">(refreshing...)</span>}
              </span>
              <button
                onClick={fetchLogs}
                className="text-amber-400 hover:text-amber-300 cursor-pointer flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Refresh
              </button>
            </div>
            <div className="max-h-52 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-indigo-800">
              {logs.length === 0 ? (
                <div className="text-slate-400">Loading Telegram polling logs...</div>
              ) : (
                logs.map((line, idx) => (
                  <div key={idx} className="leading-relaxed whitespace-pre-wrap break-all">
                    {line.includes("[ERROR]") ? (
                      <span className="text-rose-400">{line}</span>
                    ) : line.includes("[WARNING]") ? (
                      <span className="text-amber-300">{line}</span>
                    ) : line.includes("Run polling for bot") || line.includes("VERIFIED") ? (
                      <span className="text-emerald-300 font-bold">{line}</span>
                    ) : (
                      <span className="text-slate-300">{line}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "simulator" && (
          <TelegramSimulator
            cooldowns={cooldowns}
            onApplyCooldown={handleApplyCooldown}
            onResetCooldowns={handleResetCooldowns}
          />
        )}

        {activeTab === "questions" && <QuestionBankExplorer />}

        {activeTab === "cooldowns" && (
          <CooldownManager
            cooldowns={cooldowns}
            onApplyCooldown={handleApplyCooldown}
            onResetCooldowns={handleResetCooldowns}
            onRemoveSingleCooldown={handleRemoveSingleCooldown}
          />
        )}

        {activeTab === "setup" && <BotSetupGuide />}
      </main>

      {/* Footer */}
      <footer className="border-t border-indigo-800/80 bg-indigo-950/90 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3 text-xs font-bold uppercase tracking-widest text-indigo-400 font-mono">
            <span className="text-amber-400">/CHOOSE</span>
            <span className="text-rose-400">/STOPGLN</span>
            <span className="text-emerald-400">/APPROVEGLN</span>
            <span className="text-indigo-300">/LEADERBOARD</span>
          </div>
          <div className="text-xs text-indigo-400 font-mono">
            GLN Quiz Bot PROD-v2.0 • 15s Timer • 3h Cooldown • Async aiogram 3 & SQLAlchemy
          </div>
        </div>
      </footer>
    </div>
  );
}
