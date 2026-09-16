import React, { useState, useEffect } from "react";
import { Subject } from "../types";
import { ALL_SUBJECTS } from "../data/mockQuestions";
import { Clock, AlertCircle, PlayCircle, RefreshCw, CheckCircle2, Shield } from "lucide-react";

interface CooldownManagerProps {
  cooldowns: Record<string, number>;
  onApplyCooldown: (subject: Subject) => void;
  onResetCooldowns: () => void;
  onRemoveSingleCooldown: (subject: Subject) => void;
}

export const CooldownManager: React.FC<CooldownManagerProps> = ({
  cooldowns,
  onApplyCooldown,
  onResetCooldowns,
  onRemoveSingleCooldown,
}) => {
  const [now, setNow] = useState<number>(Date.now());
  const groupId = "-1001928374650";

  // Update time every second to refresh countdown timers
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Overview Banner */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-3xl p-6 border border-indigo-700/80 shadow-xl space-y-4 text-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-black text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-400" />
              Subject 3-Hour Cooldown Architecture
            </h2>
            <p className="text-xs text-indigo-300 mt-1 max-w-2xl leading-relaxed">
              When an admin finishes or stops a quiz with <code className="text-amber-300 bg-indigo-950 px-1 py-0.5 rounded font-mono">/Stopgln</code>, that specific subject enters a strict <b className="text-white">3-hour cooldown</b> in that Telegram group.
              The remaining 7 subjects remain fully available for immediate play.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onResetCooldowns}
              className="px-3.5 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 rounded-xl border border-rose-500/40 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-rose-400" />
              Reset All Cooldowns
            </button>
          </div>
        </div>

        {/* Rule Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 border-t border-indigo-800/80 text-xs">
          <div className="p-3.5 bg-indigo-950/80 rounded-2xl border border-indigo-800">
            <div className="font-bold text-amber-300 flex items-center gap-1.5">⏱️ Cooldown Duration</div>
            <div className="text-indigo-300 mt-1">Exactly 3 hours (10,800 seconds)</div>
          </div>
          <div className="p-3.5 bg-indigo-950/80 rounded-2xl border border-indigo-800">
            <div className="font-bold text-amber-300 flex items-center gap-1.5">🎯 Group Isolation</div>
            <div className="text-indigo-300 mt-1">Cooldown applies per group; other groups are unaffected</div>
          </div>
          <div className="p-3.5 bg-indigo-950/80 rounded-2xl border border-indigo-800">
            <div className="font-bold text-amber-300 flex items-center gap-1.5">🔄 Independent Subjects</div>
            <div className="text-indigo-300 mt-1">Other 7 subjects remain instantly accessible</div>
          </div>
        </div>
      </div>

      {/* 8 Subjects Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {ALL_SUBJECTS.map((subj) => {
          const key = `${groupId}:${subj.id}`;
          const expiry = cooldowns[key];
          const isCooldowned = Boolean(expiry && expiry > now);
          const remainingSec = isCooldowned ? Math.max(0, Math.ceil((expiry - now) / 1000)) : 0;

          const hours = Math.floor(remainingSec / 3600);
          const minutes = Math.floor((remainingSec % 3600) / 60);
          const seconds = remainingSec % 60;

          const formatTimer = () => {
            const hStr = hours.toString().padStart(2, "0");
            const mStr = minutes.toString().padStart(2, "0");
            const sStr = seconds.toString().padStart(2, "0");
            return `${hStr}:${mStr}:${sStr}`;
          };

          return (
            <div
              key={subj.id}
              className={`rounded-3xl p-5 border transition-all shadow-xl ${
                isCooldowned
                  ? "bg-indigo-900/90 border-2 border-rose-500/60"
                  : "bg-indigo-900/60 border border-indigo-700/80 hover:border-amber-400/60"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <span className="text-2xl">{subj.icon}</span>
                  <div>
                    <h3 className="text-sm font-bold text-white">{subj.name}</h3>
                    <p className="text-[11px] text-indigo-300">{subj.english}</p>
                  </div>
                </div>

                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                    isCooldowned
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                      : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  }`}
                >
                  {isCooldowned ? "Cooldown Active" : "Ready"}
                </span>
              </div>

              {/* Status & Timer */}
              <div className="mt-4 pt-3 border-t border-indigo-800/80 space-y-2">
                {isCooldowned ? (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-rose-300 font-bold uppercase tracking-wider text-[10px]">⏳ Remaining:</span>
                      <span className="font-mono font-black text-rose-400 text-sm">
                        {formatTimer()}
                      </span>
                    </div>
                    <p className="text-[11px] text-indigo-300 leading-snug">
                      Telegram message sent to group:
                      <code className="text-[10px] bg-indigo-950 px-2 py-1 rounded-lg block mt-1 text-rose-300 border border-indigo-800 font-mono">
                        ⚠️ {subj.name} is on cooldown. Available in: {hours}h {minutes}m.
                      </code>
                    </p>
                  </div>
                ) : (
                  <div className="text-xs text-indigo-300 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Instant start enabled via /Choose</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="mt-4 pt-2 flex items-center gap-2">
                {isCooldowned ? (
                  <button
                    onClick={() => onRemoveSingleCooldown(subj.id as Subject)}
                    className="w-full py-2 px-3 bg-indigo-950 hover:bg-indigo-800 text-indigo-200 border border-indigo-700 rounded-xl text-xs font-bold transition-colors cursor-pointer"
                  >
                    Clear Cooldown
                  </button>
                ) : (
                  <button
                    onClick={() => onApplyCooldown(subj.id as Subject)}
                    className="w-full py-2 px-3 bg-amber-400 hover:bg-amber-300 text-indigo-950 rounded-xl text-xs font-black transition-colors cursor-pointer uppercase shadow-md shadow-amber-400/20"
                  >
                    Simulate 3h Cooldown
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
