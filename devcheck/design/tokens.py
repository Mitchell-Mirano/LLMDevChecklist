"""CSS Custom Properties (design tokens) discovery, parsing, and resolution."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from .contrast import parse_color

DEFAULT_TOKEN_FILENAMES = (
    "main.css",
    "style.css",
    "styles.css",
    "base.css",
    "tokens.css",
    "variables.css",
    "globals.css",
    "theme.css",
)

_SEARCH_PREFIXES = (
    "src/assets",
    "src/styles",
    "src/css",
    "src",
    "frontend/src/assets",
    "frontend/src/styles",
    "frontend/src",
    "styles",
    "assets",
    "app",
)

_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]+)\}", re.DOTALL)
_VAR_DECL_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
_VAR_REF_RE = re.compile(r"var\(\s*(--[\w-]+)(?:\s*,[^)]+)?\s*\)")

_FG_KEYWORDS = ("text", "fg", "foreground", "primary", "secondary", "accent", "error", "danger", "warning", "success", "info", "subtle", "muted")
_BG_KEYWORDS = ("bg", "background", "surface", "card", "panel", "canvas")


def discover_tokens_files(root_dir: Path, ignore_filter=None) -> List[Path]:
    """Auto-discover CSS token files in common frontend locations."""
    found: List[Path] = []
    seen: Set[Path] = set()

    for prefix in _SEARCH_PREFIXES:
        base = root_dir / prefix
        if not base.is_dir():
            continue
        for fname in DEFAULT_TOKEN_FILENAMES:
            candidate = (base / fname).resolve()
            if candidate.is_file() and candidate not in seen:
                if ignore_filter and ignore_filter.is_ignored(candidate):
                    continue
                seen.add(candidate)
                found.append(candidate)

    return found


def _classify_selector(selector: str) -> Optional[str]:
    sel = selector.strip().lower()
    if ":root" in sel or sel == "html":
        return "default"
    theme_m = re.search(r'\[data-theme=["\']?([\w-]+)["\']?\]', sel)
    if theme_m:
        return theme_m.group(1)
    if ".dark" in sel:
        return "dark"
    if ".light" in sel:
        return "light"
    return None


def parse_css_tokens(token_paths: List[Path]) -> Dict[str, Dict[str, str]]:
    """Parse CSS custom properties grouped by theme ('default', 'dark', etc.)."""
    themes: Dict[str, Dict[str, str]] = {"default": {}}

    for path in token_paths:
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        cleaned = _CSS_COMMENT_RE.sub("", raw)
        for selector, body in _BLOCK_RE.findall(cleaned):
            theme_name = _classify_selector(selector)
            if not theme_name:
                continue
            bucket = themes.setdefault(theme_name, {})
            for var_name, val in _VAR_DECL_RE.findall(body):
                bucket[var_name.strip()] = val.strip()

    return themes


def resolve_token_value(
    var_name: str,
    theme_tokens: Dict[str, str],
    default_tokens: Dict[str, str],
    _visited: Optional[Set[str]] = None,
) -> Optional[str]:
    """Resolve a CSS variable value, following chained var(--other) references."""
    visited = _visited or set()
    if var_name in visited:
        return None
    visited.add(var_name)

    raw = theme_tokens.get(var_name) or default_tokens.get(var_name)
    if raw is None:
        return None

    m = _VAR_REF_RE.fullmatch(raw.strip())
    if m:
        return resolve_token_value(m.group(1), theme_tokens, default_tokens, visited)

    return raw.strip()


def infer_contrast_pairs(
    theme_tokens: Dict[str, str],
    default_tokens: Dict[str, str],
) -> List[Tuple[str, str]]:
    """Infer semantic (foreground, background) token pairs that resolve to valid colors."""
    merged = {**default_tokens, **theme_tokens}
    color_tokens: List[str] = []

    for name in merged:
        resolved = resolve_token_value(name, theme_tokens, default_tokens)
        if resolved and parse_color(resolved) is not None:
            color_tokens.append(name)

    bgs = [t for t in color_tokens if any(k in t.lower() for k in _BG_KEYWORDS)]
    fgs = [t for t in color_tokens if t not in bgs and any(k in t.lower() for k in _FG_KEYWORDS)]

    pairs: List[Tuple[str, str]] = []
    for bg in bgs[:3]:
        for fg in fgs:
            pairs.append((fg, bg))

    return pairs


def find_duplicate_color_tokens(token_paths: List[Path], root_dir: Path) -> Dict[str, List[dict]]:
    """Find CSS variables in the same theme that have different names but identical colors."""
    duplicates_by_file: Dict[str, List[dict]] = {}
    themes = parse_css_tokens(token_paths)
    default_tokens = themes.get("default", {})

    # Map (theme, var_name) -> (rel_path, line_no)
    locations: Dict[Tuple[str, str], Tuple[str, int]] = {}
    for path in token_paths:
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        rel_path = str(path.relative_to(root_dir) if root_dir in path.parents else path)
        current_theme: Optional[str] = None
        brace_depth = 0
        for line_no, line in enumerate(lines, start=1):
            if "{" in line and current_theme is None:
                sel = line.split("{", 1)[0]
                t = _classify_selector(sel)
                if t:
                    current_theme = t
                    brace_depth = line.count("{") - line.count("}")
                    continue
            if current_theme is not None:
                brace_depth += line.count("{") - line.count("}")
                m = _VAR_DECL_RE.search(line)
                if m:
                    locations.setdefault((current_theme, m.group(1).strip()), (rel_path, line_no))
                if brace_depth <= 0:
                    current_theme = None
                    brace_depth = 0

    for theme_name, theme_tokens in themes.items():
        color_groups: Dict[Tuple[int, int, int, float], List[str]] = {}
        for var_name in theme_tokens:
            resolved = resolve_token_value(var_name, theme_tokens, default_tokens)
            if not resolved:
                continue
            rgba = parse_color(resolved)
            if rgba is None:
                continue
            canonical = (rgba[0], rgba[1], rgba[2], round(rgba[3], 4))
            color_groups.setdefault(canonical, []).append(var_name)

        for canonical, var_names in color_groups.items():
            if len(var_names) < 2:
                continue
            primary_var = var_names[0]
            for dup_var in var_names[1:]:
                loc = locations.get((theme_name, dup_var))
                if not loc:
                    continue
                rel_path, line_no = loc
                duplicates_by_file.setdefault(rel_path, []).append({
                    "line_no": line_no,
                    "rule": "duplicate-color-token",
                    "matched": f"{dup_var} == {primary_var}",
                    "message": (
                        f"Token `{dup_var}` in `{theme_name}` duplicates the exact color of "
                        f"`{primary_var}` ({theme_tokens[dup_var]})."
                    ),
                })

    return duplicates_by_file
