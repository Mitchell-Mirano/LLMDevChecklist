# 🛠️ LLM Dev Checklist & Code Quality Suite

A modular, lightweight Python library and CLI tool designed for auditing and cleaning AI-generated code, ensuring high code quality standards in Python and Vue.js/TypeScript projects.

---

## 📥 Installation from GitHub

You can install this package directly from GitHub using `pip` or `pipx`:

### Using `pip`

```bash
pip install git+https://github.com/mitchellmirano/LLMDevChecklist.git
```

### Using `pipx` (Global CLI tool)

```bash
pipx install git+https://github.com/mitchellmirano/LLMDevChecklist.git
```

---

## 🚀 Features

- **TOML Configuration (`checklist.toml` / `pyproject.toml`)**: Flexible, per-project rules.
- **`.gitignore` Parsing**: Automatically respects `.gitignore` rules and ignores configured build/environment directories (`node_modules`, `.venv`, `dist`, etc.).
- **Python Import Cleaner (`clean_py_imports`)**: Consolidates duplicate top-level imports and purges unused references without breaking inline imports or `sys.path` logic.
- **Vue / TS / JS Import Cleaner (`clean_vue_imports`)**: Merges duplicate imports in `.vue` `<script>` blocks, `.ts`, and `.js` files and strips unused symbols.
- **English Language Compliance (`check_code_language`)**: Detects Spanish symbols, functions, variable names, and comments to enforce English standard code bases.
- **Secrets & Hardcoded Audit (`check_hardcoded`)**: Identifies absolute paths, IP addresses, secret keys, and JWT tokens.
- **Documentation Coverage Auditor (`verify_docs`)**: Audits modules, environment variables, and database schemas against documentation.

---

## ⚙️ Project Setup & Configuration

Initialize a default `checklist.toml` file in any target project:

```bash
checklist init
```

Example `checklist.toml`:

```toml
# 🛠️ Checklist Configuration (checklist.toml)

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

Once installed, use the `checklist` command line utility:

```bash
# 1. Initialize configuration file in current directory
checklist init

# 2. Run combined auto-fixers and diagnostic audit
checklist run

# 3. Run auto-fixers and format audit findings as a Markdown Action Prompt for AI Agents
checklist run --llm

# 4. Preview import cleanups WITHOUT modifying any files on disk
checklist fix --dry-run

# 5. Run auto-fixers with verbose file details
checklist fix -v

# 6. Run read-only audit with detailed line-by-line findings in terminal
checklist audit -v

# 7. Run audit or fix on specific subdirectories only
checklist audit backend/ frontend/src/
```

You can also run it via Python module syntax:
```bash
python -m checklist run --llm
```

---

## 📦 Programmatic Python Usage

Import and run auditors or auto-fixers directly inside your custom Python scripts or CI/CD pipelines:

```python
from pathlib import Path
from checklist import (
    load_config,
    GitIgnoreFilter,
    check_code_language,
    check_hardcoded,
    clean_py_imports,
    clean_vue_imports,
    generate_llm_prompt,
)

root = Path.cwd()

# 1. Load project settings
config = load_config(root)

# 2. Parse .gitignore rules
ignore_filter = GitIgnoreFilter(root)

# 3. Clean imports automatically
clean_py_imports(target_dirs=config["checklist"]["target_dirs"], ignore_filter=ignore_filter)
clean_vue_imports(target_dirs=config["checklist"]["target_dirs"], ignore_filter=ignore_filter)

# 4. Audit code language & secrets
lang_results = check_code_language(target_dirs=config["checklist"]["target_dirs"], ignore_filter=ignore_filter)
secret_results = check_hardcoded(target_dirs=config["checklist"]["target_dirs"], ignore_filter=ignore_filter)

# 5. Generate LLM prompt for AI Agents
prompt = generate_llm_prompt({"language": lang_results, "hardcoded": secret_results})
print(prompt)
```
