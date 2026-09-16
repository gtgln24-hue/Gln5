import React, { useState, useEffect, useRef } from "react";
import {
  Subject,
  QuizMessage,
  Question,
  UserStats,
  VoterInfo,
} from "../types";
import { ALL_SUBJECTS, INITIAL_QUESTIONS } from "../data/mockQuestions";
import {
  Send,
  User,
  Shield,
  Clock,
  Play,
  Square,
  AlertTriangle,
  Award,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Lightbulb,
  Eye,
  X,
  Pin,
  BarChart2,
  Users,
} from "lucide-react";

interface TelegramSimulatorProps {
  cooldowns: Record<string, number>;
  onApplyCooldown: (subject: Subject) => void;
  onResetCooldowns: () => void;
}

export const TelegramSimulator: React.FC<TelegramSimulatorProps> = ({
  cooldowns,
  onApplyCooldown,
  onResetCooldowns,
}) => {
  // Current simulated user role
  const [userRole, setUserRole] = useState<"admin" | "member" | "owner">("admin");
  const [isBotAdmin, setIsBotAdmin] = useState<boolean>(true);
  const [isGroupApproved, setIsGroupApproved] = useState<boolean>(true);

  // Group metadata
  const groupId = "-1001928374650";
  const groupName = "🎓 Hindi Pratiyogita Pariksha Group (UPSC / SSC / State PCS)";

  // Chat message history
  const [messages, setMessages] = useState<QuizMessage[]>([
    {
      id: "m_welcome",
      sender: "bot",
      senderName: "GLN Quiz Bot",
      timestamp: "10:00 AM",
      text: "👋 <b>Welcome to GLN Quiz Bot!</b>\n\nGroup Admins can start a Hindi quiz anytime using:\n👉 <b>/Choose</b>\n\n<i>Bot is active with 15-second timers, 8 competitive exam subjects, and 3-hour subject cooldowns.</i>",
      type: "text",
    },
  ]);

  const [inputCommand, setInputCommand] = useState<string>("/Choose");

  // Active quiz session state
  const [activeSession, setActiveSession] = useState<{
    sessionId: string;
    subject: Subject;
    optionsCount: number;
    currentQuestionIndex: number;
    totalQuestions: number;
    isRunning: boolean;
    isPaused: boolean;
    timerSeconds: number;
    userAnswered: boolean;
    consecutiveEmpty: number;
  } | null>(null);

  // Question sequence for this session (simulating 100 questions pool)
  const [sessionQuestions, setSessionQuestions] = useState<Question[]>([]);

  // User private alert popup (simulating Telegram answer_callback_query show_alert=True)
  const [privateAlert, setPrivateAlert] = useState<{
    show: boolean;
    title: string;
    message: string;
    isSuccess: boolean;
  } | null>(null);

  // View Votes modal data (simulating Telegram View Votes sheet from video)
  const [votesModalData, setVotesModalData] = useState<{
    show: boolean;
    questionIndex: number;
    totalQuestions: number;
    questionText: string;
    tagline: string;
    options: string[];
    correctAnswer: string;
    correctLetter: string;
    optionVotes: Record<string, number>;
    totalVotes: number;
    voters: Record<string, VoterInfo[]>;
  } | null>(null);

  // Pinned message banner visibility (as seen in video)
  const [pinnedVisible, setPinnedVisible] = useState<boolean>(true);

  // Participant live scores for current session
  const [participants, setParticipants] = useState<Record<string, { correct: number; wrong: number }>>({
    You: { correct: 0, wrong: 0 },
    "Ramesh_IAS": { correct: 0, wrong: 0 },
    "Pooja_Sharma": { correct: 0, wrong: 0 },
    "Vikas_Divyakirti_Fan": { correct: 0, wrong: 0 },
    "Anjali_Verma": { correct: 0, wrong: 0 },
  });

  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // 15-Second active question timer loop
  useEffect(() => {
    if (!activeSession || !activeSession.isRunning || activeSession.isPaused) {
      return;
    }

    if (activeSession.timerSeconds <= 0) {
      handleQuestionTimeout();
      return;
    }

    const interval = setInterval(() => {
      setActiveSession((prev) => {
        if (!prev || !prev.isRunning || prev.isPaused) return prev;
        return {
          ...prev,
          timerSeconds: Math.max(0, prev.timerSeconds - 1),
        };
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [activeSession?.timerSeconds, activeSession?.isRunning, activeSession?.isPaused]);

  // Handle command submission
  const handleSendCommand = (cmdText?: string) => {
    const text = (cmdText || inputCommand).trim();
    if (!text) return;
    setInputCommand("");

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // 1. Add user message
    const userMsg: QuizMessage = {
      id: `u_${Date.now()}`,
      sender: userRole === "admin" ? "admin" : userRole === "owner" ? "admin" : "member",
      senderName: userRole === "admin" ? "Admin (You)" : userRole === "owner" ? "Bot Owner (You)" : "Group Member (You)",
      timestamp: timeStr,
      text: text,
      type: "text",
    };
    setMessages((prev) => [...prev, userMsg]);

    // Parse commands
    if (text === "/Choose" || text.toLowerCase() === "/choose") {
      processChooseCommand(timeStr);
    } else if (text === "/Stopgln" || text.toLowerCase() === "/stopgln") {
      processStopCommand(timeStr);
    } else if (text.startsWith("/Approvegln")) {
      processApproveCommand(text, timeStr);
    } else if (text === "/leaderboard") {
      processLeaderboardCommand(timeStr);
    } else if (text.toLowerCase().startsWith("/broadcast")) {
      processBroadcastCommand(text, timeStr);
    } else {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "ℹ️ Available commands:\n• <b>/Choose</b> — Start a quiz session (Admin only)\n• <b>/Stopgln</b> — Stop current quiz and view results (Admin only)\n• <b>/Approvegln &lt;groupId&gt;</b> — Approve group (Bot Owner only)\n• <b>/broadcast &lt;message&gt;</b> — Broadcast message to all users/groups (Bot Owner only)\n• <b>/leaderboard</b> — View group rankings",
            type: "text",
          },
        ]);
      }, 400);
    }
  };

  // 1. Process /Choose
  const processChooseCommand = (timeStr: string) => {
    setTimeout(() => {
      // Check bot admin rights
      if (!isBotAdmin) {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "⚠️ <b>PLEASE MAKE ME ADMIN IN YOUR GROUP</b>\n\nI require administrator permissions to manage 15-second timers and inline quiz keyboards properly.",
            type: "error",
          },
        ]);
        return;
      }

      // Check group approval status
      if (!isGroupApproved) {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: `⚠️ <b>PLEASE CONTACT MY OWNER AND GET YOUR GROUP APPROVED.</b>\n\n📋 <b>Group ID:</b> <code>${groupId}</code>\n<i>Quizzes cannot start until the Bot Owner approves this group.</i>`,
            type: "error",
          },
        ]);
        return;
      }

      // Check user permissions
      if (userRole === "member") {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "❌ <b>Only Group Admins or Owners can start a quiz.</b>",
            type: "error",
          },
        ]);
        return;
      }

      // Check if quiz already running
      if (activeSession && activeSession.isRunning) {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "⚠️ <b>A quiz is already running in this group.</b>\nUse <b>/Stopgln</b> to finish it before starting a new one.",
            type: "error",
          },
        ]);
        return;
      }

      // Display Subject Selection Inline Keyboard
      setMessages((prev) => [
        ...prev,
        {
          id: `b_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: "📚 <b>SELECT SUBJECT</b>\n\nPlease select one of the 8 subjects to begin the 100-question quiz session:",
          type: "subject_selection",
        },
      ]);
    }, 300);
  };

  // 2. Select Subject (with 3-hour cooldown check)
  const handleSelectSubject = (subject: Subject) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Check cooldown
    const cooldownExpiry = cooldowns[`${groupId}:${subject}`];
    const now = Date.now();
    if (cooldownExpiry && cooldownExpiry > now) {
      const remainingMinutes = Math.ceil((cooldownExpiry - now) / 60000);
      const hours = Math.floor(remainingMinutes / 60);
      const mins = remainingMinutes % 60;
      const formattedTime = hours > 0 ? `${hours} hours ${mins} minutes` : `${mins} minutes`;

      setMessages((prev) => [
        ...prev,
        {
          id: `b_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `⚠️ <b>${subject} is currently on cooldown.</b>\n\n⏳ <b>Available again in:</b> ${formattedTime}.\n\n<i>Other subjects remain immediately available! Select another subject:</i>`,
          type: "subject_selection",
        },
      ]);
      return;
    }

    // Show Options Count Selection
    setMessages((prev) => [
      ...prev,
      {
        id: `b_${Date.now()}`,
        sender: "bot",
        senderName: "GLN Quiz Bot",
        timestamp: timeStr,
        text: `🎯 <b>SELECT NUMBER OF OPTIONS</b>\n\nSubject: <b>${subject}</b>\n\nHow many options should each question have?`,
        type: "options_selection",
        questionData: {
          subject,
          questionIndex: 0,
          totalQuestions: 100,
          question: INITIAL_QUESTIONS[0],
          options: [],
          correctLetter: "A",
          correctAnswer: "",
          secondsRemaining: 15,
          isLocked: false,
          optionVotes: {},
        },
      },
    ]);
  };

  // 3. Select Option Count and start quiz
  const handleSelectOptionsCount = (subject: Subject, count: number) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Prepare questions pool for this subject
    const filtered = INITIAL_QUESTIONS.filter((q) => q.subject === subject);
    // Expand questions to simulate 100-question session
    const pool: Question[] = [];
    while (pool.length < 100) {
      pool.push(...filtered.sort(() => Math.random() - 0.5));
    }
    const readyQuestions = pool.slice(0, 100);
    setSessionQuestions(readyQuestions);

    setMessages((prev) => [
      ...prev,
      {
        id: `b_prep_${Date.now()}`,
        sender: "bot",
        senderName: "GLN Quiz Bot",
        timestamp: timeStr,
        text: `⏳ <b>PREPARING 100 UNIQUE QUESTIONS...</b>\n\n📚 <b>Subject:</b> ${subject}\n🎯 <b>Format:</b> ${count} Options per question\n⏱️ <b>Timer:</b> 15 seconds per question\n\n<i>Quiz is starting now! Get ready!</i>`,
        type: "text",
      },
    ]);

    // Reset scores
    setParticipants({
      You: { correct: 0, wrong: 0 },
      "Ramesh_IAS": { correct: 0, wrong: 0 },
      "Pooja_Sharma": { correct: 0, wrong: 0 },
      "Vikas_Divyakirti_Fan": { correct: 0, wrong: 0 },
      "Anjali_Verma": { correct: 0, wrong: 0 },
    });

    // Start Session with Question 1
    setTimeout(() => {
      startQuestionIndex(1, subject, count, readyQuestions);
    }, 1200);
  };

  // Helper to construct randomized question
  const startQuestionIndex = (
    index: number,
    subject: Subject,
    optionsCount: number,
    pool: Question[]
  ) => {
    const qRaw = pool[index - 1] || INITIAL_QUESTIONS[0];

    // Adapt options to optionsCount (2, 3, or 4)
    const distractors = qRaw.options.filter((o) => o !== qRaw.correct_answer);
    distractors.sort(() => Math.random() - 0.5);

    const chosenDistractors = distractors.slice(0, optionsCount - 1);
    const combined = [qRaw.correct_answer, ...chosenDistractors].sort(() => Math.random() - 0.5);

    const letters = ["A", "B", "C", "D"];
    const correctIdx = combined.indexOf(qRaw.correct_answer);
    const correctLetter = letters[correctIdx];

    const initialVotes: Record<string, number> = {};
    combined.forEach((opt) => (initialVotes[opt] = 0));

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Build question message
    const qMessage: QuizMessage = {
      id: `q_${index}_${Date.now()}`,
      sender: "bot",
      senderName: "GLN Quiz Bot",
      timestamp: timeStr,
      text: "",
      type: "question",
      questionData: {
        questionIndex: index,
        totalQuestions: 100,
        subject: subject,
        question: qRaw,
        options: combined,
        correctLetter: correctLetter,
        correctAnswer: qRaw.correct_answer,
        secondsRemaining: 15,
        isLocked: false,
        optionVotes: initialVotes,
        tagline: "!!🖤🌹B ⓐ dshah🌹🖤!!",
        voters: {},
      },
    };

    setMessages((prev) => [...prev, qMessage]);

    setActiveSession({
      sessionId: `sim_${Date.now()}`,
      subject,
      optionsCount,
      currentQuestionIndex: index,
      totalQuestions: 100,
      isRunning: true,
      isPaused: false,
      timerSeconds: 15,
      userAnswered: false,
      consecutiveEmpty: 0,
    });
  };

  // 4. Handle User Answer click (with private alert feedback)
  const handleAnswerClick = (messageId: string, selectedOption: string) => {
    if (!activeSession || !activeSession.isRunning || activeSession.userAnswered) {
      if (activeSession?.userAnswered) {
        setPrivateAlert({
          show: true,
          title: "Telegram Alert",
          message: "⚠️ You have already answered this question.",
          isSuccess: false,
        });
      }
      return;
    }

    // Find message
    const targetMsg = messages.find((m) => m.id === messageId);
    if (!targetMsg || !targetMsg.questionData || targetMsg.questionData.isLocked) return;

    const isCorrect = selectedOption === targetMsg.questionData.correctAnswer;

    // Trigger private Telegram callback alert
    if (isCorrect) {
      setPrivateAlert({
        show: true,
        title: "Telegram Answer Feedback",
        message: "🟢 Correct Answer\n✅",
        isSuccess: true,
      });
      setParticipants((prev) => ({
        ...prev,
        You: { ...prev.You, correct: prev.You.correct + 1 },
      }));
    } else {
      setPrivateAlert({
        show: true,
        title: "Telegram Answer Feedback",
        message: "🔴 Wrong Answer\n❌",
        isSuccess: false,
      });
      setParticipants((prev) => ({
        ...prev,
        You: { ...prev.You, wrong: prev.You.wrong + 1 },
      }));
    }

    // Mark user as answered
    setActiveSession((prev) => (prev ? { ...prev, userAnswered: true } : null));

    // Update vote stats & simulate other group members answering
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== messageId || !msg.questionData) return msg;

        const updatedVotes = { ...msg.questionData.optionVotes };
        updatedVotes[selectedOption] = (updatedVotes[selectedOption] || 0) + 1;

        // Simulate other answers
        msg.questionData.options.forEach((opt) => {
          if (opt === msg.questionData?.correctAnswer) {
            updatedVotes[opt] = (updatedVotes[opt] || 0) + Math.floor(Math.random() * 8) + 4;
          } else {
            updatedVotes[opt] = (updatedVotes[opt] || 0) + Math.floor(Math.random() * 4);
          }
        });

        return {
          ...msg,
          questionData: {
            ...msg.questionData,
            userAnswer: selectedOption,
            optionVotes: updatedVotes,
          },
        };
      })
    );

    // Also update simulated members scores
    setParticipants((prev) => ({
      ...prev,
      "Ramesh_IAS": {
        correct: prev["Ramesh_IAS"].correct + (Math.random() > 0.25 ? 1 : 0),
        wrong: prev["Ramesh_IAS"].wrong + (Math.random() > 0.75 ? 1 : 0),
      },
      "Pooja_Sharma": {
        correct: prev["Pooja_Sharma"].correct + (Math.random() > 0.35 ? 1 : 0),
        wrong: prev["Pooja_Sharma"].wrong + (Math.random() > 0.65 ? 1 : 0),
      },
      "Vikas_Divyakirti_Fan": {
        correct: prev["Vikas_Divyakirti_Fan"].correct + (Math.random() > 0.2 ? 1 : 0),
        wrong: prev["Vikas_Divyakirti_Fan"].wrong + (Math.random() > 0.8 ? 1 : 0),
      },
      "Anjali_Verma": {
        correct: prev["Anjali_Verma"].correct + (Math.random() > 0.4 ? 1 : 0),
        wrong: prev["Anjali_Verma"].wrong + (Math.random() > 0.6 ? 1 : 0),
      },
    }));
  };

  // 5. 15-Second Question Timeout Handler
  const handleQuestionTimeout = () => {
    if (!activeSession) return;

    const currentIndex = activeSession.currentQuestionIndex;
    const total = activeSession.totalQuestions;
    const isFinished = currentIndex >= total;
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Lock the last question message and build the voter distribution from the video
    let lastQMsg: QuizMessage | undefined;
    setMessages((prev) => {
      const updated = [...prev];
      for (let i = updated.length - 1; i >= 0; i--) {
        if (updated[i].type === "question" && updated[i].questionData) {
          const qd = updated[i].questionData!;
          const currentVoters: Record<string, VoterInfo[]> = {};
          qd.options.forEach((opt) => {
            currentVoters[opt] = [];
          });

          // Realistic voter profiles matching Telegram Quiz Bot screenshots
          const nowTime = "today 17:20";

          // If current user answered
          if (qd.userAnswer) {
            currentVoters[qd.userAnswer].push({
              name: "You",
              avatarColor: "bg-emerald-500",
              time: nowTime,
            });
          }

          // Correct answer voter (matching Image 4)
          currentVoters[qd.correctAnswer].push({
            name: "___♥_V-ikash___ 🌍",
            avatarColor: "bg-rose-600",
            time: nowTime,
          });

          // Other option voter (matching Image 4)
          const distractors = qd.options.filter((o) => o !== qd.correctAnswer);
          if (distractors.length > 0) {
            currentVoters[distractors[0]].push({
              name: "Mr. Classic 👆 Look@",
              avatarColor: "bg-amber-600",
              time: nowTime,
            });
          }

          // Optional 3rd voter if 3+ options
          if (distractors.length > 1 && Math.random() > 0.4) {
            currentVoters[distractors[1]].push({
              name: "Lalita singh",
              avatarColor: "bg-pink-500",
              time: nowTime,
            });
          }

          const finalVotes: Record<string, number> = {};
          qd.options.forEach((opt) => {
            finalVotes[opt] = currentVoters[opt].length;
          });

          updated[i] = {
            ...updated[i],
            questionData: {
              ...qd,
              isLocked: true,
              secondsRemaining: 0,
              optionVotes: finalVotes,
              tagline: "!!🖤🌹B ⓐ dshah🌹🖤!!",
              voters: currentVoters,
            },
          };
          lastQMsg = updated[i];
          break;
        }
      }
      return updated;
    });

    if (isFinished) {
      finishQuizSession();
    } else {
      // Immediate transition to next question without delay as soon as 15s finishes
      setTimeout(() => {
        startQuestionIndex(currentIndex + 1, activeSession.subject, activeSession.optionsCount, sessionQuestions);
      }, 50);
    }
  };

  // 6. Stop quiz via /Stopgln or Finish
  const processStopCommand = (timeStr: string) => {
    if (userRole === "member") {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "❌ <b>Only Group Admins, Group Owners, or the Bot Owner can stop a quiz.</b>",
            type: "error",
          },
        ]);
      }, 300);
      return;
    }

    if (!activeSession || !activeSession.isRunning) {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "⚠️ <i>No active quiz is currently running in this group.</i>",
            type: "text",
          },
        ]);
      }, 300);
      return;
    }

    const currentSubj = activeSession.subject;
    const currentQ = activeSession.currentQuestionIndex;

    // Apply 3-hour cooldown
    onApplyCooldown(currentSubj);

    // Stop active session
    setActiveSession(null);

    // Render leaderboard
    setTimeout(() => {
      displayFinalLeaderboard(`🏁 <b>QUIZ STOPPED</b>\n<i>Stopped by Admin after Question ${currentQ}/100</i>`, currentQ, currentSubj);
    }, 400);
  };

  const finishQuizSession = () => {
    if (!activeSession) return;
    const currentSubj = activeSession.subject;
    const totalQ = activeSession.totalQuestions;

    onApplyCooldown(currentSubj);
    setActiveSession(null);

    displayFinalLeaderboard("🏆 <b>QUIZ COMPLETED</b>", totalQ, currentSubj);
  };

  const displayFinalLeaderboard = (title: string, totalQuestionsAsked: number, subject: Subject) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Calculate ranked participants
    const userArray = Object.entries(participants).map(([uname, stats]) => {
      const s = stats as { correct: number; wrong: number };
      const total = s.correct + s.wrong;
      const acc = total > 0 ? Math.round((s.correct / total) * 100) : 0;
      return {
        username: uname,
        correct: s.correct,
        wrong: s.wrong,
        total,
        accuracy: acc,
      };
    });

    userArray.sort((a, b) => b.correct - a.correct || b.accuracy - a.accuracy);

    const medals = ["🥇", "🥈", "🥉"];
    const rankingLines = userArray.map((u, i) => {
      const badge = medals[i] || `<b>${i + 1}.</b>`;
      return `${badge} <b>@${u.username}</b> — <b>${u.correct} Correct</b> | ${u.wrong} Wrong (${u.accuracy}%)`;
    });

    const totalCorrect = userArray.reduce((acc, u) => acc + u.correct, 0);
    const totalWrong = userArray.reduce((acc, u) => acc + u.wrong, 0);

    const boardMsg =
      `${title}\n\n` +
      `📊 <b>FINAL LEADERBOARD</b>\n\n` +
      `${rankingLines.join("\n")}\n\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `📝 <b>Total Questions Asked:</b> ${totalQuestionsAsked}\n` +
      `🟢 <b>Correct Answers:</b> ${totalCorrect}\n` +
      `🔴 <b>Wrong Answers:</b> ${totalWrong}\n` +
      `👥 <b>Total Participants:</b> ${userArray.length}\n\n` +
      `⏳ <b>Cooldown Applied:</b> <b>${subject}</b> is now on cooldown for <b>3 hours</b> in this group.\n` +
      `<i>Other subjects remain immediately available via /Choose.</i>`;

    setMessages((prev) => [
      ...prev,
      {
        id: `lb_${Date.now()}`,
        sender: "bot",
        senderName: "GLN Quiz Bot",
        timestamp: timeStr,
        text: boardMsg,
        type: "leaderboard",
      },
    ]);
  };

  // 7. Pause & Resume Test
  const handleTogglePause = () => {
    if (!activeSession) return;
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (activeSession.isPaused) {
      // Resume
      setActiveSession((prev) => (prev ? { ...prev, isPaused: false } : null));
      setMessages((prev) => [
        ...prev,
        {
          id: `res_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `▶️ <b>Resuming quiz from Question ${activeSession.currentQuestionIndex}/100...</b>`,
          type: "text",
        },
      ]);
    } else {
      // Pause
      setActiveSession((prev) => (prev ? { ...prev, isPaused: true } : null));
      setMessages((prev) => [
        ...prev,
        {
          id: `pause_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `⏸️ <b>Quiz Paused</b>\n\nNo participants are currently answering.\n\n<i>Click the button below to resume from Question ${activeSession.currentQuestionIndex}/100 without losing progress.</i>`,
          type: "pause",
        },
      ]);
    }
  };

  // 8. /Approvegln handler
  const processApproveCommand = (cmdText: string, timeStr: string) => {
    if (userRole !== "owner") {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "❌ <i>Only the Bot Owner can approve groups. (Switch role to 'Bot Owner' at top to test).</i>",
            type: "error",
          },
        ]);
      }, 300);
      return;
    }

    const parts = cmdText.split(" ");
    const targetId = parts[1] || groupId;

    setIsGroupApproved(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: `b_app_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `✅ <b>This group (ID: <code>${targetId}</code>) has been approved successfully.</b>\n\nNow admins can use:\n👉 <b>/Choose</b>`,
          type: "text",
        },
      ]);
    }, 400);
  };

  // 9. /broadcast handler (Owner-Only)
  const processBroadcastCommand = (cmdText: string, timeStr: string) => {
    // 1. Strictly verify owner authorization
    if (userRole !== "owner") {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "❌ You are not authorized to use this command.",
            type: "error",
          },
        ]);
      }, 300);
      return;
    }

    // 2. Extract message text after /broadcast
    const firstSpaceIndex = cmdText.indexOf(" ");
    const broadcastText = firstSpaceIndex !== -1 ? cmdText.slice(firstSpaceIndex).trim() : "";

    if (!broadcastText) {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            sender: "bot",
            senderName: "GLN Quiz Bot",
            timestamp: timeStr,
            text: "⚠️ Please provide a message.\n\nExample:\n/broadcast 🚀 Quiz bot has been updated!",
            type: "text",
          },
        ]);
      }, 300);
      return;
    }

    // 3. Show Preview with confirmation buttons
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: `bcast_prev_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `📢 BROADCAST PREVIEW\n\n${broadcastText}\n\nAre you sure you want to send this?`,
          type: "broadcast_preview",
          broadcastMessage: broadcastText,
        },
      ]);
    }, 300);
  };

  const handleBroadcastCancel = (msgId: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === msgId
          ? {
              ...m,
              text: "❌ Broadcast cancelled.",
              type: "text",
              broadcastMessage: undefined,
            }
          : m
      )
    );
  };

  const handleBroadcastConfirm = (msgId: string, broadcastText: string) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Update preview message to show broadcast started
    setMessages((prev) =>
      prev.map((m) =>
        m.id === msgId
          ? {
              ...m,
              text: `📢 BROADCAST STARTED\n\nMessage:\n${broadcastText}`,
              type: "text",
              broadcastMessage: undefined,
            }
          : m
      )
    );

    // Simulate asynchronous rate-limited delivery and deliver stats to owner
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: `bcast_done_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `✅ BROADCAST COMPLETED\n\n📊 Statistics\n\nTotal: 5\n✅ Sent: 5\n❌ Failed: 0`,
          type: "text",
        },
      ]);
    }, 1000);
  };

  const processLeaderboardCommand = (timeStr: string) => {
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: `b_lb_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text:
            "🏆 <b>ALL-TIME GROUP LEADERBOARD</b>\n\n" +
            "🥇 <b>@Vikas_Divyakirti_Fan</b> — 240 pts (92% acc)\n" +
            "🥈 <b>@Ramesh_IAS</b> — 215 pts (88% acc)\n" +
            "🥉 <b>@Pooja_Sharma</b> — 198 pts (84% acc)\n" +
            "4. <b>@Anjali_Verma</b> — 172 pts (81% acc)\n" +
            "5. <b>@You</b> — 145 pts (85% acc)\n\n" +
            "<i>Use /Choose to play active 100-question sessions!</i>",
          type: "text",
        },
      ]);
    }, 300);
  };

  const handleResetChat = () => {
    setActiveSession(null);
    setMessages([
      {
        id: "m_welcome_reset",
        sender: "bot",
        senderName: "GLN Quiz Bot",
        timestamp: "Just now",
        text: "👋 <b>Chat Reset.</b> Ready to test GLN Quiz Bot commands!\nUse <b>/Choose</b> as an Admin to start.",
        type: "text",
      },
    ]);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Simulator Control Deck */}
      <div className="bg-indigo-900/60 backdrop-blur-md rounded-2xl p-5 border border-indigo-700/80 shadow-xl text-slate-100">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Role switcher */}
          <div>
            <span className="text-xs font-bold text-amber-400 uppercase tracking-wider block mb-1.5">
              Simulate Your Role In Group:
            </span>
            <div className="inline-flex rounded-xl border border-indigo-800 p-1 bg-indigo-950/80 shadow-inner">
              <button
                id="role-admin"
                onClick={() => setUserRole("admin")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  userRole === "admin"
                    ? "bg-amber-400 text-indigo-950 shadow-md shadow-amber-400/20"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/40"
                }`}
              >
                <Shield className="w-3.5 h-3.5" />
                Group Admin
              </button>
              <button
                id="role-member"
                onClick={() => setUserRole("member")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  userRole === "member"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/40"
                }`}
              >
                <User className="w-3.5 h-3.5" />
                Normal Member
              </button>
              <button
                id="role-owner"
                onClick={() => setUserRole("owner")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  userRole === "owner"
                    ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                    : "text-indigo-200 hover:text-white hover:bg-indigo-800/40"
                }`}
              >
                <Award className="w-3.5 h-3.5" />
                Bot Owner
              </button>
            </div>
          </div>

          {/* Bot State Toggles */}
          <div className="flex flex-wrap items-center gap-3 text-xs font-medium">
            <label className="flex items-center gap-2 cursor-pointer bg-indigo-950/80 px-3 py-1.5 rounded-xl border border-indigo-800 text-indigo-200 hover:text-white">
              <input
                type="checkbox"
                checked={isBotAdmin}
                onChange={(e) => setIsBotAdmin(e.target.checked)}
                className="rounded border-indigo-700 text-amber-400 focus:ring-amber-400 accent-amber-400"
              />
              <span>Bot Is Admin</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer bg-indigo-950/80 px-3 py-1.5 rounded-xl border border-indigo-800 text-indigo-200 hover:text-white">
              <input
                type="checkbox"
                checked={isGroupApproved}
                onChange={(e) => setIsGroupApproved(e.target.checked)}
                className="rounded border-indigo-700 text-amber-400 focus:ring-amber-400 accent-amber-400"
              />
              <span>Group Approved</span>
            </label>

            <button
              onClick={onResetCooldowns}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 font-bold transition-colors cursor-pointer"
            >
              <Clock className="w-3.5 h-3.5 text-rose-400" />
              Reset All 3h Cooldowns
            </button>

            <button
              onClick={handleResetChat}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-700 bg-indigo-950/60 text-indigo-200 hover:text-white hover:bg-indigo-800 font-bold transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-amber-400" />
              Reset Feed
            </button>
          </div>
        </div>

        {/* Status Pills */}
        <div className="mt-3.5 pt-3.5 border-t border-indigo-800/80 flex flex-wrap items-center gap-2.5 text-xs text-indigo-300">
          <span className="font-bold text-indigo-200 uppercase text-[11px] tracking-wider">Group ID:</span>
          <code className="bg-indigo-950 px-2 py-0.5 rounded-md text-amber-300 font-mono border border-indigo-800">{groupId}</code>
          <span className="text-indigo-600">•</span>
          <span>15s Question Timer</span>
          <span className="text-indigo-600">•</span>
          <span>3-Hour Cooldown per Subject</span>
          <span className="text-indigo-600">•</span>
          <span>100 Unique Questions/Session</span>
          {activeSession && (
            <span className="ml-auto inline-flex items-center gap-1.5 text-emerald-300 bg-emerald-500/10 px-2.5 py-0.5 rounded-full font-bold border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Active: {activeSession.subject} (Q{activeSession.currentQuestionIndex}/100)
            </span>
          )}
        </div>
      </div>

      {/* Telegram Chat Mock Window */}
      <div className="bg-indigo-950 rounded-3xl overflow-hidden shadow-2xl border border-indigo-700/80 max-w-4xl mx-auto flex flex-col h-[740px]">
        {/* Telegram Header */}
        <div className="bg-indigo-900 px-5 py-3.5 border-b border-indigo-700 flex items-center justify-between shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-full bg-amber-400 flex items-center justify-center text-indigo-950 font-black text-xl shadow-inner ring-2 ring-amber-300/40">
              🎓
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white truncate max-w-[280px] sm:max-w-md">
                  {groupName}
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-400/10 text-amber-400 border border-amber-400/40 uppercase font-mono">
                  Supergroup
                </span>
              </div>
              <p className="text-xs text-indigo-300">1,420 members • 18 online • GLN Quiz Bot Admin</p>
            </div>
          </div>

          {/* Quick Action Buttons for admin */}
          <div className="flex items-center gap-2">
            {activeSession && (
              <>
                <button
                  onClick={handleTogglePause}
                  className="px-2.5 py-1.5 text-xs rounded-lg font-bold bg-indigo-800 hover:bg-indigo-700 text-indigo-100 border border-indigo-600 flex items-center gap-1 transition-all cursor-pointer"
                >
                  {activeSession.isPaused ? <Play className="w-3 h-3 text-emerald-400" /> : <Clock className="w-3 h-3 text-amber-400" />}
                  {activeSession.isPaused ? "Resume" : "Pause"}
                </button>
                <button
                  onClick={() => handleSendCommand("/Stopgln")}
                  className="px-3 py-1.5 text-xs rounded-lg font-bold bg-rose-500 hover:bg-rose-600 text-white shadow-md flex items-center gap-1 transition-all cursor-pointer"
                >
                  <Square className="w-3 h-3" />
                  /STOPGLN
                </button>
              </>
            )}
            <button
              onClick={() => handleSendCommand("/Choose")}
              className="px-3.5 py-1.5 text-xs rounded-lg font-black bg-amber-400 hover:bg-amber-300 text-indigo-950 shadow-md transition-all cursor-pointer uppercase"
            >
              /Choose
            </button>
          </div>
        </div>

        {/* Pinned Message Bar (as seen in user's video) */}
        {pinnedVisible && (
          <div className="bg-[#1e293b] px-4 py-2 border-b border-indigo-800/80 flex items-center justify-between text-xs text-slate-200">
            <div className="flex items-center gap-2 truncate">
              <Pin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <div className="truncate">
                <span className="text-amber-400 font-bold uppercase text-[10px] mr-1.5">
                  Pinned Message:
                </span>
                <span className="text-slate-200 font-medium">
                  [NEET HINDI QUIZ] [HINDI MEDIUM] ⚡ [EXAM ME PUCHHE GAYE SABHI IMPORTANT QUESTIONS]
                </span>
              </div>
            </div>
            <button
              onClick={() => setPinnedVisible(false)}
              className="text-slate-400 hover:text-white p-1 ml-2 cursor-pointer transition-colors"
              title="Dismiss pin"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Chat Feed */}
        <div
          ref={chatContainerRef}
          className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 bg-indigo-950/80"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${
                msg.sender === "admin" || msg.sender === "member"
                  ? "items-end"
                  : "items-start"
              }`}
            >
              {/* Sender Name & Tag */}
              <div className="flex items-center gap-1.5 mb-1 px-1 text-[11px] text-indigo-300">
                <span className="font-bold text-slate-200">{msg.senderName}</span>
                {msg.sender === "bot" && (
                  <span className="px-1.5 py-0.2 rounded text-[9px] bg-amber-400/20 text-amber-300 font-mono font-bold border border-amber-400/30">
                    BOT
                  </span>
                )}
                <span>•</span>
                <span>{msg.timestamp}</span>
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-[90%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.sender === "admin" || msg.sender === "member"
                    ? "bg-indigo-600 text-white rounded-tr-none shadow-lg shadow-indigo-950/50 border border-indigo-500/30"
                    : msg.type === "error"
                    ? "bg-rose-950/80 text-rose-200 border border-rose-800/80 rounded-tl-none shadow-md"
                    : msg.type === "question"
                    ? "w-full sm:max-w-xl !p-0 !bg-transparent !border-0 shadow-none"
                    : "bg-indigo-900/90 text-slate-100 border border-indigo-700/80 rounded-tl-none shadow-lg"
                }`}
              >
                {/* Regular HTML message content */}
                {msg.text && (
                  <div
                    className="whitespace-pre-wrap font-sans"
                    dangerouslySetInnerHTML={{ __html: msg.text }}
                  />
                )}

                {/* 1. Inline Keyboard: Subject Selection */}
                {msg.type === "subject_selection" && (
                  <div className="mt-3 pt-3 border-t border-indigo-700/60 space-y-2">
                    <p className="text-xs text-amber-400 font-bold uppercase tracking-wider mb-2">
                      👇 Tap to choose subject (Admin only):
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {ALL_SUBJECTS.map((subj) => {
                        const isCooldowned = Boolean(
                          cooldowns[`${groupId}:${subj.id}`] &&
                            cooldowns[`${groupId}:${subj.id}`] > Date.now()
                        );
                        return (
                          <button
                            key={subj.id}
                            disabled={userRole === "member"}
                            onClick={() => handleSelectSubject(subj.id as Subject)}
                            className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                              isCooldowned
                                ? "bg-indigo-950/80 border-rose-500/40 text-rose-300 hover:bg-rose-950/40"
                                : "bg-indigo-900/90 hover:bg-indigo-800 border-indigo-700 text-white hover:border-amber-400 shadow-sm"
                            } ${userRole === "member" ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
                          >
                            <span>
                              {subj.icon} {subj.name}
                            </span>
                            {isCooldowned ? (
                              <span className="text-[10px] text-rose-400 font-mono font-bold bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/30">
                                ⏳ 3h Cooldown
                              </span>
                            ) : (
                              <span className="text-[10px] text-emerald-400 font-mono font-bold uppercase">
                                ✅ Ready
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 2. Inline Keyboard: Options Selection */}
                {msg.type === "options_selection" && msg.questionData && (
                  <div className="mt-3 pt-3 border-t border-indigo-700/60 space-y-2">
                    <p className="text-xs text-indigo-200 font-bold uppercase tracking-wider mb-2">
                      👇 Tap to choose options count:
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      {[2, 3, 4].map((count) => (
                        <button
                          key={count}
                          onClick={() => handleSelectOptionsCount(msg.questionData!.subject, count)}
                          className="px-3 py-2.5 bg-amber-400 hover:bg-amber-300 text-indigo-950 rounded-xl text-xs font-black text-center shadow-md transition-all cursor-pointer"
                        >
                          {count} Options
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* 2.5 Broadcast Preview Confirmation Buttons */}
                {msg.type === "broadcast_preview" && msg.broadcastMessage && (
                  <div className="mt-3 pt-3 border-t border-indigo-700/60 space-y-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleBroadcastConfirm(msg.id, msg.broadcastMessage!)}
                        className="flex-1 py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-md transition-all cursor-pointer flex items-center justify-center gap-1"
                      >
                        ✅ SEND
                      </button>
                      <button
                        onClick={() => handleBroadcastCancel(msg.id)}
                        className="flex-1 py-2.5 px-3 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold shadow-md transition-all cursor-pointer flex items-center justify-center gap-1"
                      >
                        ❌ CANCEL
                      </button>
                    </div>
                  </div>
                )}

                {/* 3. Question Card: Locked Poll Results (Video Design) OR Active 15s Countdown */}
                {msg.type === "question" && msg.questionData && (
                  msg.questionData.isLocked ? (
                    /* Exact Poll Result Design from User Screenshots (Image 2 & 3) */
                    <div className="bg-[#17212b] rounded-2xl p-4 sm:p-5 shadow-2xl text-white space-y-3 border border-[#242f3d] flex flex-col w-full max-w-xl">
                      {/* Top Header: Quiz Bot & Admin Pill */}
                      <div className="flex items-center justify-between pb-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[#38bdf8] text-xs font-bold tracking-wide">
                            Quiz Bot
                          </span>
                          <span className="bg-[#1b382b] text-[#4ade80] border border-[#23583c] px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide">
                            Aдмин
                          </span>
                        </div>
                      </div>

                      {/* Header: [48/51] Question Title & Tagline */}
                      <div className="space-y-1">
                        <h2 className="text-white text-base sm:text-[17px] font-bold leading-snug">
                          <span className="text-white font-mono font-bold mr-1.5">
                            [{msg.questionData.questionIndex}/{msg.questionData.totalQuestions}]
                          </span>
                          {msg.questionData.question.question}
                        </h2>
                        {msg.questionData.tagline && (
                          <p className="text-xs text-rose-300/80 italic font-medium tracking-wide">
                            {msg.questionData.tagline}
                          </p>
                        )}
                      </div>

                      {/* Final Results & Overlapping Avatars & Lightbulb (Image 2) */}
                      {(() => {
                        const optVotes = msg.questionData.optionVotes as Record<string, number>;
                        const totalVotes = Object.values(optVotes).reduce((a: number, b: number) => a + Number(b), 0);
                        const votersMap = (msg.questionData.voters || {}) as Record<string, VoterInfo[]>;
                        const allVoters: VoterInfo[] = Object.values(votersMap).flat();

                        return (
                          <>
                            <div className="flex items-center justify-between pt-1 border-t border-slate-700/60 text-xs">
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400 font-normal">
                                  Final Results
                                </span>
                                {allVoters.length > 0 && (
                                  <div className="flex -space-x-1.5 overflow-hidden">
                                    {allVoters.slice(0, 4).map((v, vIdx) => (
                                      <div
                                        key={vIdx}
                                        className={`w-5 h-5 rounded-full ${
                                          v.avatarColor || "bg-indigo-500"
                                        } text-white text-[9px] font-black flex items-center justify-center ring-1 ring-[#17212b]`}
                                        title={v.name}
                                      >
                                        {v.name.charAt(0).toUpperCase()}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div
                                className="w-6 h-6 rounded-full border border-sky-400/50 text-sky-400 flex items-center justify-center text-xs shadow-xs"
                                title="Explanation"
                              >
                                💡
                              </div>
                            </div>

                            {/* Options with horizontal bars (Image 2 & 3) */}
                            <div className="space-y-3 pt-1">
                              {msg.questionData.options.map((opt, idx) => {
                                const count = optVotes[opt] || 0;
                                const pct = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
                                const isCorrect = opt === msg.questionData!.correctAnswer;
                                const voters = votersMap[opt] || [];

                                return (
                                  <div key={idx} className="space-y-1.5">
                                    {/* Option Top Line: Percentage, Option text, Count & Voter Avatar */}
                                    <div className="flex items-center justify-between text-sm">
                                      <div className="flex items-center gap-2.5 text-white font-bold min-w-0">
                                        <span className="font-mono text-sm min-w-[32px]">{pct}%</span>
                                        <span className="truncate">{opt}</span>
                                      </div>
                                      <div className="flex items-center gap-2 shrink-0">
                                        {count > 0 && (
                                          <span className="text-xs text-slate-400 font-mono font-medium">
                                            {count}
                                          </span>
                                        )}
                                        {voters.length > 0 && (
                                          <div
                                            className={`w-5 h-5 rounded-full ${
                                              voters[0].avatarColor || "bg-indigo-500"
                                            } text-white text-[9px] font-black flex items-center justify-center ring-1 ring-[#17212b] shadow-xs`}
                                            title={voters[0].name}
                                          >
                                            {voters[0].name.charAt(0).toUpperCase()}
                                          </div>
                                        )}
                                      </div>
                                    </div>

                                    {/* Option Bottom Line: Colored horizontal bar */}
                                    <div className="flex items-center gap-2">
                                      {isCorrect && (
                                        <div className="w-4 h-4 rounded-full bg-[#22c55e] text-white flex items-center justify-center text-[10px] font-black shrink-0 shadow-xs">
                                          ✓
                                        </div>
                                      )}
                                      <div className="flex-1 h-1.5 bg-[#253242] rounded-full overflow-hidden">
                                        <div
                                          className={`h-full rounded-full transition-all duration-700 ${
                                            isCorrect ? "bg-[#4ade80]" : "bg-[#f87171]"
                                          }`}
                                          style={{ width: `${Math.max(pct > 0 ? 3 : 0, pct)}%` }}
                                        />
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>

                            {/* View Votes Link & Timestamp (Image 2 & 3) */}
                            <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
                              <button
                                onClick={() => {
                                  setVotesModalData({
                                    show: true,
                                    questionIndex: msg.questionData!.questionIndex,
                                    totalQuestions: msg.questionData!.totalQuestions,
                                    questionText: msg.questionData!.question.question,
                                    tagline: msg.questionData!.tagline || "!!🖤🌹B ⓐ dshah🌹🖤!!",
                                    options: msg.questionData!.options,
                                    correctAnswer: msg.questionData!.correctAnswer,
                                    correctLetter: msg.questionData!.correctLetter,
                                    optionVotes: optVotes,
                                    totalVotes: totalVotes,
                                    voters: votersMap,
                                  });
                                }}
                                className="text-[#4ba3e3] hover:text-[#38bdf8] font-semibold text-xs sm:text-sm transition-colors cursor-pointer py-1"
                              >
                                View Votes ({totalVotes})
                              </button>
                              <span className="text-[11px] text-slate-500 font-mono">
                                17:20
                              </span>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  ) : (
                    /* Active Question Card (Telegram Native Quiz Poll Style) */
                    <div className="bg-[#17212b] rounded-2xl p-4 sm:p-5 shadow-2xl text-white space-y-3.5 border border-[#242f3d] flex flex-col w-full max-w-xl">
                      {/* Top Bar: Quiz Bot & Admin + Countdown Timer */}
                      <div className="flex items-center justify-between pb-1 border-b border-slate-700/60">
                        <div className="flex items-center gap-2">
                          <span className="text-[#38bdf8] text-xs font-bold tracking-wide">
                            Quiz Bot
                          </span>
                          <span className="bg-[#1b382b] text-[#4ade80] border border-[#23583c] px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide">
                            Aдмин
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-16 sm:w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-rose-500 transition-all duration-1000 rounded-full"
                              style={{
                                width: `${((activeSession?.timerSeconds ?? 15) / 15) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-rose-400 font-bold text-xs font-mono min-w-[24px] text-right">
                            {activeSession?.timerSeconds ?? 15}s
                          </span>
                        </div>
                      </div>

                      {/* Question Title & Tagline */}
                      <div className="space-y-1">
                        <h2 className="text-white text-base sm:text-[17px] font-bold leading-snug">
                          <span className="text-white font-mono font-bold mr-1.5">
                            [{msg.questionData.questionIndex}/{msg.questionData.totalQuestions}]
                          </span>
                          {msg.questionData.question.question}
                        </h2>
                        <div className="flex items-center justify-between text-xs">
                          <p className="text-rose-300/80 italic font-medium tracking-wide">
                            {msg.questionData.tagline || "!!🖤🌹B ⓐ dshah🌹🖤!!"}
                          </p>
                          <span className="text-slate-400 text-[11px]">
                            Anonymous Quiz
                          </span>
                        </div>
                      </div>

                      {/* Native Poll Radio Options */}
                      <div className="space-y-2 pt-1">
                        {msg.questionData.options.map((opt, idx) => {
                          const letters = ["A", "B", "C", "D"];
                          const isUserAnswer = msg.questionData!.userAnswer === opt;
                          return (
                            <button
                              key={idx}
                              disabled={activeSession?.userAnswered}
                              onClick={() => handleAnswerClick(msg.id, opt)}
                              className={`w-full p-3 rounded-xl flex items-center justify-between text-sm transition-all cursor-pointer group text-left ${
                                isUserAnswer
                                  ? "bg-sky-500/20 border border-sky-400 text-white shadow-sm"
                                  : "bg-[#212d3b] hover:bg-[#273545] border border-slate-700/60 text-slate-100"
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <span
                                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                                    isUserAnswer
                                      ? "border-sky-400 bg-sky-400"
                                      : "border-slate-500 group-hover:border-sky-400"
                                  }`}
                                >
                                  {isUserAnswer && (
                                    <span className="w-2 h-2 rounded-full bg-white" />
                                  )}
                                </span>
                                <span className="font-medium text-slate-100">
                                  {opt}
                                </span>
                              </div>
                              <span className="text-xs text-slate-400 font-mono">
                                {letters[idx]}
                              </span>
                            </button>
                          );
                        })}
                      </div>

                      {/* Inline Buttons [ A ] [ B ] [ C ] [ D ] */}
                      <div className="pt-2 border-t border-slate-700/60">
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {msg.questionData.options.map((opt, idx) => {
                            const letters = ["A", "B", "C", "D"];
                            const letter = letters[idx];
                            const isSelected = msg.questionData!.userAnswer === opt;
                            return (
                              <button
                                key={idx}
                                disabled={activeSession?.userAnswered}
                                onClick={() => handleAnswerClick(msg.id, opt)}
                                className={`py-2 px-3 rounded-xl font-bold text-xs transition-all border cursor-pointer ${
                                  isSelected
                                    ? "bg-sky-500 text-white border-sky-400 shadow-md"
                                    : "bg-[#212d3b] hover:bg-sky-500/20 text-slate-200 hover:text-white border-slate-700"
                                }`}
                              >
                                [ {letter} ]
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  )
                )}

                {/* 4. Result Message View Votes Action */}
                {msg.type === "result" && msg.resultData && (
                  <div className="mt-3 pt-2.5 border-t border-indigo-700/60">
                    <button
                      onClick={() =>
                        setVotesModalData({
                          show: true,
                          questionIndex: msg.resultData!.questionIndex,
                          totalQuestions: msg.resultData!.totalQuestions,
                          questionText: msg.resultData!.questionText,
                          tagline: msg.resultData!.tagline,
                          options: msg.resultData!.options,
                          correctAnswer: msg.resultData!.correctAnswer,
                          correctLetter: msg.resultData!.correctLetter,
                          optionVotes: msg.resultData!.optionVotes,
                          totalVotes: msg.resultData!.totalVotes,
                          voters: msg.resultData!.voters,
                        })
                      }
                      className="w-full py-2 px-3 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 hover:text-white border border-sky-400/40 text-xs font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-sm active:scale-[0.99]"
                    >
                      <Eye className="w-3.5 h-3.5 text-sky-400" />
                      View Votes ({msg.resultData.totalVotes})
                    </button>
                  </div>
                )}

                {/* 5. Pause Resume Card */}
                {msg.type === "pause" && (
                  <div className="mt-3 pt-3 border-t border-indigo-700/60">
                    <button
                      onClick={handleTogglePause}
                      className="w-full py-2.5 px-4 bg-emerald-500 hover:bg-emerald-400 text-indigo-950 rounded-xl text-xs font-black flex items-center justify-center gap-2 shadow-md transition-colors cursor-pointer uppercase"
                    >
                      <Play className="w-4 h-4" />
                      ▶️ Resume Quiz
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Telegram Chat Input Bar */}
        <div className="p-3 sm:p-4 bg-indigo-900 border-t border-indigo-700">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendCommand();
            }}
            className="flex items-center gap-2"
          >
            <div className="flex-1 relative">
              <input
                id="simulator-command-input"
                type="text"
                value={inputCommand}
                onChange={(e) => setInputCommand(e.target.value)}
                placeholder="Type /Choose or any Telegram command..."
                className="w-full bg-indigo-950 text-white placeholder-indigo-400/60 text-sm px-4 py-2.5 rounded-xl border border-indigo-700/80 focus:outline-hidden focus:border-amber-400 font-sans"
              />
            </div>

            <button
              type="submit"
              id="simulator-submit-btn"
              className="px-5 py-2.5 bg-amber-400 hover:bg-amber-300 text-indigo-950 rounded-xl font-black text-sm flex items-center gap-1.5 transition-colors cursor-pointer shadow-md shadow-amber-400/20 uppercase"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>

          {/* Quick command buttons pill bar */}
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-indigo-800/80 overflow-x-auto text-[11px]">
            <span className="text-indigo-400 font-bold uppercase tracking-wider shrink-0">Commands:</span>
            <button
              type="button"
              onClick={() => handleSendCommand("/Choose")}
              className="px-2.5 py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-800 text-amber-300 font-mono font-bold border border-indigo-800 shrink-0 cursor-pointer"
            >
              /Choose
            </button>
            <button
              type="button"
              onClick={() => handleSendCommand("/Stopgln")}
              className="px-2.5 py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-800 text-rose-300 font-mono font-bold border border-indigo-800 shrink-0 cursor-pointer"
            >
              /Stopgln
            </button>
            <button
              type="button"
              onClick={() => handleSendCommand("/leaderboard")}
              className="px-2.5 py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-800 text-emerald-300 font-mono font-bold border border-indigo-800 shrink-0 cursor-pointer"
            >
              /leaderboard
            </button>
            <button
              type="button"
              onClick={() => handleSendCommand(`/Approvegln ${groupId}`)}
              className="px-2.5 py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-800 text-purple-300 font-mono font-bold border border-indigo-800 shrink-0 cursor-pointer"
            >
              /Approvegln {groupId}
            </button>
            <button
              type="button"
              onClick={() => handleSendCommand("/broadcast 🚀 New update is available!")}
              className="px-2.5 py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-800 text-sky-300 font-mono font-bold border border-indigo-800 shrink-0 cursor-pointer"
            >
              /broadcast
            </button>
          </div>
        </div>
      </div>

      {/* Simulated View Votes Bottom Sheet (Matching Telegram Quiz Bot Image 4) */}
      {votesModalData && votesModalData.show && (
        <div
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-end sm:items-center justify-center p-0 sm:p-4 animate-in fade-in duration-200"
          onClick={() => setVotesModalData(null)}
        >
          <div
            className="bg-[#17212b] text-white w-full max-w-lg rounded-t-3xl sm:rounded-3xl border border-[#2b394a] shadow-2xl overflow-hidden max-h-[85vh] flex flex-col animate-in slide-in-from-bottom-5 duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Native Top Drag Handle */}
            <div className="pt-2.5 pb-1 flex justify-center">
              <div className="w-10 h-1 bg-slate-600/80 rounded-full" />
            </div>

            {/* Question Title Header */}
            <div className="px-5 pt-2 pb-3 border-b border-[#242f3d]/70">
              <h3 className="text-base sm:text-[17px] font-bold text-white leading-snug">
                <span className="text-white font-mono font-bold mr-1.5">
                  [{votesModalData.questionIndex}/{votesModalData.totalQuestions}]
                </span>
                {votesModalData.questionText}
              </h3>
            </div>

            {/* Options & Voters Breakdown List */}
            <div className="flex-1 overflow-y-auto divide-y divide-[#242f3d]/60 bg-[#17212b]">
              {votesModalData.options.map((opt, idx) => {
                const count = votesModalData.optionVotes[opt] || 0;
                const pct =
                  votesModalData.totalVotes > 0
                    ? Math.round((count / votesModalData.totalVotes) * 100)
                    : 0;
                const voters = votesModalData.voters[opt] || [];

                return (
                  <div key={idx} className="py-3 px-5 space-y-2.5">
                    {/* Option Title and Count */}
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-semibold text-slate-300">
                        {opt} – {pct}%
                      </span>
                      <span className="text-xs text-slate-400 font-mono">
                        {count} {count === 1 ? "answer" : "answers"}
                      </span>
                    </div>

                    {/* Voters List matching Image 4 */}
                    {voters.length > 0 ? (
                      <div className="space-y-2.5 pt-0.5">
                        {voters.map((voter, vIdx) => (
                          <div
                            key={vIdx}
                            className="flex items-center justify-between py-1"
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className={`w-10 h-10 rounded-full ${
                                  voter.avatarColor || "bg-indigo-500"
                                } text-white font-bold text-sm flex items-center justify-center shrink-0 ring-1 ring-[#242f3d] shadow-sm`}
                              >
                                {voter.name.charAt(0).toUpperCase()}
                              </div>
                              <span className="text-sm font-bold text-white truncate max-w-[200px] sm:max-w-[280px]">
                                {voter.name}
                              </span>
                            </div>
                            <span className="text-xs text-slate-400 font-mono shrink-0">
                              today {voter.time ? voter.time.replace("today ", "") : "17:20"}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic py-1">
                        No votes for this option
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Simulated Telegram Private Callback Alert (show_alert=True) */}
      {privateAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/80 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-indigo-900 border-2 border-indigo-700 text-white rounded-3xl max-w-sm w-full p-6 text-center shadow-2xl space-y-4">
            <div className="flex justify-center">
              {privateAlert.isSuccess ? (
                <div className="w-14 h-14 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-3xl">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                </div>
              ) : (
                <div className="w-14 h-14 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center text-3xl">
                  <XCircle className="w-8 h-8 text-rose-400" />
                </div>
              )}
            </div>

            <div className="space-y-1">
              <h3 className="text-xs uppercase tracking-wider text-amber-400 font-bold">
                {privateAlert.title}
              </h3>
              <p className="text-xl font-black whitespace-pre-line text-white">
                {privateAlert.message}
              </p>
            </div>

            <p className="text-xs text-indigo-300">
              This response is visible <b>only to you</b> in Telegram via private callback alert. Other group members cannot see your answer before timeout.
            </p>

            <button
              id="close-private-alert"
              onClick={() => setPrivateAlert(null)}
              className="w-full py-2.5 bg-amber-400 hover:bg-amber-300 text-indigo-950 rounded-xl text-sm font-black transition-colors cursor-pointer uppercase shadow-md"
            >
              OK (Dismiss)
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
