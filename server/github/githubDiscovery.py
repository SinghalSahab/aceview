"""
github_discovery.py

Step 3.1 — Repo Discovery (PM Plan Step 3.1)

Two independent discovery paths, both using the authenticated GitHub REST
API:

  (a) General top-N=5 discovery: fetch ALL of the candidate's public repos,
      exclude forks unless the candidate has their own commits in them, then
      score the rest by composite relevance and keep the top N. This feeds
      the overall/aggregate GitHub code-quality analysis (Step 3.4).

  (b) Project-specific resolution: for each project the candidate listed on
      their resume (using the `links.projects[].github` URLs already
      extracted by skillExtractor.py), fetch that EXACT repo directly — no
      scoring or selection needed, since we already know precisely which
      repo it is. This feeds a separate, per-project analysis later, kept
      distinct from the general top-5 set even if a project repo happens to
      also be one of the top-5.

Auth
----
Reads a GitHub Personal Access Token from the GITHUB_TOKEN environment
variable if present:
  - No token: 60 requests/hour (fine for light testing, not for production).
  - With token: 5,000 requests/hour.
Set GITHUB_TOKEN later and nothing else in this file needs to change.
"""

import os
import re
import math
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url, params=None):
    resp = requests.get(url, headers=_headers(), params=params, timeout=15)
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RuntimeError(
            "GitHub API rate limit exceeded. Unauthenticated requests are "
            "limited to 60/hour — set the GITHUB_TOKEN environment variable "
            "to a Personal Access Token to raise this to 5,000/hour."
        )
    if resp.status_code == 404:
        raise LookupError(f"GitHub API 404 for {url}")
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# 3.1.1 — Fetch all public repos, sorted by pushed date
# ---------------------------------------------------------------------------
def fetch_user_repos(username: str, per_page: int = 100) -> list:
    """
    GET /users/{username}/repos, sorted by pushed date (most recent first).
    Paginates until exhausted.
    """
    repos = []
    page = 1
    while True:
        resp = _get(
            f"{GITHUB_API_BASE}/users/{username}/repos",
            params={"sort": "pushed", "direction": "desc", "per_page": per_page, "page": page},
        )
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return repos


# ---------------------------------------------------------------------------
# 3.1.1 — Fork filtering: exclude forks UNLESS the candidate has own commits
# ---------------------------------------------------------------------------
def _has_own_commits(username: str, owner: str, repo: str) -> bool:
    """
    GET /repos/{owner}/{repo}/commits?author={username} — a fork with zero
    commits authored by the candidate is almost certainly unmodified and
    shouldn't count toward their body of work.
    """
    try:
        resp = _get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            params={"author": username, "per_page": 1},
        )
        return len(resp.json()) > 0
    except Exception:
        # empty repo / no commit history / transient error — treat
        # conservatively as "no own commits" rather than raising
        return False


def filter_forks(username: str, repos: list) -> list:
    kept = []
    for repo in repos:
        if not repo.get("fork"):
            kept.append(repo)
            continue
        owner = repo["owner"]["login"]
        name = repo["name"]
        if _has_own_commits(username, owner, name):
            kept.append(repo)
    return kept


# ---------------------------------------------------------------------------
# 3.1.2 — Composite relevance score: recency(40%) + popularity(20%) + has_source(40%)
# ---------------------------------------------------------------------------
def _recency_score(pushed_at: str) -> float:
    """0-100: pushed today -> 100, decaying linearly to 0 over 2 years."""
    if not pushed_at:
        return 0.0
    pushed = datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    days_ago = (datetime.now(timezone.utc) - pushed).days
    return max(0.0, 100.0 - (days_ago / 730.0) * 100.0)


def _popularity_score(stars: int, forks: int) -> float:
    """0-100, log-scaled so a handful of stars/forks doesn't saturate the score. ~100 combined stars+forks -> ~100."""
    raw = (stars or 0) + (forks or 0)
    if raw <= 0:
        return 0.0
    return min(100.0, math.log10(raw + 1) / math.log10(101) * 100.0)


def _has_source_beyond_readme(owner: str, repo: str) -> float:
    """
    0 or 100: inspects the repo's root contents for anything beyond a
    README/LICENSE/.gitignore-style file. Used to avoid wasting the Step
    3.2/3.3 analysis budget on empty/placeholder repos.
    """
    non_source_names = {
        "readme.md", "readme", "readme.txt", "license", "license.md",
        ".gitignore", ".gitattributes", "contributing.md", "code_of_conduct.md",
    }
    try:
        resp = _get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/")
        items = resp.json()
    except Exception:
        return 0.0
    if not isinstance(items, list):
        return 0.0
    for item in items:
        if item.get("name", "").lower() not in non_source_names:
            return 100.0
    return 0.0


