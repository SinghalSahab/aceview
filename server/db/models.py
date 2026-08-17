import uuid
import datetime
import decimal
from typing import Any, Optional, List

from pgvector.sqlalchemy.vector import VECTOR
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


from .db import Base



class Profile(Base):
    __tablename__ = 'profiles'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='profiles_pkey'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    # Relationships
    github_repositories: Mapped[List['GithubRepository']] = relationship('GithubRepository', back_populates='user', cascade='all, delete-orphan')
    resumes: Mapped[List['Resume']] = relationship('Resume', back_populates='user', cascade='all, delete-orphan')
    ats_reports: Mapped[List['AtsReport']] = relationship('AtsReport', back_populates='user', cascade='all, delete-orphan')
    interview_sessions: Mapped[List['InterviewSession']] = relationship('InterviewSession', back_populates='user', cascade='all, delete-orphan')
    rag_documents: Mapped[List['RagDocument']] = relationship('RagDocument', back_populates='user', cascade='all, delete-orphan')


class Rubric(Base):
    __tablename__ = 'rubrics'
    __table_args__ = (
        CheckConstraint("competency_type = ANY (ARRAY['technical-depth'::text, 'problem-solving'::text, 'communication'::text, 'behavioral'::text])", name='rubrics_competency_type_check'),
        PrimaryKeyConstraint('id', name='rubrics_pkey'),
        UniqueConstraint('competency_type', name='rubrics_competency_type_key'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    competency_type: Mapped[str] = mapped_column(Text, nullable=False)
    criteria: Mapped[Any] = mapped_column(JSONB, nullable=False)
    total_max: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('100'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    interview_questions: Mapped[List['InterviewQuestion']] = relationship('InterviewQuestion', back_populates='rubric')


class GithubRepository(Base):
    __tablename__ = 'github_repositories'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['public.profiles.id'], ondelete='CASCADE', name='github_repositories_user_id_fkey'),
        PrimaryKeyConstraint('id', name='github_repositories_pkey'),
        Index('idx_github_repos_profile_id', 'user_id'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    is_fork: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    github_repo_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    languages: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    architecture_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    testing_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    complexity_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    documentation_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    commit_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    overall_code_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    readme_text: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped['Profile'] = relationship('Profile', back_populates='github_repositories')
    rag_documents: Mapped[List['RagDocument']] = relationship('RagDocument', back_populates='repo')
    interview_questions: Mapped[List['InterviewQuestion']] = relationship('InterviewQuestion', back_populates='source_repo')


class Resume(Base):
    __tablename__ = 'resumes'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['public.profiles.id'], ondelete='CASCADE', name='resumes_user_id_fkey'),
        PrimaryKeyConstraint('id', name='resumes_pkey'),
        Index('idx_resumes_profile_id', 'user_id'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    experience: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    education: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    projects: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    years_of_experience: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    file_name: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text)
    github_username: Mapped[Optional[str]] = mapped_column(Text)
    sections: Mapped[Optional[Any]] = mapped_column(JSONB)
    links: Mapped[Optional[Any]] = mapped_column(JSONB)

    user: Mapped['Profile'] = relationship('Profile', back_populates='resumes')
    ats_reports: Mapped[List['AtsReport']] = relationship('AtsReport', back_populates='resume')
    interview_sessions: Mapped[List['InterviewSession']] = relationship('InterviewSession', back_populates='resume')


class AtsReport(Base):
    __tablename__ = 'ats_reports'
    __table_args__ = (
        ForeignKeyConstraint(['resume_id'], ['public.resumes.id'], ondelete='CASCADE', name='ats_reports_resume_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['public.profiles.id'], ondelete='CASCADE', name='ats_reports_user_id_fkey'),
        PrimaryKeyConstraint('id', name='ats_reports_pkey'),
        Index('idx_ats_reports_profile_id', 'user_id'),
        Index('idx_ats_reports_resume_id', 'resume_id'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    job_description: Mapped[Optional[str]] = mapped_column(Text)
    keyword_match: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    formatting_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    completeness_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    readability_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    overall_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    suggestions: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)

    resume: Mapped[Optional['Resume']] = relationship('Resume', back_populates='ats_reports')
    user: Mapped['Profile'] = relationship('Profile', back_populates='ats_reports')


class InterviewSession(Base):
    __tablename__ = 'interview_sessions'
    __table_args__ = (
        CheckConstraint("status = ANY (ARRAY['in_progress'::text, 'completed'::text, 'abandoned'::text])", name='interview_sessions_status_check'),
        ForeignKeyConstraint(['resume_id'], ['public.resumes.id'], ondelete='SET NULL', name='interview_sessions_resume_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['public.profiles.id'], ondelete='CASCADE', name='interview_sessions_user_id_fkey'),
        PrimaryKeyConstraint('id', name='interview_sessions_pkey'),
        Index('idx_interview_sessions_profile_id', 'user_id'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    current_difficulty: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('2'))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'in_progress'::text"))
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    memory_summary: Mapped[Optional[str]] = mapped_column(Text)
    covered_topics: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    target_job_description: Mapped[Optional[str]] = mapped_column(Text)
    rolling_avg_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2))

    resume: Mapped[Optional['Resume']] = relationship('Resume', back_populates='interview_sessions')
    user: Mapped['Profile'] = relationship('Profile', back_populates='interview_sessions')
    interview_questions: Mapped[List['InterviewQuestion']] = relationship('InterviewQuestion', back_populates='session', cascade='all, delete-orphan')
    session_scores: Mapped[Optional['SessionScore']] = relationship('SessionScore', uselist=False, back_populates='session', cascade='all, delete-orphan')


class RagDocument(Base):
    __tablename__ = 'rag_documents'
    __table_args__ = (
        ForeignKeyConstraint(['repo_id'], ['public.github_repositories.id'], ondelete='SET NULL', name='rag_documents_repo_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['public.profiles.id'], ondelete='CASCADE', name='rag_documents_user_id_fkey'),
        PrimaryKeyConstraint('id', name='rag_documents_pkey'),
        UniqueConstraint('user_id', 'chunk_id', name='unique_profile_chunk'),
        Index('idx_rag_documents_profile_id', 'user_id'),
        Index('idx_rag_documents_repo_id', 'repo_id', postgresql_where='(repo_id IS NOT NULL)'),
        Index('idx_rag_documents_user_source', 'user_id', 'source_type'),
        Index('rag_documents_embedding_idx', 'embedding', postgresql_ops={'embedding': 'vector_cosine_ops'}, postgresql_using='hnsw'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_id: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    metadata_: Mapped[Optional[Any]] = mapped_column('metadata', JSONB, server_default=text("'{}'::jsonb"))
    embedding: Mapped[Optional[Any]] = mapped_column(VECTOR(384))
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    repo_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    token_count: Mapped[Optional[int]] = mapped_column(Integer)

    repo: Mapped[Optional['GithubRepository']] = relationship('GithubRepository', back_populates='rag_documents')
    user: Mapped['Profile'] = relationship('Profile', back_populates='rag_documents')


class InterviewQuestion(Base):
    __tablename__ = 'interview_questions'
    __table_args__ = (
        CheckConstraint('difficulty >= 1 AND difficulty <= 5', name='interview_questions_difficulty_check'),
        ForeignKeyConstraint(['parent_question_id'], ['public.interview_questions.id'], ondelete='CASCADE', name='interview_questions_parent_question_id_fkey'),
        ForeignKeyConstraint(['rubric_id'], ['public.rubrics.id'], ondelete='SET NULL', name='fk_interview_questions_rubrics'),
        ForeignKeyConstraint(['session_id'], ['public.interview_sessions.id'], ondelete='CASCADE', name='interview_questions_session_id_fkey'),
        ForeignKeyConstraint(['source_repo_id'], ['public.github_repositories.id'], ondelete='SET NULL', name='interview_questions_source_repo_id_fkey'),
        PrimaryKeyConstraint('id', name='interview_questions_pkey'),
        Index('idx_interview_questions_parent', 'parent_question_id', postgresql_where='(parent_question_id IS NOT NULL)'),
        Index('idx_interview_questions_session', 'session_id'),
        Index('idx_interview_questions_session_id', 'session_id'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_: Mapped[str] = mapped_column('text', Text, nullable=False)
    asked_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    is_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    topic: Mapped[Optional[str]] = mapped_column(Text)
    difficulty: Mapped[Optional[int]] = mapped_column(Integer)
    sourceRepoOrSkill: Mapped[Optional[str]] = mapped_column(Text)
    skill_ref: Mapped[Optional[str]] = mapped_column(Text)
    expected_key_points: Mapped[Optional[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    rubric_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    parent_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    source_repo_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    source_skill: Mapped[Optional[str]] = mapped_column(Text)

    parent_question: Mapped[Optional['InterviewQuestion']] = relationship('InterviewQuestion', remote_side=[id], back_populates='followups')
    followups: Mapped[List['InterviewQuestion']] = relationship('InterviewQuestion', back_populates='parent_question')
    rubric: Mapped[Optional['Rubric']] = relationship('Rubric', back_populates='interview_questions')
    session: Mapped['InterviewSession'] = relationship('InterviewSession', back_populates='interview_questions')
    source_repo: Mapped[Optional['GithubRepository']] = relationship('GithubRepository', back_populates='interview_questions')
    answers: Mapped[List['Answer']] = relationship('Answer', back_populates='question', cascade='all, delete-orphan')


class SessionScore(Base):
    __tablename__ = 'session_scores'
    __table_args__ = (
        CheckConstraint("hiring_recommendation = ANY (ARRAY['Strong Hire signal'::text, 'Mixed, proceed with caution'::text, 'Not ready yet'::text])", name='session_scores_hiring_recommendation_check'),
        ForeignKeyConstraint(['session_id'], ['public.interview_sessions.id'], ondelete='CASCADE', name='session_scores_session_id_fkey'),
        PrimaryKeyConstraint('id', name='session_scores_pkey'),
        UniqueConstraint('session_id', name='session_scores_session_id_key'),
        Index('idx_session_scores_final_score', 'avg_final_score'),
        Index('idx_session_scores_session_id', 'session_id'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    technical_depth_score: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    problem_solving_score: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    communication_score: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    confidence_score: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    avg_final_score: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    hiring_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    weaknesses: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    code_quality_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2))

    session: Mapped['InterviewSession'] = relationship('InterviewSession', back_populates='session_scores')


class Answer(Base):
    __tablename__ = 'answers'
    __table_args__ = (
        ForeignKeyConstraint(['question_id'], ['public.interview_questions.id'], ondelete='CASCADE', name='answers_question_id_fkey'),
        PrimaryKeyConstraint('id', name='answers_pkey'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    answered_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    transcript: Mapped[Optional[str]] = mapped_column(Text)
    audio_path: Mapped[Optional[str]] = mapped_column(Text)

    question: Mapped['InterviewQuestion'] = relationship('InterviewQuestion', back_populates='answers')
    evaluations: Mapped[List['Evaluation']] = relationship('Evaluation', back_populates='answer', cascade='all, delete-orphan')


class Evaluation(Base):
    __tablename__ = 'evaluations'
    __table_args__ = (
        ForeignKeyConstraint(['answer_id'], ['public.answers.id'], ondelete='CASCADE', name='evaluations_answer_id_fkey'),
        PrimaryKeyConstraint('id', name='evaluations_pkey'),
        {'schema': 'public'},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    answer_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    rubric_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    keyword_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    embedding_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    reasoning_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    final_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric)
    breakdown_explanation: Mapped[Optional[Any]] = mapped_column(JSONB)
    flagged_for_review: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text('false'))

    answer: Mapped['Answer'] = relationship('Answer', back_populates='evaluations')