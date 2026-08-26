export interface ResumeItem {
  id: string;
  user_id?: string;
  file_name: string;
  file_path?: string;
  target_role?: string;
  summary?: string;
  skills: string[];
  years_of_experience?: number;
  ats_score?: number; // e.g. 85 / 100
  created_at: string;
  github_username?: string;
  projects?: Array<{
    title?: string;
    description?: string;
    skills?: string[];
    url?: string;
  }>;
  sections?: Record<string, string>;
  raw_text?: string;
}

export type InterviewType = "technical" | "behavioral" | "mixed";

export type DifficultyLevel = 1 | 2 | 3 | 4;

export interface InterviewConfig {
  resume_id: string;
  target_role: string;
  interview_type: InterviewType;
  difficulty: DifficultyLevel;
  focus_areas: string[];
  duration: 15 | 30 | 45;
}

export interface InterviewSessionPayload extends InterviewConfig {}

export interface InterviewSessionResponse {
  session_id: string;
  message?: string;
  status: "in_progress" | "initialized";
  config?: InterviewConfig;
  started_at?: string;
}
