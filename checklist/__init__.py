"""Dev quality and codebase checklist suite with clear separation between:
1. Auto-Fixers (Deterministic cleaners like import consolidation)
2. LLM Diagnostic Auditors (Context-aware reports formatted for AI Agents & LLMs)
"""

from .gitignore import GitIgnoreFilter
from .config import load_config, init_config_file
from .py_imports import clean_py_imports, detect_inline_imports
from .vue_imports import clean_vue_imports
from .check_code_language import check_code_language
from .check_hardcoded import check_hardcoded
from .verify_docs import verify_docs

# Group 1: Deterministic Auto-Fixers (no LLM required)
AUTO_FIXERS = {
    "py_imports": clean_py_imports,
    "vue_imports": clean_vue_imports,
}

# Group 2: LLM Diagnostic Auditors (generates actionable tasks for LLM / Agent)
LLM_AUDITORS = {
    "language": check_code_language,
    "hardcoded": check_hardcoded,
    "docs": verify_docs,
}


def generate_llm_prompt(audit_results: dict) -> str:
    """Formats diagnostic audit findings into a GitHub-flavored Markdown prompt for LLMs."""
    md = ["# 🤖 Checklist Action Items for LLM / AI Assistant\n"]
    md.append("Automated formatters have completed. Please review and resolve the following context-aware findings:\n")

    has_issues = False

    # 1. Language Audit Findings
    lang = audit_results.get("language", {})
    if lang.get("total_issues", 0) > 0:
        has_issues = True
        md.append("### 🌐 1. Language & Naming Conventions (Enforce English Code/Comments)")
        for file_path, issues in lang.get("issues_by_file", {}).items():
            for line_no, category, details in issues:
                md.append(f"- [ ] [{file_path}:L{line_no}](file://{file_path}#L{line_no}) - **{category}**: {details}")
        md.append("")

    # 2. Hardcoded Secrets / IPs / Paths
    hardcoded = audit_results.get("hardcoded", {})
    if hardcoded.get("total_issues", 0) > 0:
        has_issues = True
        md.append("### 🔍 2. Hardcoded Secrets, IPs & Absolute Paths")
        for file_path, issues in hardcoded.get("issues_by_file", {}).items():
            for issue in issues:
                line_no = issue["line_no"]
                md.append(f"- [ ] [{file_path}:L{line_no}](file://{file_path}#L{line_no}) - **{issue['type']}**: `{issue['matched']}` in line: `{issue['line']}`")
        md.append("")

    # 3. Documentation Coverage
    docs = audit_results.get("docs", {})
    if docs.get("total_issues", 0) > 0:
        has_issues = True
        md.append("### 📚 3. Documentation Coverage & Alignment")
        modules = docs.get("modules", {})
        for name, path in modules.get("undocumented_backend", []):
            md.append(f"- [ ] Undocumented Backend Module: [{name}](file://{path})")
        for name, path in modules.get("undocumented_frontend", []):
            md.append(f"- [ ] Undocumented Frontend Module: [{name}](file://{path})")
        md.append("")

    # 4. Inline Import Warnings
    inline_imports = audit_results.get("inline_imports", [])
    if inline_imports:
        has_issues = True
        md.append("### 📦 4. Inline Imports (PEP 8: move to top-level or confirm intentional)")
        for imp in inline_imports:
            md.append(f"- [ ] [{imp['file']}:L{imp['line_no']}](file://{imp['file']}#L{imp['line_no']}) - `{imp['import_statement']}` inside `{imp['scope']}`")
        md.append("")

    if not has_issues:
        md.append("🎉 **No diagnostic issues found! Codebase is 100% clean and compliant.**")

    return "\n".join(md)


__all__ = [
    "GitIgnoreFilter",
    "load_config",
    "init_config_file",
    "clean_py_imports",
    "detect_inline_imports",
    "clean_vue_imports",
    "check_code_language",
    "check_hardcoded",
    "verify_docs",
    "AUTO_FIXERS",
    "LLM_AUDITORS",
    "generate_llm_prompt",
]
