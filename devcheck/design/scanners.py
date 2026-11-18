"""Modular line-by-line scanners for design system, icons, CSS hygiene, and a11y."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from .contrast import NAMED_COLORS
from .suppressions import is_suppressed, parse_suppressions

# Color patterns
_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
_RGB_RE = re.compile(
    r"\brgba?\(\s*[\d.]+%?\s*[,\s]\s*[\d.]+%?\s*[,\s]\s*[\d.]+%?"
    r"(?:\s*[,/]\s*[\d.]+%?)?\s*\)",
    re.IGNORECASE,
)
_HSL_RE = re.compile(
    r"\bhsla?\(\s*[\d.]+(?:deg)?\s*[,\s]\s*[\d.]+%\s*[,\s]\s*[\d.]+%"
    r"(?:\s*[,/]\s*[\d.]+%?)?\s*\)",
    re.IGNORECASE,
)
_NAMED_COLOR_PROP_RE = re.compile(
    r"\b(?:color|background|background-color|border-color|outline-color|fill|stroke)\s*:\s*"
    r"(" + "|".join(re.escape(c) for c in NAMED_COLORS) + r")\b",
    re.IGNORECASE,
)
_HEX_CONTEXT_RE = re.compile(
    r"(?::|style=|fill=|stroke=|color=|background\s*:|border\s*:)",
    re.IGNORECASE,
)

# CSS Variables
_CSS_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)(?:\s*,[^)]+)?\s*\)")
_CSS_VAR_DECL_LINE_RE = re.compile(r"(?:^|[{;\s])--[\w-]+\s*:")

# Unicode emojis & pseudo-icons (including variation selector U+FE0F)
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"
    r"\U00002600-\U000027BF"
    r"\U00002300-\U000023FF"
    r"\U00002B00-\U00002BFF"
    r"\U0001FA00-\U0001FAFF]\uFE0F?"
)

# CSS hygiene & LLM anti-patterns
_INLINE_STYLE_RE = re.compile(r"""\bstyle\s*=\s*["'][^"']+["']""", re.IGNORECASE)
_IMPORTANT_RE = re.compile(r"!important\b", re.IGNORECASE)
_FONT_FAMILY_RE = re.compile(r"\bfont-family\s*:\s*([^;]+)", re.IGNORECASE)
_Z_INDEX_RE = re.compile(r"\bz-index\s*:\s*(\d+)\b", re.IGNORECASE)

# SVG & A11y
_SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)
_IMG_TAG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
_NON_SEMANTIC_CLICK_RE = re.compile(
    r"<(?:div|span)\b([^>]*(?:@click|v-on:click|onClick)\s*=[^>]*)>",
    re.IGNORECASE,
)
_ICON_BUTTON_RE = re.compile(
    r"<button\b([^>]*)>\s*<(?:svg|[A-Z]\w*Icon)\b",
    re.IGNORECASE,
)

_TEMPLATE_EXTS = {".vue", ".html", ".tsx", ".jsx", ".svelte"}
_STYLE_EXTS = {".css", ".scss", ".sass", ".less", ".vue"}


def _strip_comments_for_line(line: str, in_css_comment: bool, in_html_comment: bool) -> Tuple[str, bool, bool]:
    """Return active code portion of a line and updated multiline comment flags."""
    out = []
    i = 0
    n = len(line)
    while i < n:
        if in_css_comment:
            end = line.find("*/", i)
            if end == -1:
                return "".join(out), True, in_html_comment
            in_css_comment = False
            i = end + 2
        elif in_html_comment:
            end = line.find("-->", i)
            if end == -1:
                return "".join(out), in_css_comment, True
            in_html_comment = False
            i = end + 3
        else:
            if line.startswith("/*", i):
                in_css_comment = True
                i += 2
            elif line.startswith("<!--", i):
                in_html_comment = True
                i += 4
            elif line.startswith("//", i):
                break
            else:
                out.append(line[i])
                i += 1
    return "".join(out), in_css_comment, in_html_comment


def _add_issue(
    issues: List[dict],
    suppressions: dict,
    line_no: int,
    rule: str,
    matched: str,
    message: str,
) -> bool:
    if is_suppressed(suppressions, line_no, rule):
        return False
    issues.append({
        "line_no": line_no,
        "rule": rule,
        "matched": matched,
        "message": message,
    })
    return True


def scan_design_file(
    filepath: Path,
    is_token_file: bool,
    defined_tokens: Set[str],
    rules_cfg: Dict[str, bool],
    allowed_unicode: Set[str],
    max_z_index: int = 100,
) -> dict:
    """Scan a single frontend file for design system, icon, CSS hygiene, and a11y issues."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"issues": [], "css_vars_used": 0, "hardcoded_colors": 0, "unicode_icons": 0, "undefined_tokens": 0}

    lines = content.splitlines()
    suppressions = parse_suppressions(lines)
    ext = filepath.suffix.lower()
    is_template = ext in _TEMPLATE_EXTS
    is_style = ext in _STYLE_EXTS

    issues: List[dict] = []
    css_vars_used = 0
    hardcoded_colors = 0
    unicode_icons = 0
    undefined_tokens = 0

    in_css_comment = False
    in_html_comment = False

    for line_no, raw_line in enumerate(lines, start=1):
        line, in_css_comment, in_html_comment = _strip_comments_for_line(
            raw_line, in_css_comment, in_html_comment
        )
        if not line.strip():
            continue

        # Track CSS var() usage & check undefined tokens
        for var_m in _CSS_VAR_RE.finditer(line):
            var_name = var_m.group(1)
            css_vars_used += 1
            if (
                rules_cfg.get("undefined_tokens", True)
                and defined_tokens
                and var_name not in defined_tokens
            ):
                if _add_issue(
                    issues, suppressions, line_no, "undefined-token", var_name,
                    f"CSS variable `{var_name}` is not defined in project token files."
                ):
                    undefined_tokens += 1

        is_token_decl = is_token_file and bool(_CSS_VAR_DECL_LINE_RE.search(line))

        # Hardcoded colors (allowed only in CSS custom property declarations inside token files)
        if not is_token_decl and rules_cfg.get("hardcoded_colors", True):
            if _HEX_CONTEXT_RE.search(line):
                for m in _HEX_RE.finditer(line):
                    if _add_issue(
                        issues, suppressions, line_no, "hardcoded-color", m.group(0).lower(),
                        f"Hardcoded hex color `{m.group(0)}`; use a CSS token `var(--*)` from main.css."
                    ):
                        hardcoded_colors += 1
            for pattern in (_RGB_RE, _HSL_RE):
                for m in pattern.finditer(line):
                    if _add_issue(
                        issues, suppressions, line_no, "hardcoded-color", m.group(0).lower(),
                        f"Hardcoded color `{m.group(0)}`; use a CSS token `var(--*)` from main.css."
                    ):
                        hardcoded_colors += 1
            for m in _NAMED_COLOR_PROP_RE.finditer(line):
                if _add_issue(
                    issues, suppressions, line_no, "hardcoded-color", m.group(1).lower(),
                    f"Named CSS color `{m.group(1)}`; use a CSS token `var(--*)` from main.css."
                ):
                    hardcoded_colors += 1

        # Unicode emojis / pseudo-icons
        if rules_cfg.get("unicode_icons", True):
            for m in _EMOJI_RE.finditer(line):
                char = m.group(0)
                if char in allowed_unicode:
                    continue
                if _add_issue(
                    issues, suppressions, line_no, "unicode-icon", char,
                    f"Unicode symbol/emoji `{char}` used in UI; replace with an SVG icon."
                ):
                    unicode_icons += 1

        # SVG viewBox check
        if is_template and rules_cfg.get("svg_viewbox", True):
            for m in _SVG_OPEN_RE.finditer(line):
                attrs = m.group(1)
                if "viewbox" not in attrs.lower():
                    _add_issue(
                        issues, suppressions, line_no, "svg-missing-viewbox", "<svg>",
                        "Inline `<svg>` is missing a `viewBox` attribute."
                    )

        # Inline styles in templates
        if is_template and rules_cfg.get("inline_styles", True):
            for m in _INLINE_STYLE_RE.finditer(line):
                _add_issue(
                    issues, suppressions, line_no, "inline-style", m.group(0)[:60],
                    "Static inline `style=\"...\"` detected; move styles to scoped CSS using design tokens."
                )

        # !important banned everywhere in the app (CSS, SCSS, Vue, inline styles)
        if rules_cfg.get("important", True) and _IMPORTANT_RE.search(line):
            _add_issue(
                issues, suppressions, line_no, "important-override", "!important",
                "Avoid `!important`; fix selector specificity or token hierarchy instead."
            )

        # Hardcoded font-family & magic z-index (allowed only in token declarations)
        if is_style and not is_token_decl:
            if rules_cfg.get("hardcoded_font", True):
                fm = _FONT_FAMILY_RE.search(line)
                if fm and "var(" not in fm.group(1).lower() and "inherit" not in fm.group(1).lower():
                    _add_issue(
                        issues, suppressions, line_no, "hardcoded-font", fm.group(0)[:60],
                        "Hardcoded `font-family`; use a typography token `var(--font-*)`."
                    )
            if rules_cfg.get("z_index_magic", True):
                zm = _Z_INDEX_RE.search(line)
                if zm and int(zm.group(1)) > max_z_index:
                    _add_issue(
                        issues, suppressions, line_no, "magic-z-index", zm.group(0),
                        f"Magic `{zm.group(0)}` (> {max_z_index}); use a layer token `var(--z-*)`."
                    )

        # Basic A11y checks in templates
        if is_template and rules_cfg.get("a11y_basic", True):
            for m in _IMG_TAG_RE.finditer(line):
                attrs = m.group(1).lower()
                if "alt=" not in attrs:
                    _add_issue(
                        issues, suppressions, line_no, "a11y-img-alt", "<img>",
                        "`<img>` element is missing an `alt` attribute."
                    )
            for m in _NON_SEMANTIC_CLICK_RE.finditer(line):
                attrs = m.group(1).lower()
                if "role=" not in attrs and "tabindex" not in attrs:
                    _add_issue(
                        issues, suppressions, line_no, "a11y-clickable-non-semantic", m.group(0)[:50],
                        "Clickable `<div>`/`<span>` without `role`/`tabindex`; prefer `<button>`."
                    )
            for m in _ICON_BUTTON_RE.finditer(line):
                attrs = m.group(1).lower()
                if "aria-label" not in attrs and "title=" not in attrs:
                    _add_issue(
                        issues, suppressions, line_no, "a11y-icon-button", "<button>",
                        "Icon-only `<button>` is missing `aria-label` or `title`."
                    )

    return {
        "issues": issues,
        "css_vars_used": css_vars_used,
        "hardcoded_colors": hardcoded_colors,
        "unicode_icons": unicode_icons,
        "undefined_tokens": undefined_tokens,
    }
