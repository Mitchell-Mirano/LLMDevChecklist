#!/usr/bin/env python3
"""Script to audit codebase documentation completeness against actual implementation.

Scans:
  1. Public Backend & Frontend modules (excluding internal folders like /checklist, /scripts)
  2. Root deployment scripts (deploy.sh, deploy_job.sh)
  3. Environment variables (in config.py and .env files)
  4. Database collections & Pydantic schemas

Configurable Exclusions:
  - EXCLUDED_DIRS: List of root-level internal directories excluded from public documentation requirements.
  - EXCLUDED_FILES: Tooling/utility file names ignored during stale reference checks.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Carpetas en la raíz del proyecto que contienen herramientas o scripts internos y NO requieren documentación pública
EXCLUDED_DIRS = [
    "checklist",       # Scripts de verificación e inspección interna
    "scripts",         # Scripts internos de soporte, migración y mantenimiento en la raíz
    ".git",            # Control de versiones
    ".venv",           # Entorno virtual de Python
    "node_modules",    # Módulos de Node.js
    "site",            # Artefactos compilados de MkDocs
    "dist",            # Artefactos compilados del Frontend
    "__pycache__",     # Caché de ejecución de Python
    "mongo-data"       # Volumen local de datos de MongoDB
]

# Nombres de archivos utilitarios o palabras clave técnicas a ignorar
EXCLUDED_FILES = {
    "check_code_language.py", "check_hardcoded.py", "verify_docs.py", 
    "gitignore.py", "py_imports.py", "vue_imports.py", "cli.py",
    "vite.config.js", "Node.js", "Vue.js", "chart.js"
}

# Términos técnicos o variables no aplicables como variables de entorno activas
EXCLUDED_ENV_WORDS = {
    "HTTP", "JSON", "UTF", "POST", "GET", "PUT", "DELETE", "HTML", "CORS", 
    "NPS", "GPTW", "REST", "SPA", "JWT", "RBAC", "UUID", "RUT", "URL", 
    "DTO", "Pydantic", "FastAPI", "MongoDB", "RHEL", "RAM", "CPU", "SSD", "LTS",
    "API", "SMTP", "PNG", "BASE", "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USERNAME",
    "EMAIL_PASSWORD", "GCP_SERVICE_ACCOUNT_FILE", "ENVIRONMENT", "DATABASE_URL"
}


def is_path_excluded(path: Path, root_dir: Path) -> bool:
    """Verifica si una ruta pertenece a una carpeta raíz excluida de la auditoría pública."""
    try:
        rel = path.relative_to(root_dir)
        first_part = rel.parts[0] if rel.parts else ""
        if first_part in EXCLUDED_DIRS or (first_part.startswith(".") and first_part != "."):
            return True
    except ValueError:
        pass
    return False


def load_documentation_text(root_dir: Path) -> Dict[str, str]:
    """Lee todos los archivos markdown de docs/ y el README.md de la raíz."""
    docs = {}
    docs_dir = root_dir / "docs"
    
    readme = root_dir / "README.md"
    if readme.exists():
        docs["README.md"] = readme.read_text(encoding="utf-8", errors="ignore")

    if docs_dir.exists():
        for md_file in docs_dir.glob("**/*.md"):
            if not is_path_excluded(md_file, root_dir):
                rel_path = md_file.relative_to(root_dir)
                docs[str(rel_path)] = md_file.read_text(encoding="utf-8", errors="ignore")
            
    return docs


def audit_modules(docs_dict: dict, root_dir: Path) -> dict:
    """Audita los módulos de código público y scripts de despliegue contra la documentación."""
    combined_docs_text = "\n".join(docs_dict.values())
    backend_dir = root_dir / "backend" / "app"
    frontend_dir = root_dir / "frontend" / "src"

    # 1. Módulos Backend Públicos (excluyendo tests, __init__)
    backend_files = {}
    if backend_dir.exists():
        for py_file in backend_dir.glob("**/*.py"):
            if py_file.name == "__init__.py" or "pycache" in str(py_file) or py_file.name.startswith("test_"):
                continue
            rel = py_file.relative_to(root_dir)
            backend_files[py_file.name] = str(rel)

    # 2. Módulos Frontend Públicos
    frontend_files = {}
    if frontend_dir.exists():
        for fe_file in frontend_dir.glob("**/*"):
            if fe_file.is_file() and fe_file.suffix in (".vue", ".js", ".ts"):
                rel = fe_file.relative_to(root_dir)
                frontend_files[fe_file.name] = str(rel)

    # 3. Scripts de Despliegue en la Raíz
    root_deploy_scripts = {}
    for sh_file in root_dir.glob("*.sh"):
        if sh_file.is_file():
            root_deploy_scripts[sh_file.name] = sh_file.name

    # 4. Detectar módulos no documentados en código
    undocumented_backend = []
    for name, path in sorted(backend_files.items()):
        if name not in combined_docs_text and path not in combined_docs_text:
            undocumented_backend.append((name, path))

    undocumented_frontend = []
    for name, path in sorted(frontend_files.items()):
        if name not in combined_docs_text and path not in combined_docs_text:
            undocumented_frontend.append((name, path))

    undocumented_deploy_scripts = []
    for name, path in sorted(root_deploy_scripts.items()):
        if name not in combined_docs_text and path not in combined_docs_text:
            undocumented_deploy_scripts.append((name, path))

    # 5. Detectar menciones a archivos eliminados / obsoletos en la documentación
    doc_file_refs = set(re.findall(r'\b[A-Za-z0-9_-]+\.(?:py|vue|js|ts|sh)\b', combined_docs_text))
    existing_file_names = set(backend_files.keys()).union(set(frontend_files.keys())).union(set(root_deploy_scripts.keys()))
    
    stale_doc_modules = sorted([
        name for name in doc_file_refs 
        if name not in existing_file_names and name not in EXCLUDED_FILES
    ])

    return {
        "undocumented_backend": undocumented_backend,
        "undocumented_frontend": undocumented_frontend,
        "undocumented_deploy_scripts": undocumented_deploy_scripts,
        "stale_doc_modules": stale_doc_modules,
        "total_backend_count": len(backend_files),
        "total_frontend_count": len(frontend_files),
        "total_deploy_script_count": len(root_deploy_scripts)
    }


def audit_environment_variables(docs_dict: dict, root_dir: Path) -> dict:
    """Audita las variables de entorno configuradas contra la documentación."""
    combined_docs_text = "\n".join(docs_dict.values())
    code_env_vars = set()
    backend_dir = root_dir / "backend" / "app"
    
    config_file = backend_dir / "core" / "config.py"
    if config_file.exists():
        content = config_file.read_text(encoding="utf-8")
        aliases = re.findall(r'validation_alias=["\']([A-Z0-9_]+)["\']', content)
        code_env_vars.update(aliases)
        
        fields = re.findall(r'([A-Z0-9_]+)\s*:\s*(?:str|int|bool|List)', content)
        code_env_vars.update(fields)

    if backend_dir.exists():
        for py_file in backend_dir.glob("**/*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            getenvs = re.findall(r'os\.getenv\(["\']([A-Z0-9_]+)["\']', content)
            code_env_vars.update(getenvs)

    code_env_vars = {v for v in code_env_vars if v and not v.startswith("_")}
    undocumented_env_vars = sorted([v for v in code_env_vars if v not in combined_docs_text])

    doc_table_env_vars = set(re.findall(r'`([A-Z0-9_]{3,})`', combined_docs_text))
    stale_env_vars = sorted([
        v for v in doc_table_env_vars 
        if v not in code_env_vars and v not in EXCLUDED_ENV_WORDS and not v.isdigit()
    ])

    return {
        "code_env_vars": sorted(list(code_env_vars)),
        "undocumented_env_vars": undocumented_env_vars,
        "stale_env_vars": stale_env_vars
    }


def audit_database_schemas(docs_dict: dict) -> dict:
    """Audita las colecciones y esquemas MongoDB contra la documentación."""
    combined_docs_text = "\n".join(docs_dict.values())
    
    known_collections = {
        "users", "surveys", "processes", "questions", "email_logs", 
        "frentes", "factors", "areas", "gptw_levels", "survey_progress", 
        "action_plans", "area_insights", "nlp", "roles"
    }

    doc_collections = set(re.findall(r'[Cc]olección `([a-z_]+)`', combined_docs_text))

    undocumented_collections = sorted([c for c in known_collections if c not in doc_collections and f"`{c}`" not in combined_docs_text])
    stale_doc_collections = sorted([c for c in doc_collections if c not in known_collections])

    return {
        "known_collections": sorted(list(known_collections)),
        "doc_collections": sorted(list(doc_collections)),
        "undocumented_collections": undocumented_collections,
        "stale_doc_collections": stale_doc_collections
    }


def verify_docs(root_dir: Optional[Path] = None) -> dict:
    root = (root_dir or Path.cwd()).resolve()
    docs_dict = load_documentation_text(root)
    if not docs_dict:
        return {"total_issues": 0, "modules": {}, "env_vars": {}, "database": {}}

    mod_result = audit_modules(docs_dict, root)
    env_result = audit_environment_variables(docs_dict, root)
    db_result = audit_database_schemas(docs_dict)

    total_issues = (
        len(mod_result["stale_doc_modules"]) + 
        len(mod_result["undocumented_backend"]) + 
        len(mod_result["undocumented_frontend"]) + 
        len(mod_result["undocumented_deploy_scripts"]) + 
        len(env_result["undocumented_env_vars"]) + 
        len(db_result["undocumented_collections"])
    )

    return {
        "total_issues": total_issues,
        "modules": mod_result,
        "env_vars": env_result,
        "database": db_result
    }


def main():
    res = verify_docs()
    total_issues = res["total_issues"]
    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()
