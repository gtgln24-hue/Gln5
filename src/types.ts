export type Subject =
  | "Hindi"
  | "Samajik Vigyan"
  | "Itihas"
  | "Science"
  | "Botany"
  | "Zoology"
  | "Mathematics"
  | "Chemistry";

export interface Question {
  id: string;
  subject: Subject;
  question: string;
  options: string[];
  correct_answer: string;
  exam_name?: string;
  exam_year?: number;
  topic?: string;
  source_reference?: string;
}

export interface VoterInfo {
  name: string;
  avatarColor?: string;
  time: string;
}

export interface QuizMessage {
  id: string;
  sender: "bot" | "admin" | "member" | "system";
  senderName: string;
  senderUsername?: string;
  timestamp: string;
  text: string;
  type?: "text" | "subject_selection" | "options_selection" | "question" | "result" | "pause" | "leaderboard" | "error" | "broadcast_preview";
  broadcastMessage?: string;
  questionData?: {
    questionIndex: number;
    totalQuestions: number;
    subject: Subject;
    question: Question;
    options: string[];
    correctLetter: string;
    correctAnswer: string;
    secondsRemaining: number;
    isLocked: boolean;
    userAnswer?: string;
    optionVotes: Record<string, number>;
    tagline?: string;
    voters?: Record<string, VoterInfo[]>;
  };
  resultData?: {
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
  };
  pauseSessionId?: string;
}

export interface UserStats {
  userId: number;
  username: string;
  name: string;
  correct: number;
  wrong: number;
  points: number;
  accuracy: number;
}

export interface SubjectCooldownInfo {
  subject: Subject;
  expiryTimestamp: number;
  remainingSeconds: number;
}
