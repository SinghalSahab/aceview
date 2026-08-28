"""
Resume Ingestion & Persistence Service

Orchestrates the entire resume processing lifecycle:
1. Text & layout extraction from PDF (PyMuPDF)
2. NLP entity and skills parsing (spaCy skillExtractor)
3. GitHub profile discovery and code metrics calculation
4. Database persistence (Profile, Resume, GithubRepository, AtsReport)
5. RAG vector embeddings generation and storage (pgvector / rag_documents)
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Any
from urllib.parse import urlparse
import fitz  # PyMuPDF
from sqlalchemy.orm import Session

from db.models import Profile, Resume, GithubRepository, AtsReport
from skills.skillExtractor import parse_resume

try:
    from github.githubProfile import build_candidate_github_profile
except ImportError:
    try:
        from githubProfile import build_candidate_github_profile
    except ImportError:
        build_candidate_github_profile = None

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


def extract_pdf_layout(pdf_path: str) -> tuple[str, list[dict[str, Any]]]:
    """Extracts raw text and word-level layout/hyperlink annotations from PDF."""
    doc = fitz.open(pdf_path)
    text_content = ""
    pages = []
    y_offset = 0.0

    for page_index, page in enumerate(doc):
        text_content += page.get_text() + "\n"
        words = page.get_text("words")
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
    return text_content, pages


def extract_github_username(links: dict[str, Any]) -> str | None:
    """Extracts candidate GitHub username from parsed links."""
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


def ingest_and_save_resume(
    db: Session,
    user_id: str | uuid.UUID,
    file_name: str,
    file_path: str,
) -> dict[str, Any]:
    """
    Main service function: Parses resume PDF, runs GitHub analysis,
    persists all structured records into PostgreSQL / Supabase, and
    embeds vector chunks into pgvector.
    """
    user_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

    # 1. Extract raw text and layout
    text_content, layout = extract_pdf_layout(file_path)

    # 2. Parse using spaCy skillExtractor
    parsed_details = parse_resume(text_content, layout=layout)
    validation = parsed_details.get("validation", {})

    if validation.get("status") == "failed":
        return {
            "status": "failed",
            "error": "Resume parsing failed — no name or skills could be detected. "
                     "This usually means the PDF is scanned/image-only or has no "
                     "extractable text. Try a text-based PDF export instead.",
            "issues": validation.get("issues", []),
            "text": text_content,
            "parsed_details": parsed_details,
        }

    # 3. GitHub Profile Discovery & Metrics
    links = parsed_details.get("links", {})
    github_username = extract_github_username(links)
    project_links = links.get("projects", [])
    github_profile = None

    if github_username and build_candidate_github_profile:
        try:
            print(f"[GitHub Pipeline] Analyzing GitHub profile for user: {github_username}")
            github_profile = build_candidate_github_profile(
                username=github_username,
                resume_project_links=project_links,
                n=3,
            )
        except Exception as gh_err:
            print(f"[GitHub Pipeline Warning] {gh_err}")
            github_profile = {
                "username": github_username,
                "error": str(gh_err),
                "general": {"repos": [], "aggregate_score": None, "failed_repos": []},
                "project_specific": {"projects": [], "unresolved_projects": [], "failed_projects": []},
            }

    # 4. Database Persistence
    # 4a. Ensure Profile exists
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

    # 4b. Save Resume record (1:1 direct field mapping from parsed_details)
    new_resume = Resume(
        id=uuid.uuid4(),
        user_id=user_uuid,
        file_name=file_name,
        raw_text=text_content,
        summary=parsed_details.get("summary", ""),
        skills=parsed_details.get("skills", []),
        experience=parsed_details.get("experience", []),
        education=parsed_details.get("education", []),
        projects=parsed_details.get("projects", []),
        years_of_experience=parsed_details.get("years_of_experience"),
        sections=parsed_details.get("sections", {}),
        links=links,
        linkedin_url=(links.get("linkedin") or [None])[0],
        github_username=github_username,
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    # 4c. Save Discovered GitHub Repositories
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

    # 4d. Generate & Save ATS Report
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
                resume_links=links,
                years_of_experience=parsed_details.get("years_of_experience"),
                github_repos=stored_repos,
            )
            stored_count = store_chunks(db, chunks)
            print(f"[RAG Database Ingestion] Successfully upserted {stored_count} chunks to rag_documents for user {user_uuid}.")
        except Exception as rag_err:
            print(f"[RAG Database Warning] Could not store RAG chunks: {rag_err}")

    return {
        "status": "ok" if validation.get("status") == "ok" else "flagged",
        "message": "File parsed successfully and saved to database",
        "resume_id": str(new_resume.id),
        "text": text_content,
        "parsed_details": parsed_details,
        "github_profile": github_profile,
    }


def get_user_resumes(db: Session, user_id: str) -> dict:
    """Fetches all resumes and associated ATS scores for a specific authenticated user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return {"error": "Invalid user ID format", "status_code": 400}

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


def delete_user_resume(db: Session, user_id: str, resume_id: str) -> dict:
    """Deletes a resume and any associated ATS records for a specific authenticated user."""
    try:
        resume_uuid = uuid.UUID(resume_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return {"error": "Invalid UUID format", "status_code": 400}

    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_uuid, Resume.user_id == user_uuid)
        .first()
    )
    if not resume:
        return {"error": "Resume not found", "status_code": 404}

    try:
        db.query(AtsReport).filter(AtsReport.resume_id == resume_uuid).delete()
        db.delete(resume)
        db.commit()
        return {"status": "ok", "message": "Resume deleted successfully"}
    except Exception as e:
        db.rollback()
        return {"error": str(e), "status_code": 500}

