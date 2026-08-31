"""
github_profile.py

Step 3.4 — Aggregation (PM Plan Step 3.4), extended per explicit request to
keep TWO independent output tracks rather than one merged list:

  1. General/overall profile: the top-N=5 repos from github_discovery's
     composite relevance scoring (Step 3.1), each analyzed via
     code_retrieval + code_metrics (Steps 3.2/3.3), merged into a single
     relevance-weighted aggregate score — this is the literal Step 3.4 spec
     ("compute an aggregate (average weighted by repo relevance score from
     3.1)").

  2. Project-specific profiles: each GitHub-linked project from the
     candidate's resume (resolved directly by github_discovery.
     resolve_project_repos — NOT part of the scored top-5 selection, we
     already know exactly which repo it is), independently analyzed the
     same way, but reported PER PROJECT rather than folded into the
     aggregate — so the dashboard can show "here's specifically how
     BlinkBuild's code looked" alongside general profile quality, even if
     that project also happens to be one of the top-5.

Ties together github_discovery.py + code_retrieval.py + code_metrics.py
into the full Step 3 pipeline, and shapes the output to match the
Candidate Profile schema's `github.repos[]` field names (architecture_score,
testing_score, complexity_score, documentation_score, commit_score,
overall_code_score) from PM Plan Step 1, while also keeping the fuller
nested breakdown available for the dashboard.
"""

try:
    from github import githubDiscovery as gd
    from github import codeRetrieval as cr
    from github import codeMetrics as cm
except ImportError:
    try:
        import githubDiscovery as gd
        import codeRetrieval as cr
        import codeMetrics as cm
    except ImportError:
        import github_discovery as gd
        import code_retrieval as cr
        import code_metrics as cm



def _analyze_one_repo(clone_url: str) -> dict:
    """
    Full 3.2 -> 3.3 pipeline for a single repo: shallow clone -> budget-
    select files -> compute metrics. Always cleans up the temp clone dir
    before returning, even on failure (via try/finally).

    Returns both the schema-flat score fields (architecture_score,
    testing_score, complexity_score, documentation_score, commit_score,
    overall_code_score) AND the fuller sub_scores/breakdown dicts for
    dashboard use.
    """
    retrieval = cr.retrieve_repo_code(clone_url)
    try:
        metrics = cm.compute_repo_metrics(retrieval["files"], retrieval["clone_dir"])
    finally:
        cr.cleanup_clone(retrieval["clone_dir"])

    sub = metrics["sub_scores"]
    readme_info = metrics.get("breakdown", {}).get("documentation", {}).get("readme", {})
    readme_text = readme_info.get("readme_text") or ""

    return {
        "architecture_score": sub["architecture"],
        "testing_score": sub["testing"],
        "complexity_score": sub["complexity"],
        "documentation_score": sub["documentation"],
        "commit_score": sub["commit_history"],
        "overall_code_score": metrics["overall_code_score"],
        "readme_text": readme_text,
        "sub_scores": sub,
        "breakdown": metrics["breakdown"],
        "files_analyzed": retrieval["total_files_selected"],
        "total_loc_analyzed": retrieval["total_loc_selected"],
    }


# ---------------------------------------------------------------------------
# 3.4.1 — General profile: top-5 repos, relevance-weighted aggregate
# ---------------------------------------------------------------------------
def build_general_profile(username: str, n: int = 5) -> dict:
    """
    3.1 (select_top_repos) -> per-repo 3.2/3.3 analysis -> 3.4 aggregation
    (relevance-weighted average of overall_code_score across the N repos,
    using each repo's _relevance_score from Step 3.1 as its weight).

    A repo whose clone/analysis fails (private, empty, transient network
    error) is excluded from both the repos list and the aggregate
    weighting — recorded in `failed_repos` rather than silently dropped.
    """
    top_repos = gd.select_top_repos(username, n=n)

    analyzed = []
    failed = []
    for repo in top_repos:
        try:
            analysis = _analyze_one_repo(repo["clone_url"])
        except Exception as e:
            failed.append({"name": repo["name"], "error": str(e)})
            continue

        primary_lang = repo.get("language")
        languages_dict = {"primary": primary_lang} if primary_lang else {}

        analyzed.append({
            "name": repo["name"],
            "full_name": repo.get("full_name", repo["name"]),
            "github_repo_id": repo.get("id"),
            "description": repo.get("description"),
            "url": repo.get("html_url") or repo.get("clone_url"),
            "is_fork": repo.get("fork", False),
            "languages": languages_dict,
            "relevance_score": repo.get("_relevance_score"),
            "relevance_breakdown": repo.get("_relevance_breakdown"),
            **analysis,
        })

    if not analyzed:
        return {"repos": [], "aggregate_score": None, "failed_repos": failed}

    total_weight = sum(r["relevance_score"] for r in analyzed)
    if total_weight <= 0:
        # guard against div-by-zero if every repo somehow scored 0 relevance
        aggregate = sum(r["overall_code_score"] for r in analyzed) / len(analyzed)
    else:
        aggregate = sum(r["overall_code_score"] * (r["relevance_score"] / total_weight) for r in analyzed)

    return {
        "repos": analyzed,
        "aggregate_score": round(aggregate, 2),
        "failed_repos": failed,
    }


