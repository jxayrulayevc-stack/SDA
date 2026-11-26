"""Block obvious secrets in staged files (or in the whole tree with --all).

The script prints only file names, line numbers and pattern names.
It never prints the matched value itself.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BLOCKED_FILENAME_RE = re.compile(
    r"(?i)(^|\/)\.env$|\.env$|\.db$|\.sqlite\d*$|\.mafile$|\.key$|\.pem$"
)

PATTERNS: dict[str, re.Pattern[str]] = {
    "telegram_bot_token": re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    "mafile_secret_value": re.compile(
        r"(?i)\b(?:shared_secret|identity_secret|revocation_code|secret_1)\b\s*[:=]\s*"
        r"[\"']?[A-Za-z0-9+/=_-]{32,}"
    ),
    "env_secret_value": re.compile(
        r"(?i)\b(?:BOT_TOKEN|ENCRYPTION_KEY)\b\s*=\s*[\"']?[A-Za-z0-9_+/=.-]{20,}"
    ),
    "fernet_key": re.compile(
        r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43}=(?![A-Za-z0-9_-])"
    ),
}

Finding = tuple[str, int | None, str]


def _git_files(*args: str) -> list[str]:
    output = subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def collect_paths(all_files: bool) -> list[Path]:
    if all_files:
        try:
            names = _git_files("ls-files", "--cached", "--others", "--exclude-standard")
        except (subprocess.CalledProcessError, FileNotFoundError):
            names = [
                path.relative_to(ROOT).as_posix()
                for path in ROOT.rglob("*")
                if path.is_file()
                and not any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in path.parts)
            ]
    else:
        try:
            names = _git_files("diff", "--cached", "--name-only", "--diff-filter=ACM")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError("Not a git repository; run with --all for a manual scan") from exc
    return [ROOT / name for name in names]


def scan_path(path: Path) -> list[Finding]:
    """Scan a single file; returns (display path, line number or None, label)."""
    display = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    findings: list[Finding] = []

    if BLOCKED_FILENAME_RE.search(path.name) or display.startswith(("data/", "logs/")):
        findings.append((display, None, "forbidden filename"))

    if not path.is_file():
        return findings
    data = path.read_bytes()
    if b"\x00" in data:  # binary files are not scanned
        return findings
    text = data.decode("utf-8", errors="replace")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((display, line_number, label))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="scan the whole worktree")
    args = parser.parse_args(argv)

    try:
        paths = collect_paths(args.all)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    for path in paths:
        findings.extend(scan_path(path))

    if findings:
        print(f"Potential secrets found ({len(findings)}):", file=sys.stderr)
        for name, line_number, label in findings:
            location = f"{name}:{line_number}" if line_number else name
            print(f"  {location} -> {label}", file=sys.stderr)
        print("Commit blocked. Remove the secrets and regenerate exposed credentials.", file=sys.stderr)
        return 1

    print(f"OK: no secret patterns found in {len(paths)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
