#!/usr/bin/env python3
"""Module to scan codebase for hardcoded secrets, internal IP addresses, local absolute paths, and credentials."""

import re
import sys
from pathlib import Path
from typing import Optional, List, Dict
from .gitignore import GitIgnoreFilter

PATTERNS = {
    "Local absolute path": re.compile(r'(?i)["\']/(?:home|Users|var/www|C:|[a-zA-Z]:\\)[^"\']+["\']'),
    "Hardcoded IP address": re.compile(r'\b(?:127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'),
    "Potential Secret / Token": re.compile(r'(?i)(?:api[_-]?key|secret[_-]?key|password|jwt[_-]?secret)\s*=\s*["\'][^"\']{8,}["\']'),
    "Hardcoded Private Key": re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----')
}

ALLOWLIST_PATTERNS = [
    re.compile(r'127\.0\.0\.1:27017'), # standard local mongo default fallback in config
    re.compile(r'os\.path|Path\(|Path\.cwd\('),
]


def is_allowed(line: str) -> bool:
    return any(pattern.search(line) for pattern in ALLOWLIST_PATTERNS)


def scan_file(filepath: Path) -> List[dict]:
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return issues

    for i, line in enumerate(content.splitlines(), start=1):
        if is_allowed(line):
            continue

        for issue_type, regex in PATTERNS.items():
            match = regex.search(line)
            if match:
                issues.append({
                    "line_no": i,
                    "type": issue_type,
                    "matched": match.group(0),
                    "line": line.strip()[:100]
                })

    return issues


def check_hardcoded(
    target_dirs: Optional[List[str]] = None,
    ignore_filter: Optional[GitIgnoreFilter] = None,
    root_dir: Optional[Path] = None
) -> dict:
    root = (root_dir or Path.cwd()).resolve()
    if ignore_filter is None:
        ignore_filter = GitIgnoreFilter(root)

    if not target_dirs:
        candidates = [root / "backend", root / "frontend" / "src", root / "src", root / "app"]
        target_dirs = [str(c) for c in candidates if c.exists()] or [str(root)]

    total_files = 0
    issues_by_file: Dict[str, list] = {}

    for target in target_dirs:
        path = Path(target)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue

        files = [path] if path.is_file() else path.glob("**/*")
        for filepath in files:
            if filepath.is_dir() or ignore_filter.is_ignored(filepath):
                continue
            if filepath.suffix not in (".py", ".vue", ".ts", ".js", ".json", ".env.example", ".md"):
                continue

            total_files += 1
            file_issues = scan_file(filepath)
            if file_issues:
                rel_path = str(filepath.relative_to(root) if root in filepath.parents else filepath)
                issues_by_file[rel_path] = file_issues

    total_issues = sum(len(v) for v in issues_by_file.values())
    return {
        "total_files": total_files,
        "flagged_files_count": len(issues_by_file),
        "total_issues": total_issues,
        "issues_by_file": issues_by_file
    }


def main():
    args = sys.argv[1:]
    res = check_hardcoded(target_dirs=args)
    print("🔍 Scanning codebase for hardcoded variables, secrets, URLs, and paths...\n")
    for file_path, issues in res["issues_by_file"].items():
        print(f"📁 \033[1m{file_path}\033[0m")
        for issue in issues:
            print(f"   Line {issue['line_no']} [{issue['type']}]: {issue['matched']}")
        print()

    print(f"Summary: Found {res['total_issues']} potential hardcoded issue(s) across {res['flagged_files_count']} file(s).")


if __name__ == "__main__":
    main()
