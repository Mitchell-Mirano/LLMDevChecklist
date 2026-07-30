"""Thesis Checker — LaTeX manuscript validation suite for research projects.

Provides a rule-based validation framework for checking LaTeX thesis manuscripts
against institutional guidelines (e.g., UNMSM).
"""

from .core import BaseRule, RuleResult, ValidationContext
from .runner import ValidatorRunner
from .unmsm_rules import get_unmsm_rules

__all__ = [
    "BaseRule",
    "RuleResult",
    "ValidationContext",
    "ValidatorRunner",
    "get_unmsm_rules",
]
