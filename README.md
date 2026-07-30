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

After installation, the primary CLI commands `devcheck` and `tesischeck` are available:
```bash
devcheck --help        # Code quality & import cleanup suite (aliases: checklist, llm-dev-checklist)
tesischeck --help      # UNMSM LaTeX thesis manuscript validator (alias: thesis-checker)
```

---

## 🚀 Features

- **TOML Configuration (`checklist.toml` / `pyproject.toml`)**: Flexible, per-project rules.
- **Smart Project Detection (`devcheck init`)**: Auto-detects `src/`, `backend/`, `app/`, `frontend/` etc. and pre-configures `target_dirs`.
- **`.gitignore` Parsing**: Automatically respects `.gitignore` rules.
- **Python Import Cleaner (`clean_py_imports`)**: Consolidates duplicate top-level imports and purges unused references.
- **Vue / TS / JS Import Cleaner (`clean_vue_imports`)**: Merges duplicate imports in `.vue` `<script>` blocks, `.ts`, and `.js` files.
- **Inline Import Detection**: Flags `import` statements inside functions/methods as PEP 8 audit warnings.
- **English Language Compliance (`check_code_language`)**: Detects Spanish symbols, functions, variable names, and comments.
- **Secrets & Hardcoded Audit (`check_hardcoded`)**: Identifies absolute paths, IP addresses, secret keys, and JWT tokens.
- **Documentation Coverage Auditor (`verify_docs`)**: Audits modules, environment variables, and database schemas against documentation.
- **Multiple Output Formats**: `text` (terminal), `json` (CI/CD pipelines), `llm` (Markdown action prompts for AI Agents).
- **LaTeX Thesis Checker (`tesischeck`)**: Validates UNMSM thesis manuscript structure, consistency, equation environments, hardcoded tables, citations, and labels.

---

## ⚙️ Project Setup & Configuration

Initialize a `checklist.toml` in any target project (auto-detects project structure):

```bash
devcheck init
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

## 💻 CLI Commands & Examples (`devcheck`)

### Setup
```bash
devcheck init                        # Create checklist.toml with auto-detected dirs
```

### Auto-Fixers (Import Cleaners)
```bash
devcheck fix                         # Run import cleaners (modifies files on disk)
devcheck fix --dry-run               # Preview without modifying any files
devcheck fix -v                      # Verbose: show modified file list
devcheck fix backend/ app/           # Target specific directories
```

### Diagnostic Audits
```bash
devcheck audit                       # Terminal summary of all audit findings
devcheck audit -v                    # Verbose: line-by-line detail
devcheck audit --format llm          # Markdown action prompt for AI Agents
devcheck audit --format json         # JSON output for CI/CD pipelines
devcheck audit --llm                 # Shortcut for --format llm
devcheck audit backend/ frontend/    # Target specific directories
```

### Combined (Fixers + Audit)
```bash
devcheck run                         # Run fixers, then audit summary
devcheck run --format llm            # Run fixers, then LLM action prompt
devcheck run --format json           # Full JSON output (fixers + audit)
devcheck run --dry-run -v            # Preview fixers, then verbose audit
```

---

## 📝 Thesis Checker (`tesischeck`)

A separate validation suite for LaTeX thesis manuscripts, designed to enforce UNMSM (Universidad Nacional Mayor de San Marcos) thesis guidelines.

### CLI Usage

```bash
# Validate a LaTeX thesis project
tesischeck --target /path/to/latex/project

# JSON output for CI/CD
tesischeck --target /path/to/latex/project --format json

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

---

## 🧪 Centralized Test Suite

The project includes a centralized test suite differentiated per module:

```bash
# Run all tests (devcheck + tesischeck)
python3 -m unittest discover tests -v

# Run only devcheck tests
python3 -m unittest discover tests/test_devcheck -v

# Run only tesischeck tests
python3 -m unittest discover tests/test_tesischeck -v
```


