    const handleSelectOptionsCount = (subject: Subject, count: number) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // Prepare questions pool for this subject
    const filtered = INITIAL_QUESTIONS.filter((q) => q.subject === subject);
    const sourcePool = filtered.length > 0 ? filtered : INITIAL_QUESTIONS;

    // Expand questions to simulate 100-question session. Ensure we never get stuck on an empty pool.
    const pool: Question[] = [];
    const safeSource = [...sourcePool];
    while (pool.length < 100) {
      if (safeSource.length === 0) break;
      pool.push(...safeSource.sort(() => Math.random() - 0.5));
      if (pool.length > 200) break;
    }
    const readyQuestions = pool.slice(0, 100);

    if (readyQuestions.length === 0) {
      setMessages((prev) => [
        ...prev,
        {
          id: `b_error_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: timeStr,
          text: `⚠️ <b>Question pool unavailable for <i>${subject}</i>.</b>\n\nPlease reset the quiz or choose another subject.`,
          type: "error",
        },
      ]);
      return;
    }

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
      if (readyQuestions.length > 0) {
        startQuestionIndex(1, subject, count, readyQuestions);
      }
    }, 1200);
  };

  // Helper to construct randomized question
  const startQuestionIndex = (
    index: number,
    subject: Subject,
    optionsCount: number,
    pool: Question[]
  ) => {
    if (!pool || pool.length === 0) {
      setMessages((prev) => [
        ...prev,
        {
          id: `b_noq_${Date.now()}`,
          sender: "bot",
          senderName: "GLN Quiz Bot",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          text: "⚠️ <b>Quiz could not start because the question pool is empty.</b>",
          type: "error",
        },
      ]);
      return;
    }

    const qRaw = pool[index - 1] || pool[0];
