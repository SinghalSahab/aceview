import os
import tempfile
from dotenv import load_dotenv

load_dotenv()
import pprint
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
import uuid
from sqlalchemy import text
from db.db import SessionLocal
from db.models import Profile, Resume, GithubRepository, AtsReport
from skills.skillExtractor import parse_resume

try:
    from rag.chunking import build_all_chunks
    from rag.embeddings import store_chunks
except ImportError:
    try:
        from chunking import build_all_chunks
        from embeddings import store_chunks
    except ImportError:
        build_all_chunks = None
        store_chunks = None

from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from auth.middleware import require_auth

app = FastAPI(
    title="AceView Server",
    description="Python FastAPI backend server for AceView handling PDF parsing and text extraction.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_page_layout(pdf_path):
    """
    Extract word-level text layout and hyperlink annotations per page.

    This exists because resume PDFs almost always embed URLs as invisible
    link annotations behind short visible anchor text (e.g. the word
    "GitHub" or "Live"), not as literal visible URL text — plain
    page.get_text() extraction cannot see these links at all, which is why
    link extraction was previously always empty. page.get_links() is the
    only way to retrieve them, and word-level bounding boxes are needed
    alongside them so skillExtractor can figure out (a) which visible word
    each link sits behind, and (b) which resume section/project the link
    belongs to, purely from vertical position on the page.

    y-coordinates are offset by a running total of previous pages' heights
    so positions stay monotonically increasing across a multi-page resume,
    which is what lets skillExtractor compare positions across pages with
    simple less-than/greater-than checks.
    """
    doc = fitz.open(pdf_path)
    pages = []
    y_offset = 0.0

    for page_index, page in enumerate(doc):
        words = page.get_text("words")  # (x0,y0,x1,y1,word,block_no,line_no,word_no)
        word_entries = [
            {
                "text": w[4],
                "x0": w[0], "x1": w[2],
                "y0": w[1] + y_offset, "y1": w[3] + y_offset,
                "block": w[5], "line": w[6], "word_no": w[7],
                "page": page_index,
            }
            for w in words
        ]

        link_entries = []
        for link in page.get_links():
            if link.get("kind") == fitz.LINK_URI and link.get("uri"):
                rect = link["from"]
                link_entries.append({
                    "uri": link["uri"],
                    "x0": rect.x0, "x1": rect.x1,
                    "y0": rect.y0 + y_offset, "y1": rect.y1 + y_offset,
                })

        pages.append({"words": word_entries, "links": link_entries})
        y_offset += page.rect.height

    doc.close()
    return pages


from urllib.parse import urlparse
import re

try:
    from github.githubProfile import build_candidate_github_profile, build_general_profile, build_project_specific_profiles
except ImportError:
    try:
        from githubProfile import build_candidate_github_profile, build_general_profile, build_project_specific_profiles
    except ImportError:
        build_candidate_github_profile = None


def _extract_github_username_from_parsed(parsed_details: dict) -> str | None:
    links = parsed_details.get("links", {})
    github_links = links.get("github", [])
    for gl in github_links:
        if not gl:
            continue
        url = gl.strip()
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + url
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        if host in ("github.com", "www.github.com"):
            parts = [p for p in parsed.path.split("/") if p]
            if parts and parts[0].lower() not in ("topics", "trending", "explore", "settings", "orgs"):
                return parts[0]

    # Also check project github links
    for p in links.get("projects", []):
        gh = p.get("github") if isinstance(p, dict) else None
        if gh:
            url = gh.strip()
            if not re.match(r"^https?://", url, re.I):
                url = "https://" + url
            parsed = urlparse(url)
            host = parsed.netloc.lower().split(":")[0]
            if host in ("github.com", "www.github.com"):
                parts = [part for part in parsed.path.split("/") if part]
                if parts and parts[0].lower() not in ("topics", "trending", "explore", "settings", "orgs"):
                    return parts[0]
    return None


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
    print(f"[Auth] Upload requested by user_id: {user_id}")
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "No selected file"})

    # Save the uploaded PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file_path = tmp.name
        contents = await file.read()
        tmp.write(contents)

    try:
        # Extract text using PyMuPDF (fitz)
        doc = fitz.open(file_path)
        text_content = ""
        for page in doc:
            text_content += page.get_text()
            text_content += "\n"
        doc.close()

        # Word-level layout + hyperlink annotations (needed for link resolution)
        layout = _extract_page_layout(file_path)

        # Clean up the temp file
        if os.path.exists(file_path):
            os.remove(file_path)

        # Parse using spaCy skillExtractor
        parsed_details = parse_resume(text_content, layout=layout)

        # Print every detail parsed to the console
        print("\n" + "="*30 + " SPACY PARSED RESUME DETAILS " + "="*30)
        pprint.pprint(parsed_details)
        print("="*89 + "\n")

        validation = parsed_details.get("validation", {})

        # "failed" = no name AND no skills detected
        if validation.get("status") == "failed":
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Resume parsing failed — no name or skills could be detected. "
                             "This usually means the PDF is scanned/image-only or has no "
                             "extractable text. Try a text-based PDF export instead.",
                    "issues": validation.get("issues", []),
                    "text": text_content,
                    "parsed_details": parsed_details
                }
            )

        # Automatic GitHub Profile & Code Metrics Discovery
        github_username = _extract_github_username_from_parsed(parsed_details)
        project_links = parsed_details.get("links", {}).get("projects", [])
        github_profile = None

        if github_username and build_candidate_github_profile:
            try:
                print(f"[GitHub Pipeline] Analyzing GitHub profile for user: {github_username}")
                github_profile = build_candidate_github_profile(
                    username=github_username,
                    resume_project_links=project_links,
                    n=3
                )
            except Exception as gh_err:
                print(f"[GitHub Pipeline Warning] {gh_err}")
                github_profile = {
                    "username": github_username,
                    "error": str(gh_err),
                    "general": {"repos": [], "aggregate_score": None, "failed_repos": []},
                    "project_specific": {"projects": [], "unresolved_projects": [], "failed_projects": []}
                }

        # -------------------------------------------------------------
        # Database Persistence & RAG Vector Ingestion
        # -------------------------------------------------------------
        saved_resume_id = None
        db = SessionLocal()
        try:
            try:
                user_uuid = uuid.UUID(str(user_id))
            except Exception:
                user_uuid = uuid.uuid4()

            # 1. Ensure Profile exists in database
            profile = db.query(Profile).filter(Profile.id == user_uuid).first()
            if not profile:
                profile = Profile(
                    id=user_uuid,
                    name=parsed_details.get("name") or "Candidate",
                    email=(parsed_details.get("emails") or [None])[0],
                    phone=(parsed_details.get("phones") or [None])[0],
                )
                db.add(profile)
                db.commit()

            # 2. Save Resume record
            detected_summary = parsed_details.get("summary") or (parsed_details.get("sections", {}).get("Summary"))
            new_resume = Resume(
                id=uuid.uuid4(),
                user_id=user_uuid,
                file_name=file.filename,
                raw_text=text_content,
                skills=parsed_details.get("skills", []),
                experience=parsed_details.get("experience", []),
                education=parsed_details.get("education", []),
                projects=parsed_details.get("projects", []),
                years_of_experience=parsed_details.get("years_of_experience"),
                summary=detected_summary,
                linkedin_url=(parsed_details.get("links", {}).get("linkedin") or [None])[0],
                github_username=github_username,
                sections=parsed_details.get("sections", {}),
                links=parsed_details.get("links", {}),
            )
            db.add(new_resume)
            db.commit()
            db.refresh(new_resume)
            saved_resume_id = str(new_resume.id)

            # 3. Save GitHub Repositories (if discovered)
            stored_repos = []
            if github_profile:
                general_repos = github_profile.get("general", {}).get("repos", [])
                for r in general_repos:
                    repo_id = uuid.uuid4()
                    gh_repo = GithubRepository(
                        id=repo_id,
                        user_id=user_uuid,
                        repo_name=r.get("name", "repo"),
                        url=r.get("url"),
                        description=r.get("description"),
                        languages=r.get("languages", {}),
                        architecture_score=r.get("architecture_score"),
                        testing_score=r.get("testing_score"),
                        complexity_score=r.get("complexity_score"),
                        documentation_score=r.get("documentation_score"),
                        commit_score=r.get("commit_score"),
                        overall_code_score=r.get("overall_code_score"),
                        readme_text=r.get("readme_text"),
                    )
                    db.add(gh_repo)
                    stored_repos.append({**r, "id": str(repo_id)})
                db.commit()

            # 4. Generate & Save ATS Report
            skills_count = len(parsed_details.get("skills", []))
            ats_score = min(98, 70 + skills_count * 2) if skills_count > 0 else 65
            ats_report = AtsReport(
                id=uuid.uuid4(),
                user_id=user_uuid,
                resume_id=new_resume.id,
                overall_score=ats_score,
                keyword_match=min(95, 65 + skills_count * 2),
                formatting_score=90,
                completeness_score=85,
                readability_score=90,
                suggestions=["Include quantified outcomes and architectural trade-offs in project bullet points."],
            )
            db.add(ats_report)
            db.commit()

            # 5. Ingest into RAG pgvector table (rag_documents)
            if build_all_chunks and store_chunks:
                try:
                    chunks = build_all_chunks(
                        candidate_id=str(user_uuid),
                        resume_sections=parsed_details.get("sections", {}),
                        resume_skills=parsed_details.get("skills", []),
                        resume_projects=parsed_details.get("projects", []),
                        resume_links=parsed_details.get("links", {}),
                        years_of_experience=parsed_details.get("years_of_experience"),
                        github_repos=stored_repos,
                    )
                    stored_count = store_chunks(db, chunks)
                    print(f"[RAG Database Ingestion] Successfully upserted {stored_count} chunks to rag_documents for user {user_uuid}.")
                except Exception as rag_err:
                    print(f"[RAG Database Warning] Could not store RAG chunks: {rag_err}")

        except Exception as db_err:
            print(f"[Database Save Error] {db_err}")
            db.rollback()
        finally:
            db.close()

        response_payload = {
            "message": "File parsed successfully and saved to database"
                        if validation.get("status") == "ok"
                        else "File parsed with warnings",
            "resume_id": saved_resume_id,
            "text": text_content,
            "parsed_details": parsed_details,
            "github_profile": github_profile,
        }
        return response_payload

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)