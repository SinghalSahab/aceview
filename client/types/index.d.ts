interface Feedback {
  id: string;
  interviewId: string;
  totalScore: number;
  categoryScores: Array<{
    name: string;
    score: number;
    comment: string;
  }>;
  strengths: string[];
  areasForImprovement: string[];
  finalAssessment: string;
  createdAt: string;
}

interface Interview {
  id: string;
  role: string;
  level: string;
  questions: string[];
  techstack: string[];
  createdAt: string;
  userId: string;
  type: string;
  finalized: boolean;
}

interface CreateFeedbackParams {
  interviewId: string;
  userId: string;
  transcript: { role: string; content: string }[];
  feedbackId?: string;
}

interface User {
  name: string;
  email: string;
  id: string;
}

interface InterviewCardProps {
  interviewId?: string;
  userId?: string;
  role: string;
  type: string;
  techstack: string[];
  createdAt?: string;
}

interface AgentProps {
  userName: string;
  userId?: string;
  interviewId?: string;
  feedbackId?: string;
  type: "generate" | "interview";
  questions?: string[];
}

interface RouteParams {
  params: Promise<Record<string, string>>;
  searchParams: Promise<Record<string, string>>;
}

interface GetFeedbackByInterviewIdParams {
  interviewId: string;
  userId: string;
}

interface GetLatestInterviewsParams {
  userId: string;
  limit?: number;
}

interface SignInParams {
  email: string;
  idToken: string;
}

interface SignUpParams {
  uid: string;
  name: string;
  email: string;
  password: string;
}

type FormType = "sign-in" | "sign-up";

interface InterviewFormProps {
  interviewId: string;
  role: string;
  level: string;
  type: string;
  techstack: string[];
  amount: number;
}

interface TechIconProps {
  techStack: string[];
}

// This is your Prisma schema file,
// learn more about it in the docs: https://pris.ly/d/prisma-schema

// Looking for ways to speed up your queries, or scale easily with your serverless or edge functions?
// Try Prisma Accelerate: https://pris.ly/cli/accelerate-init

generator client {
  provider = "prisma-client-js"
  output = "../lib/generated/prisma"
}

datasource db {
  provider = "mongodb"
  url = env("DATABASE_URL")
}



enum Speaker {
  INTERVIEWER
  CANDIDATE
}

model Candidate {
  id        String @id @default (uuid())
  name      String
  email     String @unique
  phone     String ?
    linkedin  String ?

      createdAt DateTime @default (now())
  updatedAt DateTime @updatedAt

  resume    Resume ?
    github    GithubProfile ?
      sessions  InterviewSession[]
}

model Resume {
  id                  String @id @default (uuid())
  rawText             String @db.Text
  yearsOfExperience   Float

  candidateId         String @unique
  candidate           Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)

  skills              ResumeSkill[]
  experiences         Experience[]
  educations          Education[]
}

model ResumeSkill {
  id        String @id @default (uuid())
  name      String

  resumeId  String
  resume    Resume @relation(fields: [resumeId], references: [id], onDelete: Cascade)
}

model Experience {
  id          String @id @default (uuid())

  company     String
  role        String

  startDate   DateTime ?
    endDate     DateTime ?

      description String @db.Text

  resumeId    String
  resume      Resume @relation(fields: [resumeId], references: [id], onDelete: Cascade)
}

model Education {
  id            String @id @default (uuid())

  institution   String
  degree        String

  startYear     Int ?
    endYear       Int ?

      resumeId      String
  resume        Resume @relation(fields: [resumeId], references: [id], onDelete: Cascade)
}

model GithubProfile {
  id              String @id @default (uuid())

  username        String @unique

  aggregateScore  Float ?

    candidateId     String @unique
  candidate        Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)

  repos           GithubRepo[]
}

model GithubRepo {
  id                  String @id @default (uuid())

  name                String
  description         String ?
    readmeText          String ? @db.Text

  languages           Json

  architectureScore   Float
  testingScore        Float
  complexityScore     Float
  documentationScore  Float
  commitScore         Float
  overallCodeScore    Float

  githubProfileId     String
  githubProfile       GithubProfile @relation(fields: [githubProfileId], references: [id], onDelete: Cascade)
}

model InterviewSession {
  id                  String @id @default (uuid())

  memorySummary       String ? @db.Text
  currentDifficulty   Int @default (2)

  createdAt           DateTime @default (now())
  updatedAt           DateTime @updatedAt

  candidateId         String
  candidate           Candidate @relation(fields: [candidateId], references: [id], onDelete: Cascade)

  transcripts         Transcript[]
  evaluations         Evaluation[]
}

model Transcript {
  id          String @id @default (uuid())

  speaker     Speaker

  text        String @db.Text

  createdAt   DateTime @default (now())

  sessionId   String
  session     InterviewSession @relation(fields: [sessionId], references: [id], onDelete: Cascade)
}

model Rubric {
  id          String @id @default (uuid())

  name        String
  description String ?

    criteria    Json

  questions   Question[]
}

model Question {
  id                  String @id @default (uuid())

  text                String @db.Text

  topic               String

  difficulty          Int

  sourceRepo          String ?
    skillRef            String ?

      expectedKeyPoints   Json

  rubricId            String
  rubric              Rubric @relation(fields: [rubricId], references: [id])

  evaluations         Evaluation[]
}

model Evaluation {
  id                      String @id @default (uuid())

  rubricScore             Float
  keywordScore            Float
  embeddingScore          Float
  reasoningScore          Float
  finalScore              Float

  breakdownExplanation    String @db.Text

  flaggedForReview        Boolean @default (false)

  createdAt               DateTime @default (now())

  questionId              String
  question                Question @relation(fields: [questionId], references: [id])

  sessionId               String
  session                 InterviewSession @relation(fields: [sessionId], references: [id], onDelete: Cascade)
}