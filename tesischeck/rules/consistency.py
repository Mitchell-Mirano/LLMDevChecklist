import re
from typing import List, Pattern

from ..core import BaseRule, ValidationContext, RuleResult

class RegexConstraintRule(BaseRule):
    """
    Scans a file for a specific regex pattern and ensures it either exists
    (if required=True) or does NOT exist (if required=False).
    """
    def __init__(self, file_path: str, pattern: str, required: bool, error_message: str):
        self.file_path = file_path
        self.pattern = re.compile(pattern, re.MULTILINE)
        self.required = required
        self.error_message = error_message
        
    @property
    def name(self) -> str:
        return f"RegexConstraintRule({self.file_path})"
        
    @property
    def description(self) -> str:
        return f"Validates presence or absence of a pattern in {self.file_path}."
        
    def validate(self, context: ValidationContext) -> RuleResult:
        result = RuleResult(RuleResult.PASS)
        content = context.get_file_content(self.file_path)
        
        if not content:
            result.add_error(f"Cannot run RegexConstraintRule: {self.file_path} not found or empty.")
            return result
            
        found = bool(self.pattern.search(content))
        
        if self.required and not found:
            result.add_error(f"[{self.file_path}] {self.error_message}")
        elif not self.required and found:
            result.add_error(f"[{self.file_path}] {self.error_message}")
            
        return result


class ItemCountConsistencyRule(BaseRule):
    """
    Checks that the number of items matching a specific regex pattern across different files
    or blocks is strictly equal. 
    Useful for ensuring # questions == # objectives == # hypotheses.
    """
    def __init__(self, targets: List[dict]):
        """
        targets format: [
            {'file': 'file1.tex', 'pattern': r'\\item', 'name': 'Objectives'},
            {'file': 'file2.tex', 'pattern': r'\\item', 'name': 'Hypotheses'}
        ]
        """
        self.targets = targets
        
    @property
    def name(self) -> str:
        return "ItemCountConsistencyRule"
        
    @property
    def description(self) -> str:
        return "Ensures consistent counts across different entities (e.g. objectives vs hypotheses)."
        
    def validate(self, context: ValidationContext) -> RuleResult:
        result = RuleResult(RuleResult.PASS)
        
        counts = {}
        for target in self.targets:
            file_path = target['file']
            pattern = re.compile(target['pattern'])
            name = target['name']
            
            content = context.get_file_content(file_path)
            # Remove comments to avoid false positives
            content_no_comments = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
            
            count = len(pattern.findall(content_no_comments))
            counts[name] = count
            
        # Check if all counts are identical
        if not counts:
            return result
            
        first_count = list(counts.values())[0]
        if not all(c == first_count for c in counts.values()):
            msg = "Inconsistent counts detected:\n"
            for name, c in counts.items():
                msg += f" - {name}: {c} items\n"
            result.add_error(msg)
            
        return result
