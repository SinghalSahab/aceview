"""
Interview Session Service

Handles creation, persistence, and state management for mock interview sessions.
"""

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.orm import Session
from db.models import InterviewSession


def create_interview_session(db: Session, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Creates and persists a new mock interview session."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return {"error": "Invalid user ID format", "status_code": 400}

    resume_id_str = payload.get("resume_id")
    resume_uuid = None
    if resume_id_str:
        try:
            resume_uuid = uuid.UUID(resume_id_str)
        except ValueError:
            pass

    session_id = uuid.uuid4()
    session = InterviewSession(
        id=session_id,
        user_id=user_uuid,
        resume_id=resume_uuid,
        current_difficulty=int(payload.get("difficulty", 2)),
        status="in_progress",
        target_job_description=payload.get("target_role", "Software Engineer"),
    )

    try:
        db.add(session)
        db.commit()
        return {
            "session_id": str(session_id),
            "status": "in_progress",
            "message": "Interview session created successfully",
            "config": payload,
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e), "status_code": 500}


def handle_create_interview_session(user_id: str, payload: dict[str, Any]):
    """Abstract controller function for creating an interview session."""
    from fastapi.responses import JSONResponse
    from db.db import SessionLocal

    db = SessionLocal()
    try:
        result = create_interview_session(db=db, user_id=user_id, payload=payload)
        status_code = result.pop("status_code", 200) if "status_code" in result else 200
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=result)
        return result
    finally:
        db.close()

