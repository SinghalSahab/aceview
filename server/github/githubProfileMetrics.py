"""
github_profile_metrics.py

Overall GitHub Profile Scoring Engine & Analytics

Extracts profile-wide signals using the GitHub GraphQL API (with REST fallback)
and computes a normalized 0-100 composite developer profile score:
  - 30% Contribution Volume & Frequency
  - 25% Consistency & Active Weekly Cadence
  - 20% Collaboration & PR / Code Review Activity
  - 15% Community Impact & Star Reach
  - 10% Language Breadth & Stack Maturity

Also formats profile analytics for vector RAG insertion (source_type="github_profile_summary").
"""

from __future__ import annotations

import os
import re
import math
import requests
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def _get_auth_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AceView-Profile-Analyzer",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ---------------------------------------------------------------------------
# 1. Data Collection: GraphQL API with REST Fallback
# ---------------------------------------------------------------------------

GRAPHQL_PROFILE_QUERY = """
query CandidateProfileOverview($login: String!) {
  user(login: $login) {
    login
    name
    createdAt
    followers {
      totalCount
    }
    following {
      totalCount
    }
    starredRepositories {
      totalCount
    }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      isFork: false
      orderBy: { field: PUSHED_AT, direction: DESC }
    ) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        isFork
        pushedAt
        languages(first: 10, orderBy: { field: SIZE, direction: DESC }) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


def _fetch_profile_graphql(username: str) -> dict[str, Any] | None:
    """Queries GitHub GraphQL API for comprehensive profile and contribution data."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return None

    try:
        resp = requests.post(
            GITHUB_GRAPHQL_URL,
            headers=_get_auth_headers(),
            json={"query": GRAPHQL_PROFILE_QUERY, "variables": {"login": username}},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if "errors" in data or not data.get("data", {}).get("user"):
            return None
        return data["data"]["user"]
    except Exception as e:
        print(f"[GitHub Profile Metrics] GraphQL fetch warning: {e}")
        return None


def _fetch_profile_rest(username: str) -> dict[str, Any]:
    """Fallback REST data collector when GraphQL or GITHUB_TOKEN is not available."""
    headers = _get_auth_headers()

    # 1. User core profile
    user_res = requests.get(f"{GITHUB_API_BASE}/users/{username}", headers=headers, timeout=10)
    user_data = user_res.json() if user_res.status_code == 200 else {}

    # 2. User repositories
    repos_res = requests.get(
        f"{GITHUB_API_BASE}/users/{username}/repos",
        headers=headers,
        params={"type": "owner", "sort": "pushed", "direction": "desc", "per_page": 100},
        timeout=15,
    )
    repos_list = repos_res.json() if repos_res.status_code == 200 and isinstance(repos_res.json(), list) else []

    # 3. User recent public events
    events_res = requests.get(
        f"{GITHUB_API_BASE}/users/{username}/events",
        headers=headers,
        params={"per_page": 100},
        timeout=10,
    )
    events_list = events_res.json() if events_res.status_code == 200 and isinstance(events_res.json(), list) else []

    return {
        "login": username,
        "user_data": user_data,
        "repos": repos_list,
        "events": events_list,
    }


def extract_raw_profile_metrics(username: str) -> dict[str, Any]:
    """
    Extracts unified raw profile signals from either GraphQL or REST fallback.
    """
    gql_data = _fetch_profile_graphql(username)

    if gql_data:
        # Parsed via GraphQL
        created_at_str = gql_data.get("createdAt")
        followers_count = gql_data.get("followers", {}).get("totalCount", 0)
        following_count = gql_data.get("following", {}).get("totalCount", 0)
        starred_count = gql_data.get("starredRepositories", {}).get("totalCount", 0)

        repos_nodes = gql_data.get("repositories", {}).get("nodes", [])
        total_repos_count = gql_data.get("repositories", {}).get("totalCount", len(repos_nodes))

        total_stars = sum(r.get("stargazerCount", 0) for r in repos_nodes)
        total_forks = sum(r.get("forkCount", 0) for r in repos_nodes)

        # Aggregate languages
        language_bytes: dict[str, int] = {}
        for r in repos_nodes:
            lang_edges = r.get("languages", {}).get("edges", [])
            for edge in lang_edges:
                l_name = edge.get("node", {}).get("name")
                l_size = edge.get("size", 0)
                if l_name and l_size > 0:
                    language_bytes[l_name] = language_bytes.get(l_name, 0) + l_size

        contribs = gql_data.get("contributionsCollection", {})
        calendar = contribs.get("contributionCalendar", {})
        annual_contributions = calendar.get("totalContributions", 0)
        commits = contribs.get("totalCommitContributions", 0)
        prs = contribs.get("totalPullRequestContributions", 0)
        reviews = contribs.get("totalPullRequestReviewContributions", 0)
        issues = contribs.get("totalIssueContributions", 0)
        repo_contribs = contribs.get("totalRepositoryContributions", 0)
        restricted = contribs.get("restrictedContributionsCount", 0)

        # Process calendar days for streaks and active cadence
        weeks = calendar.get("weeks", [])
        active_days = 0
        active_weeks = 0
        longest_streak = 0
        current_streak = 0

        for w in weeks:
            week_days = w.get("contributionDays", [])
            week_has_contrib = False
            for d in week_days:
                count = d.get("contributionCount", 0)
                if count > 0:
                    active_days += 1
                    week_has_contrib = True
                    current_streak += 1
                    if current_streak > longest_streak:
                        longest_streak = current_streak
                else:
                    current_streak = 0
            if week_has_contrib:
                active_weeks += 1

        return {
            "source": "graphql",
            "username": username,
            "name": gql_data.get("name") or username,
            "created_at": created_at_str,
            "followers": followers_count,
            "following": following_count,
            "starred_repos_count": starred_count,
            "public_repos_count": total_repos_count,
            "total_stars_received": total_stars,
            "total_forks_received": total_forks,
            "annual_contributions": max(annual_contributions, commits + prs + reviews + issues + restricted),
            "total_commits": commits,
            "total_prs": prs,
            "total_reviews": reviews,
            "total_issues": issues,
            "total_repos_created": repo_contribs,
            "active_days": active_days,
            "active_weeks": active_weeks,
            "longest_streak_days": longest_streak,
            "language_bytes": language_bytes,
        }

    # Fallback to REST API estimation
    rest_data = _fetch_profile_rest(username)
    u_info = rest_data.get("user_data", {})
    repos = rest_data.get("repos", [])
    events = rest_data.get("events", [])

    created_at_str = u_info.get("created_at")
    followers_count = u_info.get("followers", 0)
    public_repos_count = u_info.get("public_repos", len(repos))

    total_stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
    total_forks = sum(r.get("forks_count", 0) for r in repos if not r.get("fork"))

    language_bytes: dict[str, int] = {}
    for r in repos:
        primary_lang = r.get("language")
        size_kb = r.get("size", 10)
        if primary_lang:
            language_bytes[primary_lang] = language_bytes.get(primary_lang, 0) + (size_kb * 1024)

    # Estimate activity from recent event history
    commits = 0
    prs = 0
    reviews = 0
    issues = 0
    event_days = set()

    for ev in events:
        ev_type = ev.get("type")
        c_date = (ev.get("created_at") or "")[:10]
        if c_date:
            event_days.add(c_date)

        if ev_type == "PushEvent":
            payload = ev.get("payload", {})
            commits += len(payload.get("commits", [])) or 1
        elif ev_type in ("PullRequestEvent", "PullRequestReviewCommentEvent"):
            prs += 1
        elif ev_type == "PullRequestReviewEvent":
            reviews += 1
        elif ev_type == "IssuesEvent":
            issues += 1

    active_days = len(event_days)
    estimated_annual = max(active_days * 3, commits + prs + reviews + issues)
    active_weeks = min(52, max(1, active_days // 2))

    return {
        "source": "rest_fallback",
        "username": username,
        "name": u_info.get("name") or username,
        "created_at": created_at_str,
        "followers": followers_count,
        "following": u_info.get("following", 0),
        "starred_repos_count": 0,
        "public_repos_count": public_repos_count,
        "total_stars_received": total_stars,
        "total_forks_received": total_forks,
        "annual_contributions": estimated_annual,
        "total_commits": commits,
        "total_prs": prs,
        "total_reviews": reviews,
        "total_issues": issues,
        "total_repos_created": public_repos_count,
        "active_days": active_days,
        "active_weeks": active_weeks,
        "longest_streak_days": min(14, active_days),
        "language_bytes": language_bytes,
    }


# ---------------------------------------------------------------------------
# 2. Normalized Scoring Formula (0 to 100)
# ---------------------------------------------------------------------------

def compute_overall_github_score(raw_metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Computes a normalized composite score (0-100) based on developer habits:
      - 30% Contribution Volume & Frequency
      - 25% Consistency & Active Weekly Cadence
      - 20% Collaboration & PR/Review Activity
      - 15% Community Impact & Star Reach
      - 10% Language Breadth & Stack Maturity

    Includes division-by-zero protection, smooth log scaling, and bot dampening.
    """
    annual_contribs = max(0, int(raw_metrics.get("annual_contributions", 0)))
    active_days = max(0, int(raw_metrics.get("active_days", 0)))
    active_weeks = max(0, min(52, int(raw_metrics.get("active_weeks", 0))))
    longest_streak = max(0, int(raw_metrics.get("longest_streak_days", 0)))
    total_prs = max(0, int(raw_metrics.get("total_prs", 0)))
    total_reviews = max(0, int(raw_metrics.get("total_reviews", 0)))
    total_issues = max(0, int(raw_metrics.get("total_issues", 0)))
    total_stars = max(0, int(raw_metrics.get("total_stars_received", 0)))
    total_forks = max(0, int(raw_metrics.get("total_forks_received", 0)))
    followers = max(0, int(raw_metrics.get("followers", 0)))
    language_bytes = raw_metrics.get("language_bytes", {}) or {}

    # Account maturity
    created_at_str = raw_metrics.get("created_at")
    account_age_days = 365
    if created_at_str:
        try:
            created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            account_age_days = max(1, (datetime.now(timezone.utc) - created_dt).days)
        except Exception:
            account_age_days = 365

    account_months = max(1.0, account_age_days / 30.417)
    contributions_per_month = round(annual_contribs / min(12.0, account_months), 1)

    # -----------------------------------------------------------------------
    # Sub-score 1: Contribution Volume & Frequency (30% weight)
    # Benchmark: 0 -> 0; 50 -> 50; 200 -> 80; 500+ -> 100 (log-damped)
    # -----------------------------------------------------------------------
    if annual_contribs <= 0:
        volume_score = 0.0
    else:
        # log10(1 + 500) ≈ 2.70
        volume_score = min(100.0, (math.log10(1 + annual_contribs) / math.log10(501)) * 100.0)

    # -----------------------------------------------------------------------
    # Sub-score 2: Consistency & Active Cadence (25% weight)
    # Rewards steady weekly habits over a 1-weekend commit explosion
    # -----------------------------------------------------------------------
    active_weeks_ratio = active_weeks / 52.0
    active_days_ratio = min(1.0, active_days / 365.0)
    streak_score = min(100.0, (longest_streak / 21.0) * 100.0)  # 21-day streak is excellent

    consistency_score = min(
        100.0,
        (0.50 * (active_weeks_ratio * 100.0)) +
        (0.30 * min(100.0, active_days_ratio * 100.0 * 2.5)) +
        (0.20 * streak_score)
    )

    # -----------------------------------------------------------------------
    # Sub-score 3: Collaboration & PR/Review Activity (20% weight)
    # Evaluates PRs, code reviews, and issue participation
    # -----------------------------------------------------------------------
    collab_points = (total_prs * 7.0) + (total_reviews * 10.0) + (total_issues * 3.0)
    if collab_points <= 0:
        collaboration_score = min(40.0, volume_score * 0.3)  # Partial credit if high solo commits
    else:
        collaboration_score = min(100.0, (collab_points / 50.0) * 100.0)

    # -----------------------------------------------------------------------
    # Sub-score 4: Community Impact & Star Reach (15% weight)
    # Stars, forks, and followers
    # -----------------------------------------------------------------------
    impact_points = (total_stars * 6.0) + (total_forks * 8.0) + (followers * 2.0)
    if impact_points <= 0:
        impact_score = 15.0 if raw_metrics.get("public_repos_count", 0) > 0 else 0.0
    else:
        impact_score = min(100.0, (math.log10(1 + impact_points) / math.log10(101)) * 100.0)

    # -----------------------------------------------------------------------
    # Sub-score 5: Language Breadth & Stack Maturity (10% weight)
    # Analyzes primary languages and polyglot capability
    # -----------------------------------------------------------------------
    total_bytes = sum(language_bytes.values())
    significant_languages = []
    if total_bytes > 0:
        for lang, b_count in sorted(language_bytes.items(), key=lambda x: x[1], reverse=True):
            ratio = b_count / total_bytes
            if ratio >= 0.03 or b_count >= 5000:  # At least 3% of code or 5KB
                significant_languages.append({"language": lang, "percentage": round(ratio * 100, 1), "bytes": b_count})

    diversity_count = len(significant_languages)
    if diversity_count == 0:
        language_score = 20.0
    elif diversity_count == 1:
        language_score = 55.0
    elif diversity_count == 2:
        language_score = 80.0
    elif diversity_count == 3:
        language_score = 92.0
    else:
        language_score = 100.0

    # -----------------------------------------------------------------------
    # Final Composite Score (0 - 100)
    # -----------------------------------------------------------------------
    overall_score = (
        (0.30 * volume_score) +
        (0.25 * consistency_score) +
        (0.20 * collaboration_score) +
        (0.15 * impact_score) +
        (0.10 * language_score)
    )

    return {
        "overall_score": round(overall_score, 2),
        "sub_scores": {
            "volume_and_frequency": round(volume_score, 2),
            "consistency_and_cadence": round(consistency_score, 2),
            "collaboration_and_prs": round(collaboration_score, 2),
            "community_impact": round(impact_score, 2),
            "language_breadth": round(language_score, 2),
        },
        "weights": {
            "volume": 0.30,
            "consistency": 0.25,
            "collaboration": 0.20,
            "community_impact": 0.15,
            "language_breadth": 0.10,
        },
        "signals": {
            "annual_contributions": annual_contribs,
            "active_days_ratio": round(active_days_ratio, 4),
            "active_weeks_ratio": round(active_weeks_ratio, 4),
            "longest_streak_days": longest_streak,
            "total_pull_requests": total_prs,
            "total_code_reviews": total_reviews,
            "total_stars_received": total_stars,
            "total_forks_received": total_forks,
            "account_age_days": account_age_days,
            "contributions_per_month": contributions_per_month,
            "primary_languages": significant_languages[:6],
        }
    }


# ---------------------------------------------------------------------------
# 3. RAG Summary Generator for AI Mock Interviewer
# ---------------------------------------------------------------------------

def format_github_profile_rag_summary(username: str, score_data: dict[str, Any]) -> str:
    """
    Formats the profile analytics into an authoritative markdown briefing
    for RAG ingestion (source_type='github_profile_summary') so the AI interviewer
    agent can evaluate candidate consistency, habits, and stack proficiency.
    """
    overall = score_data.get("overall_score", 0.0)
    sub = score_data.get("sub_scores", {})
    signals = score_data.get("signals", {})

    langs = signals.get("primary_languages", [])
    lang_str = ", ".join(f"{l['language']} ({l['percentage']}%)" for l in langs) if langs else "Not detected"

    # Habit rating badge
    if overall >= 85:
        habit_rating = "Highly Active Polyglot Contributor"
    elif overall >= 70:
        habit_rating = "Steady & Consistent Developer"
    elif overall >= 50:
        habit_rating = "Moderate Contributor"
    else:
        habit_rating = "Early Stage / Occasional Contributor"

    summary_lines = [
        f"### Overall GitHub Candidate Developer Profile (@{username})",
        f"- **Overall GitHub Profile Score**: {overall}/100 ({habit_rating})",
        f"- **Annual Contribution Volume**: {signals.get('annual_contributions', 0)} total contributions ({signals.get('contributions_per_month', 0)}/month). Sub-score: {sub.get('volume_and_frequency', 0)}/100.",
        f"- **Consistency & Cadence**: Active on {int(signals.get('active_weeks_ratio', 0) * 52)} of 52 weeks ({int(signals.get('active_days_ratio', 0) * 365)} active days/year). Longest streak: {signals.get('longest_streak_days', 0)} days. Sub-score: {sub.get('consistency_and_cadence', 0)}/100.",
        f"- **Collaboration & Open Source**: {signals.get('total_pull_requests', 0)} Pull Requests created, {signals.get('total_code_reviews', 0)} Code Reviews submitted. Sub-score: {sub.get('collaboration_and_prs', 0)}/100.",
        f"- **Community Impact**: {signals.get('total_stars_received', 0)} Stars earned across repositories, {signals.get('total_forks_received', 0)} Forks. Sub-score: {sub.get('community_impact', 0)}/100.",
        f"- **Primary Tech Stack & Breadth**: {lang_str}. Sub-score: {sub.get('language_breadth', 0)}/100.",
        "",
        "#### Interviewer Context & Probing Suggestions:",
    ]

    if signals.get("total_code_reviews", 0) > 0:
        summary_lines.append(f"- Candidate actively participates in code review workflows ({signals.get('total_code_reviews')} reviews completed); probe their code review checklist and team collaboration style.")
    if signals.get("longest_streak_days", 0) >= 14:
        summary_lines.append(f"- Candidate demonstrates sustained engineering discipline with a {signals.get('longest_streak_days')}-day contribution streak.")
    if len(langs) >= 2:
        summary_lines.append(f"- Candidate writes across multiple ecosystems ({langs[0]['language']} and {langs[1]['language']}); test architectural trade-offs between these paradigms.")

    return "\n".join(summary_lines)


# ---------------------------------------------------------------------------
# 4. Full Profile Analysis Pipeline Entrypoint
# ---------------------------------------------------------------------------

def analyze_full_github_profile(username: str) -> dict[str, Any]:
    """
    Executes the complete profile-wide evaluation pipeline:
    1. Extracts raw metrics from GraphQL / REST
    2. Calculates normalized 0-100 scores
    3. Generates concise RAG markdown narrative
    """
    raw_metrics = extract_raw_profile_metrics(username)
    score_data = compute_overall_github_score(raw_metrics)
    rag_summary = format_github_profile_rag_summary(username, score_data)

    return {
        "username": username,
        "raw_metrics": raw_metrics,
        "score_data": score_data,
        "rag_summary": rag_summary,
    }


if __name__ == "__main__":
    import json
    test_user = "torvalds"
    print(f"Running Overall GitHub Profile Scoring Engine on @{test_user}...")
    res = analyze_full_github_profile(test_user)
    print("\n--- SCORE DATA ---")
    print(json.dumps(res["score_data"], indent=2))
    print("\n--- RAG SUMMARY ---")
    print(res["rag_summary"])
