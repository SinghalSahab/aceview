import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
if "HUGGING_FACE_TOKEN" in os.environ:
    os.environ["HF_TOKEN"] = os.environ["HUGGING_FACE_TOKEN"]

import pprint
import uuid
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from db.db import SessionLocal
from db.models import Resume, AtsReport, InterviewSession, Profile
from auth.middleware import require_auth
from skills.resumeService import ingest_and_save_resume

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
def get_resumes(user_id: str = Depends(require_auth)):
    db = SessionLocal()
    try:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid user ID format"})

        resumes = (
            db.query(Resume)
            .filter(Resume.user_id == user_uuid)
            .order_by(Resume.created_at.desc())
            .all()
        )

        resumes_list = []
        for r in resumes:
            ats_report = (
                db.query(AtsReport)
                .filter(AtsReport.resume_id == r.id)
                .order_by(AtsReport.created_at.desc())
                .first()
            )
            latest_ats = ats_report.overall_score if ats_report else None

            if latest_ats is not None:
                ats_score = int(latest_ats)
            else:
                skills_count = len(r.skills) if isinstance(r.skills, list) else 0
                ats_score = min(98, 70 + skills_count * 2) if skills_count > 0 else 80

            target_role = "Software Engineer"
            if isinstance(r.sections, dict) and r.sections.get("target_role"):
                target_role = r.sections["target_role"]

            resumes_list.append({
                "id": str(r.id),
                "user_id": str(r.user_id),
                "file_name": r.file_name or "Resume.pdf",
                "file_path": r.file_path,
                "target_role": target_role,
                "summary": r.summary or "",
                "skills": r.skills if isinstance(r.skills, list) else [],
                "experience": r.experience if isinstance(r.experience, list) else [],
                "education": r.education if isinstance(r.education, list) else [],
                "projects": r.projects if isinstance(r.projects, list) else [],
                "years_of_experience": float(r.years_of_experience) if r.years_of_experience is not None else None,
                "ats_score": ats_score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "github_username": r.github_username,
                "sections": r.sections if isinstance(r.sections, dict) else {},
                "raw_text": r.raw_text or "",
            })

        return {"resumes": resumes_list}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


def _delete_resume(resume_id_str: str, user_id_str: str):
    db = SessionLocal()
    try:
        try:
            resume_uuid = uuid.UUID(resume_id_str)
            user_uuid = uuid.UUID(user_id_str)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid UUID format"})

        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_uuid, Resume.user_id == user_uuid)
            .first()
        )
        if not resume:
            return JSONResponse(status_code=404, content={"error": "Resume not found"})

        # Delete associated ATS reports
        db.query(AtsReport).filter(AtsReport.resume_id == resume_uuid).delete()
        db.delete(resume)
        db.commit()
        return {"status": "ok", "message": "Resume deleted successfully"}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.delete("/api/resumes")
def delete_resume_query(
    id: Optional[str] = Query(None),
    user_id: str = Depends(require_auth),
):
    if not id:
        return JSONResponse(status_code=400, content={"error": "Missing resume id parameter"})
    return _delete_resume(id, user_id)


@app.delete("/api/resumes/{resume_id}")
def delete_resume_path(
    resume_id: str,
    user_id: str = Depends(require_auth),
):
    return _delete_resume(resume_id, user_id)


@app.post("/api/interviews/session")
def create_interview_session(
    payload: dict = Body(...),
    user_id: str = Depends(require_auth),
):
    db = SessionLocal()
    try:
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid user ID format"})

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
        return JSONResponse(status_code=500, content={"error": str(e)})
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

    # Save uploaded file temporarily for extraction
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