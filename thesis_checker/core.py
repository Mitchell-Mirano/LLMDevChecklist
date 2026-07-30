from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
import glob

class RuleResult:
    """Standardized result object for rules."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    
    def __init__(self, status: str, messages: Optional[List[str]] = None):
        self.status = status
        self.messages = messages or []
        
    def add_error(self, message: str):
        self.status = self.FAIL
        self.messages.append(message)
        
    def add_warning(self, message: str):
        if self.status == self.PASS:
            self.status = self.WARNING
        self.messages.append(message)
        
    def __bool__(self):
        return self.status == self.PASS


class ValidationContext:
    """Holds state and caches file reads during a validation run."""
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)
        self._file_cache: Dict[str, str] = {}
        
    def get_file_content(self, relative_path: str) -> str:
        """Reads a file and caches it. Returns empty string if not found."""
        abs_path = os.path.join(self.target_dir, relative_path)
        if abs_path in self._file_cache:
            return self._file_cache[abs_path]
            
        if not os.path.exists(abs_path):
            return ""
            
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self._file_cache[abs_path] = content
            return content

    def glob_files(self, pattern: str) -> List[str]:
        """Returns relative paths matching a glob pattern."""
        search_path = os.path.join(self.target_dir, pattern)
        abs_paths = glob.glob(search_path, recursive=True)
        return [os.path.relpath(p, self.target_dir) for p in abs_paths]


class BaseRule(ABC):
    """Abstract base class for all validation rules."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the rule."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Human readable description of what the rule checks."""
        pass
        
    @abstractmethod
    def validate(self, context: ValidationContext) -> RuleResult:
        """Executes the rule logic against the provided context."""
        pass
