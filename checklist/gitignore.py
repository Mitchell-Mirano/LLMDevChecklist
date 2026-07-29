"""Parser for .gitignore files to automatically exclude ignored paths in audit checks."""

import fnmatch
from pathlib import Path


class GitIgnoreFilter:
    """Parses .gitignore patterns and checks if paths match any ignore rule."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.patterns = []
        
        # Default fallback ignore patterns if no .gitignore exists
        self.patterns.extend([
            ".git", ".venv", "venv", "node_modules", "dist", "site", "__pycache__", "*.pyc", "mongo-data"
        ])

        gitignore_path = self.root_dir / ".gitignore"
        if gitignore_path.exists():
            for line in gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    pattern = stripped.rstrip("/")
                    if pattern not in self.patterns:
                        self.patterns.append(pattern)

    def is_ignored(self, path: Path) -> bool:
        """Checks if a given path matches any .gitignore pattern."""
        try:
            rel_path = path.resolve().relative_to(self.root_dir)
        except ValueError:
            return False

        rel_str = str(rel_path)
        parts = rel_path.parts

        for pattern in self.patterns:
            if fnmatch.fnmatch(rel_str, pattern) or any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True
        return False
