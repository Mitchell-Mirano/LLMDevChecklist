# 🛠️ LLM Dev Checklist & Code Quality Suite

A modular, lightweight Python library and CLI tool designed for auditing and cleaning AI-generated code, ensuring high code quality standards in Python and Vue.js/TypeScript projects.

---

## 📥 Installation from GitHub

```bash
# Using pip
pip install git+https://github.com/Mitchell-Mirano/LLMDevChecklist.git

# Using pipx (global CLI tool)
pipx install git+https://github.com/Mitchell-Mirano/LLMDevChecklist.git
```

After installation, both `checklist` and `llm-dev-checklist` commands are available:
```bash
checklist --help
llm-dev-checklist --help  # Same tool, alternative name
```

---

## 🚀 Features

- **TOML Configuration (`checklist.toml` / `pyproject.toml`)**: Flexible, per-project rules.
- **Smart Project Detection (`checklist init`)**: Auto-detects `src/`, `backend/`, `app/`, `frontend/` etc. and pre-configures `target_dirs`.
- **`.gitignore` Parsing**: Automatically respects `.gitignore` rules.
- **Python Import Cleaner (`clean_py_imports`)**: Consolidates duplicate top-level imports and purges unused references.
- **Vue / TS / JS Import Cleaner (`clean_vue_imports`)**: Merges duplicate imports in `.vue` `<script>` blocks, `.ts`, and `.js` files.
- **Inline Import Detection**: Flags `import` statements inside functions/methods as PEP 8 audit warnings.
- **English Language Compliance (`check_code_language`)**: Detects Spanish symbols, functions, variable names, and comments.
- **Secrets & Hardcoded Audit (`check_hardcoded`)**: Identifies absolute paths, IP addresses, secret keys, and JWT tokens.
- **Documentation Coverage Auditor (`verify_docs`)**: Audits modules, environment variables, and database schemas against documentation.
- **Multiple Output Formats**: `text` (terminal), `json` (CI/CD pipelines), `llm` (Markdown action prompts for AI Agents).

---

## ⚙️ Project Setup & Configuration

Initialize a `checklist.toml` in any target project (auto-detects project structure):

```bash
checklist init
```

Example output:
```
✨ Created configuration file at: /path/to/project/checklist.toml
   Auto-detected target directories: ['backend', 'frontend/src', 'scripts']
```

Example `checklist.toml`:

```toml
[checklist]
use_gitignore = true
target_dirs = ["backend", "frontend/src", "scripts"]
exclude_dirs = [".git", ".venv", "venv", "node_modules", "dist", "site", "__pycache__", "mongo-data"]
exclude_files = ["vite.config.js"]

[checklist.auto_fixers]
py_imports = true
vue_imports = true

[checklist.auditors]
language = true
hardcoded = true
docs = true

[checklist.language]
strict_english = true
custom_allowed_words = ["gptw", "nps", "rut"]

[checklist.hardcoded]
allow_localhost = true
```

---

## 💻 CLI Commands & Examples

### Setup
```bash
checklist init                        # Create checklist.toml with auto-detected dirs
```

### Auto-Fixers (Import Cleaners)
```bash
checklist fix                         # Run import cleaners (modifies files on disk)
checklist fix --dry-run               # Preview without modifying any files
checklist fix -v                      # Verbose: show modified file list
checklist fix backend/ app/           # Target specific directories
```

### Diagnostic Audits
```bash
checklist audit                       # Terminal summary of all audit findings
checklist audit -v                    # Verbose: line-by-line detail
checklist audit --format llm          # Markdown action prompt for AI Agents
checklist audit --format json         # JSON output for CI/CD pipelines
checklist audit --llm                 # Shortcut for --format llm
checklist audit backend/ frontend/    # Target specific directories
```

### Combined (Fixers + Audit)
```bash
checklist run                         # Run fixers, then audit summary
checklist run --format llm            # Run fixers, then LLM action prompt
checklist run --format json           # Full JSON output (fixers + audit)
checklist run --dry-run -v            # Preview fixers, then verbose audit
```

### Python module syntax
```bash
python -m checklist run --format llm
```

---

## 📦 Programmatic Python Usage

Import and run auditors or auto-fixers directly in custom scripts or CI/CD pipelines:

