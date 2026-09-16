import React, { useState, useEffect } from "react";
import { Question, Subject } from "../types";
import { ALL_SUBJECTS, INITIAL_QUESTIONS } from "../data/mockQuestions";
import { Search, Sparkles, BookOpen, Filter, CheckCircle, ExternalLink, Loader2 } from "lucide-react";

export const QuestionBankExplorer: React.FC = () => {
  const [questions, setQuestions] = useState<Question[]>(INITIAL_QUESTIONS);
  const [selectedSubject, setSelectedSubject] = useState<string>("All");
  const [selectedExam, setSelectedExam] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loadingAiId, setLoadingAiId] = useState<string | null>(null);
  const [aiExplanations, setAiExplanations] = useState<Record<string, { text: string; engine?: string }>>({});

  // Fetch question bank from API if running
  useEffect(() => {
    fetch("/api/questions")
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error("API not available");
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setQuestions(data);
        }
      })
      .catch(() => {
        // Fallback to INITIAL_QUESTIONS
      });
  }, []);

  // Filter questions
  const filteredQuestions = questions.filter((q) => {
    const matchesSubject = selectedSubject === "All" || q.subject === selectedSubject;
    const matchesExam = selectedExam === "All" || (q.exam_name && q.exam_name.includes(selectedExam));
    const queryLower = searchQuery.toLowerCase();
    const matchesSearch =
      !searchQuery ||
      q.question.toLowerCase().includes(queryLower) ||
      q.correct_answer.toLowerCase().includes(queryLower) ||
      (q.topic && q.topic.toLowerCase().includes(queryLower));

    return matchesSubject && matchesExam && matchesSearch;
  });

  // Unique exams list
  const exams = ["All", "UPSC", "UPPSC", "SSC", "NEET", "JEE", "BPSC", "RRB", "CDS"];

  const handleExplainWithAi = async (q: Question) => {
    setLoadingAiId(q.id);
    try {
      const res = await fetch("/api/ai/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q.question,
          correctAnswer: q.correct_answer,
          subject: q.subject,
          topic: q.topic,
        }),
      });
      const data = await res.json();
      setAiExplanations((prev) => ({
        ...prev,
        [q.id]: {
          text: data.explanation || "व्याख्या प्राप्त नहीं हो सकी।",
          engine: data.engine || "builtin",
        },
      }));
    } catch (e) {
      setAiExplanations((prev) => ({
        ...prev,
        [q.id]: {
          text: `स्पष्टीकरण: '${q.correct_answer}' इस प्रश्न का प्रामाणिक उत्तर है।`,
          engine: "builtin",
        },
      }));
    } finally {
      setLoadingAiId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Search & Filter Bar */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-2xl p-5 border border-indigo-700/80 shadow-xl space-y-4 text-slate-100">
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-amber-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search questions in Hindi or English (e.g., संधि, संविधान, Xylem, आवर्त सारणी)..."
              className="w-full bg-indigo-950 border border-indigo-700/80 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-indigo-400/60 focus:outline-hidden focus:border-amber-400 focus:bg-indigo-950/90 font-sans"
            />
          </div>

          {/* Exam Tag Filter */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0 text-xs">
            <span className="text-amber-400 font-bold uppercase tracking-wider shrink-0 flex items-center gap-1">
              <Filter className="w-3 h-3" /> Exam:
            </span>
            {exams.map((exam) => (
              <button
                key={exam}
                onClick={() => setSelectedExam(exam)}
                className={`px-3 py-1.5 rounded-xl font-bold transition-all shrink-0 cursor-pointer ${
                  selectedExam === exam
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/20"
                    : "bg-indigo-950/80 hover:bg-indigo-800 text-indigo-200 border border-indigo-800"
                }`}
              >
                {exam}
              </button>
            ))}
          </div>
        </div>

        {/* 8 Subjects Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-t border-indigo-800/80 pt-3">
          <button
            onClick={() => setSelectedSubject("All")}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
              selectedSubject === "All"
                ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/20"
                : "bg-indigo-950/80 hover:bg-indigo-800 text-indigo-200 border border-indigo-800"
            }`}
          >
            All Subjects ({questions.length})
          </button>
          {ALL_SUBJECTS.map((subj) => {
            const count = questions.filter((q) => q.subject === subj.id).length;
            const isSelected = selectedSubject === subj.id;
            return (
              <button
                key={subj.id}
                onClick={() => setSelectedSubject(subj.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
                  isSelected
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/20"
                    : "bg-indigo-950/80 hover:bg-indigo-800 text-indigo-200 border border-indigo-800"
                }`}
              >
                <span>{subj.icon}</span>
                <span>{subj.name}</span>
                <span
                  className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                    isSelected
                      ? "bg-indigo-950/20 text-indigo-950 font-bold"
                      : "bg-indigo-900 text-indigo-300"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Questions List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-indigo-300 px-1">
          <span>
            Showing <b className="text-amber-400 font-mono">{filteredQuestions.length}</b> verified questions
          </span>
          <span className="hidden sm:inline text-indigo-400">Questions are randomly shuffled during live 100-question quiz sessions</span>
        </div>

        {filteredQuestions.length === 0 ? (
          <div className="bg-indigo-900/40 rounded-3xl p-12 border border-indigo-800 text-center space-y-3">
            <BookOpen className="w-12 h-12 text-indigo-400 mx-auto" />
            <p className="text-base font-bold text-white">No questions found</p>
            <p className="text-xs text-indigo-300">
              Try adjusting your search query or switching the subject filter.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredQuestions.map((q, idx) => {
              return (
                <div
                  key={q.id || idx}
                  className="bg-white rounded-3xl p-5 sm:p-6 border-2 border-indigo-100 shadow-xl space-y-3.5 hover:border-amber-400 transition-colors text-slate-800"
                >
                  {/* Top tags */}
                  <div className="flex items-center justify-between text-xs">
                    <span className="inline-flex items-center gap-1 font-bold text-indigo-700 bg-indigo-100 px-3 py-1 rounded-full text-xs uppercase tracking-wider">
                      {q.subject}
                    </span>
                    {q.exam_name && (
                      <span className="font-bold text-amber-700 bg-amber-50 px-3 py-1 rounded-full text-xs uppercase tracking-wider border border-amber-200">
                        📚 {q.exam_name} {q.exam_year ? `(${q.exam_year})` : ""}
                      </span>
                    )}
                  </div>

                  {/* Question Text */}
                  <h4 className="text-base font-bold text-slate-900 leading-snug">
                    {q.question}
                  </h4>

                  {/* Topic & Source */}
                  {(q.topic || q.source_reference) && (
                    <div className="text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 space-y-1">
                      {q.topic && (
                        <div>
                          <span className="font-bold text-slate-700">📖 टॉपिक:</span> {q.topic}
                        </div>
                      )}
                      {q.source_reference && (
                        <div className="text-slate-500 truncate">
                          <span className="font-bold text-slate-700">ℹ️ स्रोत:</span>{" "}
                          {q.source_reference}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Options */}
                  <div className="space-y-2 text-xs">
                    {q.options.map((opt, oIdx) => {
                      const isCorrect = opt === q.correct_answer;
                      return (
                        <div
                          key={oIdx}
                          className={`p-3 rounded-2xl flex items-center justify-between font-bold border-2 transition-all ${
                            isCorrect
                              ? "bg-emerald-50 text-emerald-950 border-emerald-500 shadow-xs"
                              : "bg-slate-50/70 text-slate-700 border-slate-200"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black ${
                                isCorrect
                                  ? "bg-emerald-600 text-white"
                                  : "bg-slate-200 text-slate-700"
                              }`}
                            >
                              {String.fromCharCode(65 + oIdx)}
                            </span>
                            <span>{opt}</span>
                          </div>
                          {isCorrect && (
                            <span className="text-[11px] text-emerald-700 flex items-center gap-1 font-bold">
                              <CheckCircle className="w-3.5 h-3.5" /> सही उत्तर
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* AI Explanation Card */}
                  {aiExplanations[q.id] && (
                    <div className="p-3.5 bg-indigo-50 border border-indigo-200 rounded-2xl text-xs text-indigo-950 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="font-bold flex items-center gap-1.5 text-indigo-900 uppercase tracking-wider text-[11px]">
                          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                          <span>हिंदी व्याख्या:</span>
                        </div>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-200/60 text-indigo-900 border border-indigo-300">
                          {aiExplanations[q.id].engine === "gemini"
                            ? "⚡ Gemini AI"
                            : "✨ Built-in Engine (No Key Needed)"}
                        </span>
                      </div>
                      <p className="leading-relaxed text-slate-800">{aiExplanations[q.id].text}</p>
                    </div>
                  )}

                  {/* Action Footer */}
                  <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-[11px] text-slate-400 font-mono font-medium">ID: {q.id}</span>
                    <button
                      onClick={() => handleExplainWithAi(q)}
                      disabled={loadingAiId === q.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-indigo-950 font-black transition-colors cursor-pointer text-xs shadow-xs uppercase"
                    >
                      {loadingAiId === q.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Generating...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5 text-indigo-950" />
                          <span>Explain with AI</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
