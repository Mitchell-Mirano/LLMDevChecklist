import os
import re
from typing import List, Dict

from ..core import BaseRule, ValidationContext, RuleResult

class FileExistenceRule(BaseRule):
    """Verifies that all specified files exist."""
    
    def __init__(self, required_files: List[str]):
        self.required_files = required_files
        
    @property
    def name(self) -> str:
        return "FileExistenceRule"
        
    @property
    def description(self) -> str:
        return "Verifies that all required files exist in the project."
        
    def validate(self, context: ValidationContext) -> RuleResult:
        result = RuleResult(RuleResult.PASS)
        for rel_path in self.required_files:
            abs_path = os.path.join(context.target_dir, rel_path)
            if not os.path.exists(abs_path):
                result.add_error(f"Required file missing: {rel_path}")
        return result


class SectionHierarchyRule(BaseRule):
    r"""
    Verifies that a specific file contains exactly the expected sections.
    It can ensure exact ordering and names of LaTeX \section{} commands.
    """
    
    def __init__(self, file_path: str, expected_sections: List[str], allow_additional: bool = False):
        self.file_path = file_path
        self.expected_sections = expected_sections
        self.allow_additional = allow_additional
        
    @property
    def name(self) -> str:
        return f"SectionHierarchyRule({self.file_path})"
        
    @property
    def description(self) -> str:
        return f"Verifies exact section titles and hierarchy in {self.file_path}."
        
    def validate(self, context: ValidationContext) -> RuleResult:
        result = RuleResult(RuleResult.PASS)
        content = context.get_file_content(self.file_path)
        
        if not content:
            result.add_error(f"Cannot run SectionHierarchyRule: {self.file_path} not found or empty.")
            return result
            
        # Extract all \section{...} commands, ignoring commented out sections
        sections = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('%'):
                continue
            
            # Simple regex to extract section titles, e.g. \section{Title}
            match = re.search(r'\\section\s*\{([^}]*)\}', line)
            if match:
                sections.append(match.group(1).strip())
                
        # Compare extracted sections to expected
        if not self.allow_additional and len(sections) != len(self.expected_sections):
            result.add_error(
                f"[{self.file_path}] Expected {len(self.expected_sections)} sections, "
                f"found {len(sections)}.\nExpected: {self.expected_sections}\nFound: {sections}"
            )
            
        for i, expected in enumerate(self.expected_sections):
            if i >= len(sections):
                result.add_error(f"[{self.file_path}] Missing expected section: '{expected}'")
            elif sections[i] != expected:
                result.add_error(f"[{self.file_path}] Section title mismatch at index {i+1}. Expected: '{expected}', Found: '{sections[i]}'")
                
        return result
