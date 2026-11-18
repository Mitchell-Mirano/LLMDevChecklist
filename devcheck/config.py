"""Configuration module for the checklist library.

Loads settings from checklist.toml or pyproject.toml [tool.checklist].
"""

from pathlib import Path
from typing import Dict, Any, Optional
from .design.tokens import discover_tokens_files
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


DEFAULT_CONFIG = {
    "checklist": {
        "use_gitignore": True,
        "target_dirs": ["backend", "frontend/src", "scripts"],
        "exclude_dirs": [".git", ".venv", "venv", "node_modules", "dist", "site", "__pycache__", "mongo-data"],
        "exclude_files": ["vite.config.js"],
    },
    "auto_fixers": {
        "py_imports": True,
        "vue_imports": True,
    },
    "auditors": {
        "language": True,
        "hardcoded": True,
        "docs": True,
        "design": True,
    },
    "language": {
        "strict_english": True,
        "custom_allowed_words": [],
    },
    "hardcoded": {
        "allow_localhost": True,
    },
    "design": {
        "tokens_files": [],
        "extensions": [".vue", ".css", ".scss", ".tsx", ".jsx", ".svelte", ".html"],
        "min_contrast_aa": 4.5,
        "min_contrast_large": 3.0,
        "contrast_pairs": [],
        "allowed_unicode": [],
        "max_z_index": 100,
        "icon_library": "",
        "rules": {
            "hardcoded_colors": True,
            "undefined_tokens": True,
            "duplicate_tokens": True,
            "contrast": True,
            "unicode_icons": True,
            "svg_viewbox": True,
            "inline_styles": True,
            "important": True,
            "hardcoded_font": True,
            "z_index_magic": True,
            "a11y_basic": True,
        },
    }
}

DEFAULT_TOML_TEMPLATE = """# 🛠️ Checklist Configuration (checklist.toml)

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
design = true

[checklist.language]
strict_english = true
custom_allowed_words = ["gptw", "nps", "rut"]

[checklist.hardcoded]
allow_localhost = true

[checklist.design]
# Leave tokens_files empty to auto-detect main.css / tokens.css / variables.css
tokens_files = []
extensions = [".vue", ".css", ".scss", ".tsx", ".jsx", ".svelte", ".html"]
min_contrast_aa = 4.5
max_z_index = 100
icon_library = ""
"""


def load_config(root_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Loads configuration from checklist.toml or pyproject.toml [tool.checklist]."""
    root = (root_dir or Path.cwd()).resolve()
    config = {
        "checklist": dict(DEFAULT_CONFIG["checklist"]),
        "auto_fixers": dict(DEFAULT_CONFIG["auto_fixers"]),
        "auditors": dict(DEFAULT_CONFIG["auditors"]),
        "language": dict(DEFAULT_CONFIG["language"]),
        "hardcoded": dict(DEFAULT_CONFIG["hardcoded"]),
        "design": {
            **DEFAULT_CONFIG["design"],
            "rules": dict(DEFAULT_CONFIG["design"]["rules"]),
        },
    }

    # 1. Try checklist.toml in project root
    custom_toml = root / "checklist.toml"
    if custom_toml.exists():
        try:
            data = tomllib.loads(custom_toml.read_text(encoding="utf-8"))
            _merge_config(config, data)
            return config
        except Exception as e:
            print(f"⚠️ Error parsing checklist.toml: {e}")

    # 2. Try pyproject.toml [tool.checklist]
    pyproject_toml = root / "pyproject.toml"
    if pyproject_toml.exists():
        try:
            data = tomllib.loads(pyproject_toml.read_text(encoding="utf-8"))
            if "tool" in data and "checklist" in data["tool"]:
                _merge_config(config, data["tool"]["checklist"])
                return config
        except Exception:
            pass

    return config


def _merge_config(base: dict, overlay: dict):
    for key, value in overlay.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _merge_config(base[key], value)
        else:
            base[key] = value


# Common project directory patterns to auto-detect
_KNOWN_DIR_PATTERNS = [
    "backend", "frontend/src", "frontend", "src", "app", "lib", "scripts",
    "api", "server", "packages", "modules",
]


def detect_target_dirs(root_dir: Path) -> list:
    """Scan project root for common directory patterns and return existing ones.
    
    Falls back to ["."] if no known patterns are found.
    """
    root = root_dir.resolve()
    found = []
    for pattern in _KNOWN_DIR_PATTERNS:
        candidate = root / pattern
        if candidate.is_dir():
            found.append(pattern)
    return found or ["."]


def _generate_toml_content(target_dirs: list, tokens_files: Optional[list] = None) -> str:
    """Generate checklist.toml content with the given target_dirs."""
    dirs_str = ", ".join(f'"{d}"' for d in target_dirs)
    tokens_str = ", ".join(f'"{t}"' for t in (tokens_files or []))
    return f"""# 🛠️ Checklist Configuration (checklist.toml)

[checklist]
use_gitignore = true
target_dirs = [{dirs_str}]
exclude_dirs = [".git", ".venv", "venv", "node_modules", "dist", "site", "__pycache__", "mongo-data"]
exclude_files = ["vite.config.js"]

[checklist.auto_fixers]
py_imports = true
vue_imports = true

[checklist.auditors]
language = true
hardcoded = true
docs = true
design = true

[checklist.language]
strict_english = true
custom_allowed_words = ["gptw", "nps", "rut"]

[checklist.hardcoded]
allow_localhost = true

[checklist.design]
# Auto-detected or manual token CSS files (main.css / tokens.css / variables.css)
tokens_files = [{tokens_str}]
extensions = [".vue", ".css", ".scss", ".tsx", ".jsx", ".svelte", ".html"]
min_contrast_aa = 4.5
max_z_index = 100
icon_library = ""
"""


def init_config_file(root_dir: Optional[Path] = None) -> Path:
    """Creates a checklist.toml with auto-detected target directories."""
    root = (root_dir or Path.cwd()).resolve()
    toml_path = root / "checklist.toml"
    if not toml_path.exists():
        detected_dirs = detect_target_dirs(root)
        detected_tokens = [
            str(p.relative_to(root)) for p in discover_tokens_files(root) if root in p.parents
        ]
        content = _generate_toml_content(detected_dirs, detected_tokens)
        toml_path.write_text(content, encoding="utf-8")
        print(f"✨ Created configuration file at: {toml_path}")
        print(f"   Auto-detected target directories: {detected_dirs}")
        if detected_tokens:
            print(f"   Auto-detected design tokens: {detected_tokens}")
    else:
        print(f"ℹ️ Configuration file already exists at: {toml_path}")
    return toml_path
