"""
code_metrics.py

Step 3.3 — Metric Extraction (PM Plan Step 3.3)

Takes the budget-selected file list from code_retrieval.py's
select_files_within_budget() (or retrieve_repo_code()) plus the clone_dir,
and computes five 0-100 sub-scores + a weighted overall_code_score:

  overall_code_score = 0.25*architecture + 0.2*testing + 0.2*complexity
                      + 0.15*documentation + 0.2*commit_history

Each sub-score function also returns a breakdown dict — these feed the
dashboard directly (Step 10), not just the total.

Caveat worth knowing: commit-history scoring reads `git log` on the LOCAL
clone, which (per Step 3.2) is a shallow clone at depth=50 — so "commit
frequency over repo lifetime" is really "over the last <=50 commits", not
the repo's true full history. This is a deliberate trade-off to avoid an
extra full-history clone or extra GitHub API calls; documented here and in
the returned breakdown via `history_window_commits`.
"""

import os
import re
import subprocess
from datetime import datetime, timezone

try:
    import radon.complexity as radon_cc
except ImportError:
    radon_cc = None

try:
    import lizard
except ImportError:
    lizard = None

# ---------------------------------------------------------------------------
# 3.3.1 — Architecture score
# ---------------------------------------------------------------------------
RECOGNIZED_MODULE_DIRS = {
    "src", "lib", "tests", "test", "api", "models", "components", "services",
    "utils", "controllers", "routes", "views", "app", "core", "config",
    "middleware", "handlers", "schemas", "migrations", "static", "templates",
    "public", "hooks", "store", "pages", "internal", "pkg", "cmd", "domain",
    "repository", "repositories", "helpers",
}
LARGE_FILE_LOC_THRESHOLD = 800
LARGE_FILE_PENALTY_PER_FILE = 5
LARGE_FILE_MAX_TOTAL_PENALTY = 30


def compute_architecture_score(files: list) -> dict:
    """
    ratio of files under a recognizable module folder vs. flat/root-level
    files, scaled to 0-100, minus a penalty for any file over 800 LOC
    (capped so one pathological file can't zero out an otherwise
    well-organized repo).
    """
    if not files:
        return {"score": 0.0, "organized_ratio": 0.0, "large_file_count": 0,
                "large_files": [], "penalty_applied": 0.0}

    organized = 0
    for f in files:
        parts = f["path"].split(os.sep)[:-1]  # directory components only
        if any(p.lower() in RECOGNIZED_MODULE_DIRS for p in parts):
            organized += 1

    ratio = organized / len(files)
    base_score = ratio * 100

    large_files = [f["path"] for f in files if f["loc"] > LARGE_FILE_LOC_THRESHOLD]
    penalty = min(LARGE_FILE_MAX_TOTAL_PENALTY, len(large_files) * LARGE_FILE_PENALTY_PER_FILE)

    score = max(0.0, base_score - penalty)
    return {
        "score": round(score, 2),
        "organized_ratio": round(ratio, 3),
        "large_file_count": len(large_files),
        "large_files": large_files[:10],  # cap for readability
        "penalty_applied": penalty,
    }


# ---------------------------------------------------------------------------
# 3.3.2 — Testing score
# ---------------------------------------------------------------------------
_TEST_FILENAME_RE = re.compile(r"(^|/)(test_[^/]+|[^/]+\.test\.[^/]+|[^/]*spec[^/]*)$", re.I)


def _is_test_file(rel_path: str) -> bool:
    fname = os.path.basename(rel_path)
    return bool(_TEST_FILENAME_RE.search(fname)) or "/test" in rel_path.lower() or "/tests" in rel_path.lower()


