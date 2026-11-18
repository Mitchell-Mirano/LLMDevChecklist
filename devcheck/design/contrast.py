"""WCAG 2.1 contrast calculation and CSS color normalization utilities."""

import math
import re
from typing import Dict, Optional, Tuple

RGBA = Tuple[int, int, int, float]
RGB = Tuple[int, int, int]

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB_RE = re.compile(
    r"^rgba?\(\s*([\d.]+%?)\s*[,\s]\s*([\d.]+%?)\s*[,\s]\s*([\d.]+%?)"
    r"(?:\s*[,/]\s*([\d.]+%?))?\s*\)$",
    re.IGNORECASE,
)
_HSL_RE = re.compile(
    r"^hsla?\(\s*([\d.]+)(?:deg)?\s*[,\s]\s*([\d.]+)%\s*[,\s]\s*([\d.]+)%"
    r"(?:\s*[,/]\s*([\d.]+%?))?\s*\)$",
    re.IGNORECASE,
)

NAMED_COLORS: Dict[str, RGBA] = {
    "black": (0, 0, 0, 1.0),
    "white": (255, 255, 255, 1.0),
    "red": (255, 0, 0, 1.0),
    "green": (0, 128, 0, 1.0),
    "blue": (0, 0, 255, 1.0),
    "yellow": (255, 255, 0, 1.0),
    "orange": (255, 165, 0, 1.0),
    "purple": (128, 0, 128, 1.0),
    "pink": (255, 192, 203, 1.0),
    "gray": (128, 128, 128, 1.0),
    "grey": (128, 128, 128, 1.0),
    "silver": (192, 192, 192, 1.0),
    "navy": (0, 0, 128, 1.0),
    "teal": (0, 128, 128, 1.0),
    "cyan": (0, 255, 255, 1.0),
    "magenta": (255, 0, 255, 1.0),
    "maroon": (128, 0, 0, 1.0),
    "olive": (128, 128, 0, 1.0),
    "lime": (0, 255, 0, 1.0),
    "aqua": (0, 255, 255, 1.0),
    "fuchsia": (255, 0, 255, 1.0),
}


def _parse_alpha(alpha_str: Optional[str]) -> float:
    if alpha_str is None:
        return 1.0
    s = alpha_str.strip()
    if s.endswith("%"):
        return max(0.0, min(1.0, float(s[:-1]) / 100.0))
    return max(0.0, min(1.0, float(s)))


def _parse_channel(val: str) -> int:
    s = val.strip()
    if s.endswith("%"):
        return max(0, min(255, round(float(s[:-1]) * 255.0 / 100.0)))
    return max(0, min(255, round(float(s))))


def _hsl_to_rgb(h: float, s: float, l: float) -> RGB:
    h = (h % 360.0) / 360.0
    s = max(0.0, min(1.0, s / 100.0))
    l = max(0.0, min(1.0, l / 100.0))

    if s == 0:
        v = round(l * 255)
        return (v, v, v)

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    r = round(hue_to_rgb(p, q, h + 1 / 3) * 255)
    g = round(hue_to_rgb(p, q, h) * 255)
    b = round(hue_to_rgb(p, q, h - 1 / 3) * 255)
    return (r, g, b)


def parse_color(color_str: str) -> Optional[RGBA]:
    """Parse hex, rgb/rgba, hsl/hsla, or named CSS color into (r, g, b, alpha)."""
    if not color_str:
        return None
    cleaned = color_str.strip().lower()

    if cleaned in NAMED_COLORS:
        return NAMED_COLORS[cleaned]

    hex_m = _HEX_RE.match(cleaned)
    if hex_m:
        h = hex_m.group(1)
        if len(h) in (3, 4):
            r = int(h[0] * 2, 16)
            g = int(h[1] * 2, 16)
            b = int(h[2] * 2, 16)
            a = int(h[3] * 2, 16) / 255.0 if len(h) == 4 else 1.0
            return (r, g, b, a)
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
        return (r, g, b, a)

    rgb_m = _RGB_RE.match(cleaned)
    if rgb_m:
        r = _parse_channel(rgb_m.group(1))
        g = _parse_channel(rgb_m.group(2))
        b = _parse_channel(rgb_m.group(3))
        a = _parse_alpha(rgb_m.group(4))
        return (r, g, b, a)

    hsl_m = _HSL_RE.match(cleaned)
    if hsl_m:
        r, g, b = _hsl_to_rgb(
            float(hsl_m.group(1)),
            float(hsl_m.group(2)),
            float(hsl_m.group(3)),
        )
        a = _parse_alpha(hsl_m.group(4))
        return (r, g, b, a)

    return None


def composite_alpha(fg: RGBA, bg: RGB) -> RGB:
    """Alpha-composite foreground RGBA over opaque background RGB."""
    alpha = fg[3]
    if alpha >= 1.0:
        return (fg[0], fg[1], fg[2])
    r = round(fg[0] * alpha + bg[0] * (1.0 - alpha))
    g = round(fg[1] * alpha + bg[1] * (1.0 - alpha))
    b = round(fg[2] * alpha + bg[2] * (1.0 - alpha))
    return (r, g, b)


def _srgb_to_linear(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else math.pow((s + 0.055) / 1.055, 2.4)


def relative_luminance(rgb: RGB) -> float:
    """Compute WCAG 2.1 relative luminance for an opaque sRGB tuple."""
    r_lin = _srgb_to_linear(rgb[0])
    g_lin = _srgb_to_linear(rgb[1])
    b_lin = _srgb_to_linear(rgb[2])
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(fg_str: str, bg_str: str, fallback_bg: str = "#121212") -> Optional[float]:
    """Calculate WCAG 2.1 contrast ratio between foreground and background colors."""
    fg = parse_color(fg_str)
    bg = parse_color(bg_str)
    if fg is None or bg is None:
        return None

    base = parse_color(fallback_bg) or (18, 18, 18, 1.0)
    bg_rgb = composite_alpha(bg, (base[0], base[1], base[2]))
    fg_rgb = composite_alpha(fg, bg_rgb)

    l1 = relative_luminance(fg_rgb)
    l2 = relative_luminance(bg_rgb)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def evaluate_contrast(ratio: float, min_aa: float = 4.5, min_large: float = 3.0) -> dict:
    """Evaluate a contrast ratio against WCAG 2.1 AA and AAA thresholds."""
    aa_normal = ratio >= min_aa
    aa_large = ratio >= min_large
    aaa_normal = ratio >= 7.0
    status = "PASS" if aa_normal else ("PASS (Large)" if aa_large else "FAIL")
    return {
        "ratio": round(ratio, 2),
        "aa_normal": aa_normal,
        "aa_large": aa_large,
        "aaa_normal": aaa_normal,
        "status": status,
    }
