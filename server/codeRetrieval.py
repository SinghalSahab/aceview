"""
code_retrieval.py

Step 3.2 — Code Retrieval (PM Plan Step 3.2)

1. Shallow-clone (depth=50) a repo into a temp directory instead of a full
   clone, to keep runtime bounded.
2. Walk the cloned tree and select files within a fixed budget — max 300
   files / 20,000 LOC total — skipping binary files, node_modules, vendor,
   and generated/build directories, so Step 3.3's metric extraction runs
   against a bounded, source-relevant file set rather than scanning
   everything in the repo.
"""

import os
import shutil
import subprocess
import tempfile

MAX_FILES = 300
MAX_TOTAL_LOC = 20_000
CLONE_DEPTH = 50
CLONE_TIMEOUT_SECONDS = 120

SKIP_DIR_NAMES = {
    "node_modules", "vendor", ".git", "dist", "build", "out", "target",
    "__pycache__", ".venv", "venv", "env", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", "bin", "obj", ".idea", ".vscode",
    ".tox", "egg-info", ".eggs", "site-packages",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll", ".so",
    ".dylib", ".class", ".jar", ".war", ".pyc", ".pyo", ".woff", ".woff2",
    ".ttf", ".eot", ".otf", ".mp3", ".mp4", ".mov", ".avi", ".wasm",
    ".bin", ".db", ".sqlite", ".sqlite3", ".lock",
}

# Common source-code extensions — used to prioritize which files stay
# within budget when a repo has more content than the budget allows (real
# source files are kept over config/misc text files), not to filter files
# out outright.
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php",
    ".c", ".cpp", ".cc", ".h", ".hpp", ".cs", ".rs", ".swift", ".kt",
    ".kts", ".scala", ".m", ".mm", ".sh", ".sql", ".html", ".css", ".scss",
    ".vue", ".dart", ".r", ".pl", ".lua",
}


# ---------------------------------------------------------------------------
# 3.2.1 — Shallow clone
# ---------------------------------------------------------------------------
def shallow_clone(clone_url: str, depth: int = CLONE_DEPTH) -> str:
    """
    Clones `clone_url` (e.g. repo['clone_url'] from the GitHub API response
    in github_discovery.py) into a fresh temp directory with
    --depth={depth} --single-branch, and returns the directory path.

    depth=50 (rather than a full clone) keeps clone time roughly constant
    regardless of a repo's total commit history length — needed since Step
    3.3's commit-history scoring only looks at recent activity anyway, not
    the full history.

    Caller is responsible for cleanup via cleanup_clone() once analysis is
    done, so temp directories don't accumulate across many candidates.
    """
    dest = tempfile.mkdtemp(prefix="repo_clone_")
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", str(depth), "--single-branch", clone_url, dest],
            capture_output=True, text=True, timeout=CLONE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        raise RuntimeError(f"git clone timed out after {CLONE_TIMEOUT_SECONDS}s for {clone_url}")

    if result.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise RuntimeError(f"git clone failed for {clone_url}: {result.stderr.strip()}")

    return dest