def compute_testing_score(files: list) -> dict:
    """
    (test files) / (total source files) * 100. Explicit floor of 0 when
    zero test files exist, regardless of how small total_source_files is
    (guards against a degenerate ratio on a repo with almost no source
    files at all).
    """
    source_files = [f for f in files if f["is_source"]]
    test_files = [f for f in source_files if _is_test_file(f["path"])]

    if not test_files or not source_files:
        return {"score": 0.0, "test_file_count": len(test_files),
                "source_file_count": len(source_files), "ratio": 0.0}

    ratio = len(test_files) / len(source_files)
    score = min(100.0, ratio * 100)
    return {
        "score": round(score, 2),
        "test_file_count": len(test_files),
        "source_file_count": len(source_files),
        "ratio": round(ratio, 3),
    }


# ---------------------------------------------------------------------------
# 3.3.3 — Complexity score (radon for .py, lizard for everything else)
# ---------------------------------------------------------------------------
def _avg_complexity_python(abs_path: str):
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        blocks = radon_cc.cc_visit(source)
    except Exception:
        return None
    if not blocks:
        return None
    return sum(b.complexity for b in blocks) / len(blocks)


def _avg_complexity_lizard(abs_path: str):
    try:
        result = lizard.analyze_file(abs_path)
    except Exception:
        return None
    if not result or not result.function_list:
        return None
    return sum(fn.cyclomatic_complexity for fn in result.function_list) / len(result.function_list)


def compute_complexity_score(files: list) -> dict:
    """
    Per-file average cyclomatic complexity (radon for .py, lizard for other
    recognized source extensions), then averaged across files. Mapped to
    0-100 on an inverted scale: avg complexity <=5 -> 100, >=20 -> 0, linear
    between (lower complexity = higher score).

    Files with zero detected functions (e.g. pure config/constants files)
    are skipped rather than counted as complexity 0 — including them would
    artificially inflate the score for repos that are mostly boilerplate.
    """
    per_file_avgs = []
    analyzed_files = 0
    unanalyzable_files = 0

    for f in files:
        if not f["is_source"]:
            continue
        abs_path = f["absolute_path"]
        if f["extension"] == ".py":
            avg = _avg_complexity_python(abs_path)
        else:
            avg = _avg_complexity_lizard(abs_path)

        if avg is None:
            unanalyzable_files += 1
            continue
        per_file_avgs.append(avg)
        analyzed_files += 1

    if not per_file_avgs:
        return {"score": None, "avg_complexity": None, "analyzed_files": 0,
                "unanalyzable_files": unanalyzable_files,
                "note": "no functions detected in any selected source file"}

    overall_avg = sum(per_file_avgs) / len(per_file_avgs)

    if overall_avg <= 5:
        score = 100.0
    elif overall_avg >= 20:
        score = 0.0
    else:
        score = 100.0 - (overall_avg - 5) / 15.0 * 100.0

    return {
        "score": round(score, 2),
        "avg_complexity": round(overall_avg, 2),
        "analyzed_files": analyzed_files,
        "unanalyzable_files": unanalyzable_files,
    }


# ---------------------------------------------------------------------------
# 3.3.4 — Documentation score
# ---------------------------------------------------------------------------
COMMENT_MARKERS = {
    ".py": "#", ".sh": "#", ".rb": "#", ".pl": "#", ".r": "#",
    ".js": "//", ".jsx": "//", ".ts": "//", ".tsx": "//", ".java": "//",
    ".c": "//", ".cpp": "//", ".cc": "//", ".h": "//", ".hpp": "//",
    ".cs": "//", ".go": "//", ".rs": "//", ".swift": "//", ".kt": "//",
    ".kts": "//", ".scala": "//", ".dart": "//",
}
# heuristic multiplier: a repo with ~30%+ comment-line density is already
# very well documented, so ratios are scaled up rather than requiring an
# unrealistic 100% comment density to earn full credit
_COMMENT_RATIO_SCALE = 3.0

README_NAMES = ("readme.md", "readme.rst", "readme.txt", "readme")


def _count_comment_lines(abs_path: str, ext: str) -> int:
    marker = COMMENT_MARKERS.get(ext)
    count = 0
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return 0

    in_py_docstring = False
    for line in lines:
        stripped = line.strip()
        if ext == ".py":
            # approximate docstring tracking: toggles on each triple-quote
            # occurrence — not a full parser, but catches the common case
            # of a docstring opened and closed on its own lines
            triple_count = stripped.count('"""') + stripped.count("'''")
            if in_py_docstring:
                count += 1
                if triple_count % 2 == 1:
                    in_py_docstring = False
                continue
            if triple_count % 2 == 1:
                in_py_docstring = True
                count += 1
                continue
        if marker and stripped.startswith(marker):
            count += 1
    return count


