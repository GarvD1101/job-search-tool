import os
import re
import sys
from pathlib import Path

# Paths to ignore during scanning
IGNORED_DIRS = {
    ".git",
    ".venv",
    ".private",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    "cache",
    ".cache",
    "data/cache",
}

# Regex patterns for credential detection
SECRET_PATTERNS = [
    ("Groq API Key", re.compile(r"gsk_[a-zA-Z0-9]{20,}")),
    ("Private Key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "Database Connection URL with Password",
        re.compile(r"postgres(?:ql)?://[^:\s]+:[^@\s]+@[^/\s]+"),
    ),
    (
        "Hardcoded Env Key Assignment",
        re.compile(
            r"(?:JOOBLE_API_KEY|GROQ_API_KEY|SUPABASE_DB_URL)\s*=\s*['\"][a-zA-Z0-9_\-:/.@]{8,}['\"]"
        ),
    ),
    ("Generic Bearer Token", re.compile(r"Bearer\s+ey[a-zA-Z0-9_\-\.]{20,}")),
    ("JWT Secret / Service Role Key", re.compile(r"eyJhbGciOi[a-zA-Z0-9_\-\.]{30,}")),
]


def is_ignored(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return False
    return any(part in IGNORED_DIRS for part in rel_parts)


def check_file(path: Path) -> list[str]:
    findings = []
    # Skip binary or very large files
    if path.stat().st_size > 1_000_000:
        return findings

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        # Skip comment or example placeholders like FOO= or empty values
        stripped = line.strip()
        if not stripped:
            continue

        for pattern_name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                # Ensure we do not print the secret itself
                findings.append(f"{path}:{line_idx} - {pattern_name}")

    return findings


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    all_findings = []

    # Check for presence of real .env file in repo
    env_file = root / ".env"
    if env_file.exists():
        all_findings.append(
            ".env file is present on disk. Ensure .env is never committed to git."
        )

    for dirpath, dirnames, filenames in os.walk(root):
        # Mutate dirnames in place to skip ignored dirs
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            if is_ignored(fpath, root):
                continue

            findings = check_file(fpath)
            all_findings.extend(findings)

    if all_findings:
        print("Secret check FAILED. The following potential secrets were detected:")
        for finding in all_findings:
            print(f"  {finding}")
        print("Remove any detected secrets before pushing.")
        return 1

    print("Secret check PASSED: No secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