def cleanup_clone(clone_dir: str):
    """Remove a cloned repo's temp directory. Safe to call even if it's already gone."""
    shutil.rmtree(clone_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 3.2.2 — File/LOC budget enforcement
# ---------------------------------------------------------------------------
def _is_binary_extension(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in BINARY_EXTENSIONS


def _count_loc(file_path: str):
    """
    Returns an int line count, or None if the file isn't text-decodable
    (treated as binary regardless of extension — catches binaries that
    don't have a recognized extension).
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as f:
            return sum(1 for _ in f)
    except (UnicodeDecodeError, OSError):
        return None


def _walk_candidate_files(clone_dir: str):
    """
    Walks the cloned tree, pruning SKIP_DIR_NAMES in place (so os.walk
    never even descends into node_modules/vendor/etc — cheaper than
    filtering after the fact on a large repo), and yields (abs_path,
    rel_path) for every file not excluded by extension.
    """
    for root, dirnames, filenames in os.walk(clone_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".git")]
        for fname in filenames:
            abs_path = os.path.join(root, fname)
            if _is_binary_extension(abs_path):
                continue
            rel_path = os.path.relpath(abs_path, clone_dir)
            yield abs_path, rel_path


def select_files_within_budget(clone_dir: str, max_files: int = MAX_FILES,
                                max_total_loc: int = MAX_TOTAL_LOC) -> dict:
    """
    Selects files within the (max_files, max_total_loc) budget.

    Selection order prioritizes recognized source-code extensions over
    other text files (e.g. a stray .txt or .md deep in the tree won't push
    out an actual .py/.js file), then sorts by path depth then alphabetical
    for determinism.

    A candidate file is skipped entirely (not truncated) if adding its full
    LOC would exceed the remaining LOC budget — truncating mid-file would
    corrupt Step 3.3's complexity/architecture analysis (e.g. a cyclomatic
    complexity scan needs complete functions, not a file cut off partway
    through one), so a file that doesn't fit is deferred rather than
    partially included. This means a handful of very large files can use up
    the budget while leaving many small files unselected — see
    `skipped_over_budget` in the returned stats if that matters for a given
    repo.

    Returns:
      {
        "files": [{"path": rel_path, "absolute_path": abs_path,
                    "extension": str, "loc": int, "is_source": bool}, ...],
        "total_files_considered": int,   # after binary/skip-dir filtering
        "total_files_selected": int,
        "total_loc_selected": int,
        "skipped_binary_or_undecodable": int,
        "skipped_over_budget": int,
      }
    """
    candidates = []
    skipped_binary = 0

    for abs_path, rel_path in _walk_candidate_files(clone_dir):
        loc = _count_loc(abs_path)
        if loc is None:
            skipped_binary += 1
            continue
        ext = os.path.splitext(rel_path)[1].lower()
        candidates.append({
            "path": rel_path,
            "absolute_path": abs_path,
            "extension": ext,
            "loc": loc,
            "is_source": ext in SOURCE_EXTENSIONS,
        })

    total_considered = len(candidates)

    # source files first, then shallower paths first, then alphabetical —
    # gives a deterministic, sensible priority order for budget trimming
    candidates.sort(key=lambda f: (0 if f["is_source"] else 1, f["path"].count(os.sep), f["path"]))

    selected = []
    total_loc = 0
    skipped_over_budget = 0

    for f in candidates:
        if len(selected) >= max_files:
            skipped_over_budget += 1
            continue
        if total_loc + f["loc"] > max_total_loc:
            skipped_over_budget += 1
            continue
        selected.append(f)
        total_loc += f["loc"]

    return {
        "files": selected,
        "total_files_considered": total_considered,
        "total_files_selected": len(selected),
        "total_loc_selected": total_loc,
        "skipped_binary_or_undecodable": skipped_binary,
        "skipped_over_budget": skipped_over_budget,
    }


# ---------------------------------------------------------------------------
# 3.2 full pipeline for a single repo
# ---------------------------------------------------------------------------
def retrieve_repo_code(clone_url: str, depth: int = CLONE_DEPTH,
                        max_files: int = MAX_FILES, max_total_loc: int = MAX_TOTAL_LOC) -> dict:
    """
    Full Step 3.2 pipeline for one repo: shallow clone -> select files
    within budget. Returns the budget dict from select_files_within_budget
    plus "clone_dir" (needed by Step 3.3, and must be passed to
    cleanup_clone() once that analysis is done).
    """
    clone_dir = shallow_clone(clone_url, depth=depth)
    try:
        result = select_files_within_budget(clone_dir, max_files=max_files, max_total_loc=max_total_loc)
    except Exception:
        cleanup_clone(clone_dir)
        raise
    result["clone_dir"] = clone_dir
    return result


if __name__ == "__main__":
    # Live smoke test against a small, well-known public repo — no GitHub
    # API call involved here (git clone over https isn't subject to the
    # REST API's 60/hr unauthenticated rate limit), so this works even
    # while github_discovery.py's API calls are rate-limited.
    result = retrieve_repo_code("https://github.com/octocat/Hello-World.git")
    print(f"Cloned to: {result['clone_dir']}")
    print(f"Files considered: {result['total_files_considered']}")
    print(f"Files selected:   {result['total_files_selected']}")
    print(f"Total LOC:        {result['total_loc_selected']}")
    print(f"Skipped (binary): {result['skipped_binary_or_undecodable']}")
    print(f"Skipped (budget): {result['skipped_over_budget']}")
    for f in result["files"][:10]:
        print(f"  {f['path']:40s} loc={f['loc']:5d} source={f['is_source']}")
    cleanup_clone(result["clone_dir"])
    print("Cleaned up temp clone dir.")