# ---------------------------------------------------------------------------
# 3.4.2 — Project-specific profiles (one per resume project, independent)
# ---------------------------------------------------------------------------
def build_project_specific_profiles(resume_project_links: list) -> dict:
    """
    Resolves each resume project's GitHub link to its exact repo (via
    github_discovery.resolve_project_repos — no scoring/selection needed,
    we already know which repo it is) and independently analyzes each one.
    Kept as a SEPARATE per-project list, never merged into the general
    top-5 aggregate above.
    """
    resolved, unresolved = gd.resolve_project_repos(resume_project_links)

    analyzed = []
    failed = []
    for item in resolved:
        repo = item["repo"]
        try:
            analysis = _analyze_one_repo(repo["clone_url"])
        except Exception as e:
            failed.append({"project_name": item["project_name"], "error": str(e)})
            continue

        primary_lang = repo.get("language")
        languages_dict = {"primary": primary_lang} if primary_lang else {}

        analyzed.append({
            "project_name": item["project_name"],
            "name": repo.get("name", item["project_name"]),
            "full_name": repo.get("full_name", repo.get("name")),
            "github_repo_id": repo.get("id"),
            "description": repo.get("description"),
            "url": repo.get("html_url") or repo.get("clone_url"),
            "is_fork": repo.get("fork", False),
            "languages": languages_dict,
            **analysis,
        })

    return {
        "projects": analyzed,
        "unresolved_projects": unresolved,   # no parseable GitHub link on the resume
        "failed_projects": failed,           # had a link, but clone/analysis failed
    }



try:
    from github.githubProfileMetrics import analyze_full_github_profile
except ImportError:
    try:
        from githubProfileMetrics import analyze_full_github_profile
    except ImportError:
        analyze_full_github_profile = None


# ---------------------------------------------------------------------------
# Full Step 3 pipeline entry point
# ---------------------------------------------------------------------------
def build_candidate_github_profile(username: str, resume_project_links: list, n: int = 5) -> dict:
    """
    Shape matches the Candidate Profile schema's `github` field (PM Plan
    Step 1), extended with the general/project_specific split and overall
    profile scoring summary:

    {
      "username": str,
      "general": {"repos": [...], "aggregate_score": float, "failed_repos": [...]},
      "project_specific": {"projects": [...], "unresolved_projects": [...], "failed_projects": [...]},
      "profile_summary": {"score_data": {...}, "rag_summary": str, "raw_metrics": {...}}
    }
    """
    general = build_general_profile(username, n=n)
    project_specific = build_project_specific_profiles(resume_project_links)

    profile_summary = None
    if analyze_full_github_profile:
        try:
            profile_summary = analyze_full_github_profile(username)
        except Exception as e:
            print(f"[GitHub Profile Metrics Warning] {e}")

    return {
        "username": username,
        "general": general,
        "project_specific": project_specific,
        "profile_summary": profile_summary,
    }



def handle_analyze_github_user(username: str, user_id: str):
    """Abstract controller function for analyzing candidate GitHub profile."""
    from fastapi.responses import JSONResponse

    print(f"[Auth] GitHub analysis requested by user_id: {user_id}")
    try:
        profile = build_candidate_github_profile(username=username, resume_project_links=[], n=5)
        return profile
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "username": username})



if __name__ == "__main__":
    import json
    # Live smoke test against a real account with a small number of real
    # repos, kept small (n=2) to stay within a fresh rate-limit window.
    resume_links = [
        {"project": "Hello World Demo", "github": "https://github.com/octocat/Hello-World"},
        {"project": "Spoon Knife Fork Demo", "github": "https://github.com/octocat/Spoon-Knife"},
    ]
    profile = build_candidate_github_profile("octocat", resume_links, n=2)
    print(json.dumps(profile, indent=2, default=str))