def _find_readme(clone_dir: str):
    try:
        entries = os.listdir(clone_dir)
    except OSError:
        return None
    for entry in entries:
        if entry.lower() in README_NAMES:
            return os.path.join(clone_dir, entry)
    return None


def _score_readme_completeness(readme_path: str) -> dict:
    if not readme_path or not os.path.isfile(readme_path):
        return {"score": 0.0, "has_readme": False, "has_description": False,
                "has_setup_instructions": False, "has_usage_examples": False}
    try:
        with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return {"score": 0.0, "has_readme": False, "has_description": False,
                "has_setup_instructions": False, "has_usage_examples": False}

    low = content.lower()
    has_description = len(content.strip()) > 100
    has_setup = bool(re.search(r"\b(install|setup|getting started|requirements)\b", low))
    has_usage = bool(re.search(r"\b(usage|example|```)\b", low))

    # 25 pts just for existing, 25 each for description/setup/usage
    score = 25.0
    score += 25.0 if has_description else 0.0
    score += 25.0 if has_setup else 0.0
    score += 25.0 if has_usage else 0.0

    return {
        "score": score,
        "has_readme": True,
        "has_description": has_description,
        "has_setup_instructions": has_setup,
        "has_usage_examples": has_usage,
    }


def compute_documentation_score(files: list, clone_dir: str) -> dict:
    """
    0.5 * comment-density score + 0.5 * README-completeness score.
    """
    total_lines = 0
    comment_lines = 0
    for f in files:
        if not f["is_source"]:
            continue
        total_lines += f["loc"]
        comment_lines += _count_comment_lines(f["absolute_path"], f["extension"])

    comment_ratio = (comment_lines / total_lines) if total_lines else 0.0
    comment_score = min(100.0, comment_ratio * 100 * _COMMENT_RATIO_SCALE)

    readme_path = _find_readme(clone_dir)
    readme_result = _score_readme_completeness(readme_path)

    overall = 0.5 * comment_score + 0.5 * readme_result["score"]

    return {
        "score": round(overall, 2),
        "comment_line_ratio": round(comment_ratio, 4),
        "comment_score": round(comment_score, 2),
        "readme": readme_result,
    }


# ---------------------------------------------------------------------------
# 3.3.5 — Commit history score
# ---------------------------------------------------------------------------
_FREQUENCY_COMMITS_PER_DAY_FOR_100 = 0.2  # ~1 commit every 5 days -> full credit
_RECENCY_DECAY_DAYS = 365
_MSG_LEN_FOR_0 = 10
_MSG_LEN_FOR_100 = 50


