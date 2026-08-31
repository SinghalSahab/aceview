import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
if "HUGGING_FACE_TOKEN" in os.environ:
    os.environ["HF_TOKEN"] = os.environ["HUGGING_FACE_TOKEN"]

from fastapi import FastAPI, File, UploadFile, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from db.db import SessionLocal
from auth.middleware import require_auth
from skills.resumeService import (
    handle_resume_upload,
    handle_get_resumes,
    handle_delete_resume,
)
from skills.interviewService import handle_create_interview_session
from github.githubProfile import handle_analyze_github_user

app = FastAPI(
    title="AceView Server",
    description="Python FastAPI backend server for AceView handling PDF parsing, RAG embeddings, and AI interview services.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/home")
def return_home():
    return {
        "message": "Server is working fine!",
        "status": "OK"
    }


@app.get("/health/db")
def database_health():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "database": "connected",
            "result": result
        }
    finally:
        db.close()


@app.get("/api/github/analyze/{username}")
def analyze_github_user(
    username: str,
    user_id: str = Depends(require_auth),
):
    return handle_analyze_github_user(username=username, user_id=user_id)


@app.get("/api/resumes")
def fetch_resumes(user_id: str = Depends(require_auth)):
    return handle_get_resumes(user_id=user_id)


@app.delete("/api/resumes")
def delete_resume_by_query(
    id: Optional[str] = Query(None),
    user_id: str = Depends(require_auth),
):
    return handle_delete_resume(user_id=user_id, resume_id=id)


@app.delete("/api/resumes/{resume_id}")
def delete_resume_by_path(
    resume_id: str,
    user_id: str = Depends(require_auth),
):
    return handle_delete_resume(user_id=user_id, resume_id=resume_id)


@app.post("/api/interviews/session")
def start_interview_session(
    payload: dict = Body(...),
    user_id: str = Depends(require_auth),
):
    return handle_create_interview_session(user_id=user_id, payload=payload)


@app.post("/api/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth),
):
    return await handle_resume_upload(file=file, user_id=user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)