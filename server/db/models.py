import uuid
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from .db import Base



class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    linkedin: Mapped[Optional[str]] = mapped_column(Text)
    github_username: Mapped[Optional[str]] = mapped_column(Text)
    years_of_experience: Mapped[Optional[float]] = mapped_column(Numeric)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="profile", cascade="all, delete-orphan")
    github_repos: Mapped[List["GitHubRepository"]] = relationship("GitHubRepository", back_populates="profile", cascade="all, delete-orphan")
    rag_documents: Mapped[List["RAGDocument"]] = relationship("RAGDocument", back_populates="profile", cascade="all, delete-orphan")
    interview_sessions: Mapped[List["InterviewSession"]] = relationship("InterviewSession", back_populates="profile", cascade="all, delete-orphan")
    ats_reports: Mapped[List["ATSReport"]] = relationship("ATSReport", back_populates="profile", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    experience: Mapped[list] = mapped_column(JSONB, default=list)
    education: Mapped[list] = mapped_column(JSONB, default=list)
    projects: Mapped[list] = mapped_column(JSONB, default=list)
    years_of_experience: Mapped[Optional[float]] = mapped_column(Numeric)
    
    file_name: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["Profile"] = relationship("Profile", back_populates="resumes")


class GitHubRepository(Base):
    __tablename__ = "github_repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    
    github_repo_id: Mapped[Optional[int]] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    
    languages: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    architecture_score: Mapped[Optional[float]] = mapped_column(Numeric)
    testing_score: Mapped[Optional[float]] = mapped_column(Numeric)
    complexity_score: Mapped[Optional[float]] = mapped_column(Numeric)
    documentation_score: Mapped[Optional[float]] = mapped_column(Numeric)
    commit_score: Mapped[Optional[float]] = mapped_column(Numeric)
    overall_code_score: Mapped[Optional[float]] = mapped_column(Numeric)
    
    readme_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    profile: Mapped["Profile"] = relationship("Profile", back_populates="github_repos")


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    chunk_id: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["Profile"] = relationship("Profile", back_populates="rag_documents")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    
    current_difficulty: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    memory_summary: Mapped[Optional[str]] = mapped_column(Text)
    covered_topics: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    profile: Mapped["Profile"] = relationship("Profile", back_populates="interview_sessions")
    questions: Mapped[List["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(Text)
    difficulty: Mapped[Optional[int]] = mapped_column(Integer)
    source_repo: Mapped[Optional[str]] = mapped_column(Text)
    skill_ref: Mapped[Optional[str]] = mapped_column(Text)
    expected_key_points: Mapped[list] = mapped_column(JSONB, default=list)
    rubric_id: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="questions")
    answers: Mapped[List["Answer"]] = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False)
    
    transcript: Mapped[Optional[str]] = mapped_column(Text)
    audio_path: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped["InterviewQuestion"] = relationship("InterviewQuestion", back_populates="answers")
    evaluation: Mapped[Optional["Evaluation"]] = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("answers.id", ondelete="CASCADE"), nullable=False)
    
    rubric_score: Mapped[Optional[float]] = mapped_column(Numeric)
    keyword_score: Mapped[Optional[float]] = mapped_column(Numeric)
    embedding_score: Mapped[Optional[float]] = mapped_column(Numeric)
    reasoning_score: Mapped[Optional[float]] = mapped_column(Numeric)
    final_score: Mapped[Optional[float]] = mapped_column(Numeric)
    
    breakdown_explanation: Mapped[Optional[dict]] = mapped_column(JSONB)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answer: Mapped["Answer"] = relationship("Answer", back_populates="evaluation")


class ATSReport(Base):
    __tablename__ = "ats_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    
    job_description: Mapped[Optional[str]] = mapped_column(Text)
    keyword_match: Mapped[Optional[float]] = mapped_column(Numeric)
    formatting_score: Mapped[Optional[float]] = mapped_column(Numeric)
    completeness_score: Mapped[Optional[float]] = mapped_column(Numeric)
    readability_score: Mapped[Optional[float]] = mapped_column(Numeric)
    overall_score: Mapped[Optional[float]] = mapped_column(Numeric)
    
    suggestions: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["Profile"] = relationship("Profile", back_populates="ats_reports")