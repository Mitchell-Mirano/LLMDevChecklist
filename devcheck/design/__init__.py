"""Scalable, multi-project Design System & Accessibility Auditor."""

from .auditor import check_design
from .contrast import contrast_ratio, evaluate_contrast, parse_color

__all__ = [
    "check_design",
    "contrast_ratio",
    "evaluate_contrast",
    "parse_color",
]
