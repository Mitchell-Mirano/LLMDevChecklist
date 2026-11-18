"""Main orchestrator for the scalable multi-project Design System Auditor."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from ..gitignore import GitIgnoreFilter
from .contrast import contrast_ratio, evaluate_contrast
from .scanners import scan_design_file
from .tokens import (
    discover_tokens_files,
    find_duplicate_color_tokens,
    infer_contrast_pairs,
    parse_css_tokens,
    resolve_token_value,
)

DEFAULT_EXTENSIONS = (".vue", ".css", ".scss", ".tsx", ".jsx", ".svelte", ".html")

DEFAULT_RULES = {
    "hardcoded_colors": True,
    "undefined_tokens": True,
    "duplicate_tokens": True,
    "contrast": True,
    "unicode_icons": True,
    "svg_viewbox": True,
    "inline_styles": True,
    "important": True,
    "hardcoded_font": True,
    "z_index_magic": True,
    "a11y_basic": True,
}


def _resolve_token_paths(
    root: Path,
    configured_tokens: Optional[List[str]],
    ignore_filter: GitIgnoreFilter,
) -> List[Path]:
    if configured_tokens:
        paths: List[Path] = []
        for raw in configured_tokens:
            p = Path(raw)
            if not p.is_absolute():
                p = root / p
            if p.is_file():
                paths.append(p.resolve())
        return paths
    return discover_tokens_files(root, ignore_filter=ignore_filter)


def _audit_contrast(
    themes: Dict[str, Dict[str, str]],
    configured_pairs: Optional[List[List[str]]],
    min_aa: float,
    min_large: float,
) -> dict:
    default_tokens = themes.get("default", {})
    checked_pairs: List[dict] = []
    failures_count = 0

    for theme_name, theme_tokens in themes.items():
        if not theme_tokens and theme_name != "default":
            continue

        if configured_pairs:
            pairs: List[Tuple[str, str]] = [
                (p[0], p[1]) for p in configured_pairs if isinstance(p, (list, tuple)) and len(p) == 2
            ]
        else:
            pairs = infer_contrast_pairs(theme_tokens, default_tokens)

        for fg_var, bg_var in pairs:
            fg_val = resolve_token_value(fg_var, theme_tokens, default_tokens)
            bg_val = resolve_token_value(bg_var, theme_tokens, default_tokens)
            if not fg_val or not bg_val:
                continue
            cr = contrast_ratio(fg_val, bg_val)
            if cr is None:
                continue
            ev = evaluate_contrast(cr, min_aa=min_aa, min_large=min_large)
            if ev["status"] == "FAIL":
                failures_count += 1
            checked_pairs.append({
                "theme": theme_name,
                "fg_token": fg_var,
                "bg_token": bg_var,
                "fg_value": fg_val,
                "bg_value": bg_val,
                **ev,
            })

    return {
        "checked_pairs": checked_pairs,
        "failures_count": failures_count,
    }


def check_design(
    target_dirs: Optional[List[str]] = None,
    ignore_filter: Optional[GitIgnoreFilter] = None,
    root_dir: Optional[Path] = None,
    design_cfg: Optional[Dict[str, Any]] = None,
) -> dict:
    """Audit frontend files for design token compliance, WCAG contrast, SVG icons, and a11y."""
    root = (root_dir or Path.cwd()).resolve()
    if ignore_filter is None:
        ignore_filter = GitIgnoreFilter(root)

    cfg = design_cfg or {}
    extensions = tuple(e.lower() for e in cfg.get("extensions", DEFAULT_EXTENSIONS))
    rules_cfg = {**DEFAULT_RULES, **cfg.get("rules", {})}
    allowed_unicode: Set[str] = set(cfg.get("allowed_unicode", []))
    max_z_index = int(cfg.get("max_z_index", 100))
    min_aa = float(cfg.get("min_contrast_aa", 4.5))
    min_large = float(cfg.get("min_contrast_large", 3.0))

    if not target_dirs:
        candidates = [root / "frontend" / "src", root / "src", root / "app"]
        target_dirs = [str(c) for c in candidates if c.exists()] or [str(root)]

    token_paths = _resolve_token_paths(root, cfg.get("tokens_files"), ignore_filter)
    token_path_set = set(token_paths)
    themes = parse_css_tokens(token_paths)

    defined_tokens: Set[str] = set()
    for t_map in themes.values():
        defined_tokens.update(t_map.keys())

    contrast_res = (
        _audit_contrast(themes, cfg.get("contrast_pairs"), min_aa, min_large)
        if rules_cfg.get("contrast", True)
        else {"checked_pairs": [], "failures_count": 0}
    )

    total_files = 0
    total_css_vars = 0
    total_hardcoded_colors = 0
    total_unicode_icons = 0
    total_undefined_tokens = 0
    issues_by_file: Dict[str, List[dict]] = {}
    scanned_paths: Set[Path] = set()

    for target in target_dirs:
        path = Path(target)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue

        files = [path] if path.is_file() else path.glob("**/*")
        for filepath in files:
            resolved = filepath.resolve()
            if resolved in scanned_paths or filepath.is_dir() or ignore_filter.is_ignored(filepath):
                continue
            if filepath.suffix.lower() not in extensions:
                continue

            scanned_paths.add(resolved)
            total_files += 1
            is_token_file = resolved in token_path_set

            res = scan_design_file(
                filepath=filepath,
                is_token_file=is_token_file,
                defined_tokens=defined_tokens,
                rules_cfg=rules_cfg,
                allowed_unicode=allowed_unicode,
                max_z_index=max_z_index,
            )

            total_css_vars += res["css_vars_used"]
            total_hardcoded_colors += res["hardcoded_colors"]
            total_unicode_icons += res["unicode_icons"]
            total_undefined_tokens += res["undefined_tokens"]

            if res["issues"]:
                rel_path = str(filepath.relative_to(root) if root in filepath.parents else filepath)
                issues_by_file[rel_path] = res["issues"]

    duplicate_tokens_count = 0
    if rules_cfg.get("duplicate_tokens", True) and token_paths:
        dup_by_file = find_duplicate_color_tokens(token_paths, root)
        for rel_path, dup_issues in dup_by_file.items():
            duplicate_tokens_count += len(dup_issues)
            issues_by_file.setdefault(rel_path, []).extend(dup_issues)

    file_issues_count = sum(len(v) for v in issues_by_file.values())
    total_issues = file_issues_count + contrast_res["failures_count"]
    denom = total_css_vars + total_hardcoded_colors
    tokenization_rate = round((total_css_vars / denom * 100.0), 1) if denom > 0 else 100.0

    rel_token_files = [
        str(p.relative_to(root) if root in p.parents else p) for p in token_paths
    ]

    return {
        "total_files": total_files,
        "flagged_files_count": len(issues_by_file),
        "total_issues": total_issues,
        "issues_by_file": issues_by_file,
        "metrics": {
            "hardcoded_colors": total_hardcoded_colors,
            "css_vars_used": total_css_vars,
            "tokenization_rate": tokenization_rate,
            "unicode_icons": total_unicode_icons,
            "undefined_tokens": total_undefined_tokens,
            "duplicate_tokens": duplicate_tokens_count,
            "tokens_files": rel_token_files,
            "defined_tokens_count": len(defined_tokens),
        },
        "contrast": contrast_res,
    }