```python
from pathlib import Path
from checklist import (
    load_config,
    GitIgnoreFilter,
    clean_py_imports,
    clean_vue_imports,
    detect_inline_imports,
    check_code_language,
    check_hardcoded,
    generate_llm_prompt,
)

root = Path.cwd()
config = load_config(root)
ignore_filter = GitIgnoreFilter(root)
target_dirs = config["checklist"]["target_dirs"]

# 1. Clean imports automatically
py_res = clean_py_imports(target_dirs=target_dirs, ignore_filter=ignore_filter)
vue_res = clean_vue_imports(target_dirs=target_dirs, ignore_filter=ignore_filter)

# 2. Audit code language & secrets
lang_results = check_code_language(target_dirs=target_dirs, ignore_filter=ignore_filter)
secret_results = check_hardcoded(target_dirs=target_dirs, ignore_filter=ignore_filter)

# 3. Get inline import warnings
inline_imports = py_res.get("inline_imports", [])

# 4. Generate LLM prompt for AI Agents
prompt = generate_llm_prompt({
    "language": lang_results,
    "hardcoded": secret_results,
    "inline_imports": inline_imports,
})
print(prompt)
```

---

## 🔗 Pre-commit Integration

Add to your project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Mitchell-Mirano/LLMDevChecklist
    rev: v1.1.0
    hooks:
      - id: checklist-fix
      - id: checklist-audit
```

---

## 🤖 GitHub Actions Integration

Add the provided workflow template to your repository:

```yaml
# .github/workflows/checklist.yml
name: LLM Dev Checklist — Code Quality Audit

on:
  pull_request:
    branches: [main, develop]

jobs:
  checklist-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install git+https://github.com/Mitchell-Mirano/LLMDevChecklist.git
      - run: checklist fix --dry-run -v
      - run: checklist audit --format json > audit-results.json
      - uses: actions/upload-artifact@v4
        with:
          name: checklist-audit-results
          path: audit-results.json
```

---

## 📝 Thesis Checker (UNMSM LaTeX Validator)

A separate validation suite for LaTeX thesis manuscripts, designed to enforce UNMSM (Universidad Nacional Mayor de San Marcos) thesis guidelines.

### CLI Usage

```bash
# Validate a LaTeX thesis project
thesis-checker --target /path/to/latex/project

# JSON output for CI/CD
thesis-checker --target /path/to/latex/project --format json

# Via Python module
python -m thesis_checker --target /path/to/latex/project
```

### Available Rules

| Rule | Description |
|------|-------------|
| `FileExistenceRule` | Verifies all required files exist (`tesis.tex`, chapters, bibliography) |
| `SectionHierarchyRule` | Validates exact section titles and ordering per chapter |
| `RegexConstraintRule` | Checks for forbidden or required patterns in files |
| `ItemCountConsistencyRule` | Ensures objectives, problems, and hypotheses counts match |
| `NoHardcodedTablesRule` | Tables must be imported via `\input{}`, not hardcoded |
| `CiteVerificationRule` | Every `\cite{}` key must exist in the `.bib` file |
| `OrphanLabelRule` | Every `\label{}` must have a corresponding `\ref{}` |
| `EquationEnvironmentRule` | Prohibits unnumbered equations (`$$`, `equation*`) |
| `LiteraturePDFNamingRule` | PDF filenames must match citation keys in `.bib` |

### UNMSM Thesis Structure Expected

```
project/
├── tesis.tex
├── bibliografia.bib
└── chapters/
    ├── 01_problema_investigacion.tex
    ├── 02_revision_literatura.tex
    ├── 03_hipotesis_variables.tex
    ├── 04_materiales_metodos.tex
    ├── 05_resultados.tex
    ├── 06_conclusiones.tex
    └── 07_anexos.tex
```

### Programmatic Usage

```python
from thesis_checker import ValidatorRunner, get_unmsm_rules

runner = ValidatorRunner("/path/to/latex/project")
for rule in get_unmsm_rules():
    runner.add_rule(rule)

results = runner.run(output_format="json")  # or "text"
print(f"Passed: {results['passed']}/{results['total_rules']}")
```

### Custom Rules

Extend `BaseRule` to create your own institutional rules:

```python
from thesis_checker import BaseRule, ValidationContext, RuleResult

class CustomRule(BaseRule):
    @property
    def name(self):
        return "CustomRule"

    @property
    def description(self):
        return "My custom validation rule."

    def validate(self, context: ValidationContext) -> RuleResult:
        result = RuleResult(RuleResult.PASS)
        content = context.get_file_content("tesis.tex")
        if "keyword" not in content:
            result.add_error("Missing required keyword in tesis.tex")
        return result
```

