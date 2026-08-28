import os
import tempfile
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
if "HUGGING_FACE_TOKEN" in os.environ:
    os.environ["HF_TOKEN"] = os.environ["HUGGING_FACE_TOKEN"]

from fastapi import FastAPI, File, UploadFile, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from db.db import SessionLocal
from auth.middleware import require_auth
from skills.resumeService import (
    ingest_and_save_resume,
    get_user_resumes,
    delete_user_resume,
)
from skills.interviewService import create_interview_session

try:
    from github.githubProfile import build_candidate_github_profile
except ImportError:
    try:
        from githubProfile import build_candidate_github_profile
    except ImportError:
        build_candidate_github_profile = None

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
    print(f"[Auth] GitHub analysis requested by user_id: {user_id}")
    if not build_candidate_github_profile:
        return JSONResponse(status_code=500, content={"error": "GitHub profile analysis module not loaded."})
    try:
        profile = build_candidate_github_profile(username=username, resume_project_links=[], n=5)
        return profile
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "username": username})


@app.get("/api/resumes")
def fetch_resumes(user_id: str = Depends(require_auth)):
    db = SessionLocal()
    try:
        result = get_user_resumes(db=db, user_id=user_id)
        status_code = result.pop("status_code", 200) if "status_code" in result else 200
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=result)
        return result
    finally:
        db.close()


@app.delete("/api/resumes")
def delete_resume_by_query(
    id: Optional[str] = Query(None),
    user_id: str = Depends(require_auth),
):
    if not id:
        return JSONResponse(status_code=400, content={"error": "Missing resume id parameter"})
    db = SessionLocal()
    try:
        result = delete_user_resume(db=db, user_id=user_id, resume_id=id)
        status_code = result.pop("status_code", 200) if "status_code" in result else 200
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=result)
        return result
    finally:
        db.close()


@app.delete("/api/resumes/{resume_id}")
def delete_resume_by_path(
    resume_id: str,
    user_id: str = Depends(require_auth),
):
    db = SessionLocal()
    try:
        result = delete_user_resume(db=db, user_id=user_id, resume_id=resume_id)
        status_code = result.pop("status_code", 200) if "status_code" in result else 200
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=result)
        return result
    finally:
        db.close()


@app.post("/api/interviews/session")
def start_interview_session(
    payload: dict = Body(...),
    user_id: str = Depends(require_auth),
):
    db = SessionLocal()
    try:
        result = create_interview_session(db=db, user_id=user_id, payload=payload)
        status_code = result.pop("status_code", 200) if "status_code" in result else 200
        if status_code != 200:
            return JSONResponse(status_code=status_code, content=result)
        return result
    finally:
        db.close()


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(require_auth),
):
    print(f"[Auth] Resume upload requested by user_id: {user_id}")
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "No selected file"})

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file_path = tmp.name
        contents = await file.read()
        tmp.write(contents)

    db = SessionLocal()
    try:
        result = ingest_and_save_resume(
            db=db,
            user_id=user_id,
            file_name=file.filename,
            file_path=file_path,
        )

        if result.get("status") == "failed":
            return JSONResponse(status_code=422, content=result)

        return result
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)