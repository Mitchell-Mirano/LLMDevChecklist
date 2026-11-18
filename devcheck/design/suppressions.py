"""Inline suppression parser for design audit comments."""

import re
from typing import Dict, List, Optional, Set

_IGNORE_NEXT_RE = re.compile(
    r"devcheck-ignore-next-line(?:\s*\(\s*([^)]+)\s*\))?",
    re.IGNORECASE,
)
_IGNORE_LINE_RE = re.compile(
    r"devcheck-ignore(?!-next-line)(?:\s*\(\s*([^)]+)\s*\))?",
    re.IGNORECASE,
)


def _parse_rule_set(raw: Optional[str]) -> Optional[Set[str]]:
    if not raw:
        return None
    rules = {r.strip().lower() for r in raw.split(",") if r.strip()}
    return rules or None


def parse_suppressions(lines: List[str]) -> Dict[int, Optional[Set[str]]]:
    """Map 1-based line numbers to suppressed rule IDs (None = suppress all rules)."""
    suppressed: Dict[int, Optional[Set[str]]] = {}

    for idx, line in enumerate(lines, start=1):
        m_next = _IGNORE_NEXT_RE.search(line)
        if m_next:
            target_line = idx + 1
            rules = _parse_rule_set(m_next.group(1))
            if target_line in suppressed:
                if suppressed[target_line] is None or rules is None:
                    suppressed[target_line] = None
                else:
                    suppressed[target_line].update(rules)
            else:
                suppressed[target_line] = rules

        m_curr = _IGNORE_LINE_RE.search(line)
        if m_curr:
            rules = _parse_rule_set(m_curr.group(1))
            if idx in suppressed:
                if suppressed[idx] is None or rules is None:
                    suppressed[idx] = None
                else:
                    suppressed[idx].update(rules)
            else:
                suppressed[idx] = rules

    return suppressed


def is_suppressed(suppressions: Dict[int, Optional[Set[str]]], line_no: int, rule_id: str) -> bool:
    """Return True if rule_id is suppressed on the given 1-based line_no."""
    if line_no not in suppressions:
        return False
    allowed = suppressions[line_no]
    if allowed is None:
        return True
    return rule_id.lower() in allowed