def _git_log(clone_dir: str):
    try:
        result = subprocess.run(
            ["git", "-C", clone_dir, "log", "--pretty=format:%H|%aI|%s"],
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        sha, date_str, subject = parts
        try:
            commit_date = datetime.fromisoformat(date_str)
        except ValueError:
            continue
        commits.append({"sha": sha, "date": commit_date, "subject": subject})
    return commits


def compute_commit_history_score(clone_dir: str) -> dict:
    """
    40% commit frequency (commits/day over the visible window) + 30%
    recency of last commit + 30% avg commit-message subject length, each
    scaled 0-100, weighted-summed.

    See module docstring: this reads the LOCAL shallow clone (depth=50 from
    Step 3.2), so "frequency" is over at most the last 50 commits, not the
    repo's true full lifetime.
    """
    commits = _git_log(clone_dir)
    if not commits:
        return {"score": 0.0, "commit_count": 0, "history_window_commits": 0,
                "frequency_score": 0.0, "recency_score": 0.0, "message_quality_score": 0.0}

    commits.sort(key=lambda c: c["date"])
    first_date = commits[0]["date"]
    last_date = commits[-1]["date"]
    now = datetime.now(timezone.utc)

    if len(commits) < 2:
        # frequency is undefined with a single data point — scoring it 100
        # (an artifact of flooring span_days to 1.0) would misleadingly
        # reward a one-off single commit as if it were sustained activity
        frequency_score = 0.0
        commits_per_day = 0.0
    else:
        span_days = max(1.0, (last_date - first_date).total_seconds() / 86400.0)
        commits_per_day = len(commits) / span_days
        frequency_score = min(100.0, (commits_per_day / _FREQUENCY_COMMITS_PER_DAY_FOR_100) * 100.0)

    days_since_last = max(0.0, (now - last_date).total_seconds() / 86400.0)
    recency_score = max(0.0, 100.0 - (days_since_last / _RECENCY_DECAY_DAYS) * 100.0)

    avg_msg_len = sum(len(c["subject"]) for c in commits) / len(commits)
    if avg_msg_len <= _MSG_LEN_FOR_0:
        message_quality_score = 0.0
    elif avg_msg_len >= _MSG_LEN_FOR_100:
        message_quality_score = 100.0
    else:
        message_quality_score = (avg_msg_len - _MSG_LEN_FOR_0) / (_MSG_LEN_FOR_100 - _MSG_LEN_FOR_0) * 100.0

    overall = 0.4 * frequency_score + 0.3 * recency_score + 0.3 * message_quality_score

    return {
        "score": round(overall, 2),
        "commit_count": len(commits),
        "history_window_commits": len(commits),
        "commits_per_day": round(commits_per_day, 3),
        "days_since_last_commit": round(days_since_last, 1),
        "avg_commit_message_length": round(avg_msg_len, 1),
        "frequency_score": round(frequency_score, 2),
        "recency_score": round(recency_score, 2),
        "message_quality_score": round(message_quality_score, 2),
    }


# ---------------------------------------------------------------------------
# 3.3 combined: overall_code_score
# ---------------------------------------------------------------------------
WEIGHTS = {
    "architecture": 0.25,
    "testing": 0.20,
    "complexity": 0.20,
    "documentation": 0.15,
    "commit_history": 0.20,
}


def compute_repo_metrics(files: list, clone_dir: str) -> dict:
    """
    Runs all five sub-score computations and combines them into
    overall_code_score. If complexity couldn't be computed at all (no
    functions detected in any file — e.g. a pure-config or pure-markup
    repo), it's excluded from the weighted average and the remaining
    weights are renormalized, rather than silently treating it as 0 (which
    would unfairly punish a repo for having no functions to analyze).
    """
    architecture = compute_architecture_score(files)
    testing = compute_testing_score(files)
    complexity = compute_complexity_score(files)
    documentation = compute_documentation_score(files, clone_dir)
    commit_history = compute_commit_history_score(clone_dir)

    sub_scores = {
        "architecture": architecture["score"],
        "testing": testing["score"],
        "complexity": complexity["score"],
        "documentation": documentation["score"],
        "commit_history": commit_history["score"],
    }

    usable_weights = {k: WEIGHTS[k] for k, v in sub_scores.items() if v is not None}
    weight_sum = sum(usable_weights.values()) or 1.0
    overall = sum(sub_scores[k] * (usable_weights[k] / weight_sum) for k in usable_weights)

    return {
        "overall_code_score": round(overall, 2),
        "sub_scores": sub_scores,
        "breakdown": {
            "architecture": architecture,
            "testing": testing,
            "complexity": complexity,
            "documentation": documentation,
            "commit_history": commit_history,
        },
        "weights_used": usable_weights,
    }


if __name__ == "__main__":
    import json
    from code_retrieval import retrieve_repo_code, cleanup_clone

    result = retrieve_repo_code("https://github.com/pallets/flask.git", depth=50)
    metrics = compute_repo_metrics(result["files"], result["clone_dir"])
    print(json.dumps(metrics, indent=2, default=str))
    cleanup_clone(result["clone_dir"])