def score_repo(repo: dict) -> dict:
    """
    Returns a shallow copy of `repo` augmented with:
      _relevance_score (0-100) and _relevance_breakdown {recency, popularity, has_source_beyond_readme}
    """
    owner = repo["owner"]["login"]
    name = repo["name"]

    recency = _recency_score(repo.get("pushed_at"))
    popularity = _popularity_score(repo.get("stargazers_count", 0), repo.get("forks_count", 0))
    has_source = _has_source_beyond_readme(owner, name)

    relevance = 0.4 * recency + 0.2 * popularity + 0.4 * has_source

    scored = dict(repo)
    scored["_relevance_score"] = round(relevance, 2)
    scored["_relevance_breakdown"] = {
        "recency": round(recency, 2),
        "popularity": round(popularity, 2),
        "has_source_beyond_readme": has_source,
    }
    return scored


# ---------------------------------------------------------------------------
# 3.1 full pipeline (general, top-N)
# ---------------------------------------------------------------------------
def select_top_repos(username: str, n: int = 5) -> list:
    """
    fetch -> filter forks -> score -> top N by relevance, most relevant first.
    This is the general discovery path feeding the aggregate/profile-level
    analysis in Step 3.4 — kept separate from project-specific resolution.
    """
    repos = fetch_user_repos(username)
    repos = filter_forks(username, repos)
    scored = [score_repo(r) for r in repos]
    scored.sort(key=lambda r: r["_relevance_score"], reverse=True)
    return scored[:n]


# ---------------------------------------------------------------------------
# Project-specific repo resolution (from resume-extracted GitHub links)
# ---------------------------------------------------------------------------
def parse_owner_repo_from_url(github_url: str):
    """
    'https://github.com/jane/blinkbuild' -> ('jane', 'blinkbuild'); None if
    unparseable OR if the host isn't actually github.com (checked via a real
    hostname comparison, not a substring match — a naive regex search for
    "github.com" would incorrectly match a URL like "not-github.com/x/y",
    since that string also contains "github.com" as a substring).
    """
    if not github_url:
        return None
    url = github_url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    if host not in ("github.com", "www.github.com"):
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    repo = re.sub(r"\.git$", "", repo)
    return owner, repo


def fetch_repo_by_owner_name(owner: str, repo: str) -> dict:
    """GET /repos/{owner}/{repo} — direct fetch, no scoring (we already know exactly which repo it is)."""
    return _get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}").json()


def resolve_project_repos(resume_project_links: list):
    """
    Args:
      resume_project_links: the `links.projects` list produced by
      skillExtractor.py's parse_resume(), e.g.
        [{"project": "BlinkBuild ...", "github": "https://github.com/jane/blinkbuild", ...}, ...]

    Returns (resolved, unresolved):
      resolved:   [{"project_name": str, "repo": <GitHub repo API dict>}, ...]
      unresolved: [project_name, ...]  — projects with no parseable GitHub
                  link, or a 404/fetch failure, surfaced explicitly rather
                  than silently dropped, so the candidate can be told
                  "couldn't verify this project's code" instead of it just
                  disappearing.
    """
    resolved, unresolved = [], []
    for proj in resume_project_links:
        github_url = proj.get("github")
        parsed = parse_owner_repo_from_url(github_url) if github_url else None
        if not parsed:
            unresolved.append(proj.get("project"))
            continue
        owner, repo_name = parsed
        try:
            repo_data = fetch_repo_by_owner_name(owner, repo_name)
            resolved.append({"project_name": proj.get("project"), "repo": repo_data})
        except Exception:
            unresolved.append(proj.get("project"))
    return resolved, unresolved


if __name__ == "__main__":
    import pprint
    # Live smoke test against a real, well-known public account.
    top = select_top_repos("octocat", n=3)
    print(f"Top {len(top)} repos for octocat:")
    for r in top:
        print(f"  {r['name']:30s} score={r['_relevance_score']:6.2f}  breakdown={r['_relevance_breakdown']}")

    print()
    resolved, unresolved = resolve_project_repos([
        {"project": "Hello World Demo", "github": "https://github.com/octocat/Hello-World"},
        {"project": "Broken Link Demo", "github": "https://github.com/octocat/this-repo-does-not-exist-xyz"},
        {"project": "No GitHub Link Demo", "github": None},
    ])
    print("Resolved project repos:")
    for r in resolved:
        print(f"  {r['project_name']!r} -> {r['repo']['full_name']}")
    print("Unresolved:", unresolved)