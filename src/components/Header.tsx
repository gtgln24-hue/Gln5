import React from "react";
import { MessageSquare, BookOpen, Clock, ShieldCheck, Terminal, Power, Download } from "lucide-react";

interface HeaderProps {
  activeTab: "simulator" | "questions" | "cooldowns" | "setup";
  setActiveTab: (tab: "simulator" | "questions" | "cooldowns" | "setup") => void;
  activeCooldownCount: number;
  botRunning?: boolean;
  onToggleBot?: () => void;
  isTogglingBot?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  activeCooldownCount,
  botRunning = true,
  onToggleBot,
  isTogglingBot = false,
}) => {
  return (
    <header className="border-b border-indigo-700 bg-indigo-900 shadow-lg sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-18 py-2 gap-3">
          {/* Brand Logo & Details */}
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 bg-amber-400 rounded-full flex items-center justify-center text-indigo-950 font-black text-lg shadow-inner ring-2 ring-amber-300/40 shrink-0">
              GLN
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black tracking-tight uppercase text-white">
                  GLN Quiz Bot
                </h1>
                <span className="text-amber-400 font-bold text-xs px-2 py-0.5 border border-amber-400/80 rounded bg-amber-400/10 font-mono">
                  PROD-v2.0
                </span>
                <span className="hidden lg:inline-flex items-center gap-1.5 text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  @Glnquizbot (ID: 8518332185)
                </span>
              </div>
              <p className="text-indigo-300 text-xs font-mono uppercase tracking-widest hidden sm:block">
                Admin & Owner Control Terminal • 8 Hindi Subjects
              </p>
            </div>
          </div>

          {/* Right Section: Bot Run Switch + Navigation Tabs */}
          <div className="flex items-center gap-3 flex-wrap sm:flex-nowrap justify-end">
            {/* Interactive Bot Run Switch in Header */}
            {onToggleBot && (
              <div
                id="header-bot-switch-container"
                className="flex items-center gap-2 bg-indigo-950/90 border border-indigo-700/90 px-3 py-1 rounded-xl shadow-inner select-none"
              >
                <div className="flex flex-col text-right">
                  <span className="text-[10px] uppercase font-mono text-indigo-300 font-bold tracking-wider leading-tight">
                    Bot Switch
                  </span>
                  <span
                    className={`text-[11px] font-mono font-bold flex items-center gap-1 justify-end leading-tight ${
                      botRunning ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        botRunning ? "bg-emerald-400 animate-ping" : "bg-rose-500"
                      }`}
                    />
                    {isTogglingBot ? "WAIT..." : botRunning ? "ON" : "OFF"}
                  </span>
                </div>

                <button
                  id="header-bot-power-toggle"
                  type="button"
                  role="switch"
                  aria-checked={botRunning}
                  disabled={isTogglingBot}
                  onClick={onToggleBot}
                  title={botRunning ? "Click to Stop Telegram Bot" : "Click to Start Telegram Bot"}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-indigo-900 ${
                    botRunning ? "bg-emerald-500 hover:bg-emerald-400" : "bg-slate-700 hover:bg-slate-600"
                  } ${isTogglingBot ? "opacity-60 cursor-not-allowed" : ""}`}
                >
                  <span
                    aria-hidden="true"
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out flex items-center justify-center ${
                      botRunning ? "translate-x-5" : "translate-x-0"
                    }`}
                  >
                    <Power
                      className={`w-3 h-3 ${
                        botRunning ? "text-emerald-600" : "text-slate-500"
                      }`}
                    />
                  </span>
                </button>
              </div>
            )}

            {/* Navigation Tabs */}
            <nav className="flex items-center gap-1 bg-indigo-950/80 border border-indigo-800/80 p-1.5 rounded-xl shadow-inner">
              <button
                id="tab-simulator"
                onClick={() => setActiveTab("simulator")}
                className={`flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-all cursor-pointer ${
                  activeTab === "simulator"
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/30"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/60"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Live Simulator</span>
              </button>

              <button
                id="tab-questions"
                onClick={() => setActiveTab("questions")}
                className={`flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-all cursor-pointer ${
                  activeTab === "questions"
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/30"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/60"
                }`}
              >
                <BookOpen className="w-4 h-4" />
                <span>Question Bank</span>
              </button>

              <button
                id="tab-cooldowns"
                onClick={() => setActiveTab("cooldowns")}
                className={`flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-all relative cursor-pointer ${
                  activeTab === "cooldowns"
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/30"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/60"
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>3h Cooldowns</span>
                {activeCooldownCount > 0 && (
                  <span className="inline-flex items-center justify-center px-1.5 py-0.2 text-[10px] font-black rounded-full bg-rose-500 text-white shadow-sm font-mono">
                    {activeCooldownCount}
                  </span>
                )}
              </button>

              <button
                id="tab-setup"
                onClick={() => setActiveTab("setup")}
                className={`flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-all cursor-pointer ${
                  activeTab === "setup"
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/30"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/60"
                }`}
              >
                <Terminal className="w-4 h-4" />
                <span className="hidden md:inline">Bot Code & Docs</span>
                <span className="md:hidden">Docs</span>
              </button>
            </nav>

            {/* 1-Click Direct ZIP Download */}
            <a
              id="header-download-zip-btn"
              href="/api/download/bot-zip"
              download="gln-quiz-bot-source.zip"
              title="Download Complete Bot Source Code as ZIP"
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl bg-amber-400 hover:bg-amber-300 text-indigo-950 transition-all shadow-md shrink-0 cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Download ZIP</span>
            </a>
          </div>
        </div>
      </div>
    </header>
  );
};
