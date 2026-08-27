import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
if "HUGGING_FACE_TOKEN" in os.environ:
    os.environ["HF_TOKEN"] = os.environ["HUGGING_FACE_TOKEN"]

import pprint
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from db.db import SessionLocal
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