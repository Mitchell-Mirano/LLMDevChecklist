#!/usr/bin/env python3
"""Module to audit codebase language conventions:
Ensures all code symbols (function names, class names, variable/parameter names)
and developer code comments (line & inline) are written in English instead of Spanish.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict
from .gitignore import GitIgnoreFilter

SPANISH_VERB_PATTERNS = [
    r'\bobtener_', r'\bcrear_', r'\bguardar_', r'\beliminar_', r'\bcalcular_',
    r'\bgenerar_', r'\bprocesar_', r'\bcargar_', r'\benviar_', r'\bbuscar_',
    r'\bvalidar_', r'\bactualizar_', r'\blimpiar_', r'\bconsultar_', r'\bdescargar_',
    r'Obtener\b', r'Crear\b', r'Guardar\b', r'Eliminar\b', r'Calcular\b',
    r'Generar\b', r'Procesar\b', r'Cargar\b', r'Enviar\b', r'Buscar\b'
]

SPANISH_NOUN_PATTERNS = [
    r'\busuario\b', r'\busuarios\b', r'\bfecha\b', r'\bfechas\b', r'\brespuesta\b',
    r'\brespuestas\b', r'\bpregunta\b', r'\bpreguntas\b', r'\bencuesta\b', r'\bencuestas\b',
    r'\bproceso\b', r'\bprocesos\b', r'\bcorreo\b', r'\bcorreos\b', r'\bclave\b',
    r'\bclaves\b', r'\bcontrasena\b', r'\bcontraseña\b', r'\bdatos\b', r'\btabla\b',
    r'\blista_\b', r'\brango\b', r'\bpromedio\b', r'\bcolaborador\b', r'\bcolaboradores\b',
    r'\bnombre_\b', r'\bestado_\b'
]

SPANISH_SYMBOL_REGEX = re.compile(
    "|".join(SPANISH_VERB_PATTERNS + SPANISH_NOUN_PATTERNS),
    re.IGNORECASE
)

SPANISH_COMMENT_WORDS = {
    "el", "la", "los", "las", "una", "unos", "unas", "de", "del", "en", "para",
    "por", "con", "sin", "sobre", "entre", "desde", "hasta", "hacia", "según", "durante",
    "mediante", "como", "más", "menos", "pero", "sino", "aunque", "donde", "cuando",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel", "aquella",
    "método", "metodo", "función", "funcion", "clase", "parámetro", "parametro", "retorna", "devuelve",
    "guarda", "obtiene", "calcula", "crea", "elimina", "actualiza", "consulta", "registro",
    "proceso", "usuario", "usuarios", "dinámico", "dinamico", "entorno", "inicial", "sembrado",
    "respuesta", "respuestas", "pregunta", "preguntas", "encuesta", "encuestas", "datos",
    "tabla", "lista", "rango", "promedio", "hacer", "recopilamos", "identificar", "quiénes",
    "quienes", "mismo", "misma", "lógica", "logica", "solicitud", "validar", "verificar", "comprobar",
    "cargar", "descargar", "generar", "limpiar", "despacho", "envío", "envio", "hitos", "duración",
    "duracion", "avance", "pendientes", "finalizado", "días", "dias", "aprox", "completaron",
    "elegibles", "participantes", "solamente", "ambos", "cada", "después", "despues", "antes",
    "luego", "todavía", "todavia", "siempre", "nunca", "ejemplo", "ejemplos", "archivo", "archivos",
    "carpeta", "ruta", "rutas", "salida", "entrada", "peticiones"
}


def extract_comments_from_line(line: str, is_python: bool = True):
    symbol = "#" if is_python else "//"
    if symbol in line:
        parts = line.split(symbol, 1)
        code_part = parts[0]
        single_quotes = code_part.count("'") % 2
        double_quotes = code_part.count('"') % 2
        if single_quotes == 0 and double_quotes == 0:
            return parts[1].strip()
    return None


def is_spanish_comment(comment_text: str) -> str:
    tokens = re.findall(r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]+\b', comment_text.lower())
    for token in tokens:
        if token in SPANISH_COMMENT_WORDS:
            return token
    return ""


def audit_python_file(filepath: Path):
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return issues

    lines = content.splitlines()

    for line_idx, line in enumerate(lines, start=1):
        comment = extract_comments_from_line(line, is_python=True)
        if comment:
            matched_word = is_spanish_comment(comment)
            if matched_word:
                issues.append((line_idx, f"Comment in Spanish ('{matched_word}')", line.strip()[:100]))

    try:
        tree = ast.parse(content)
        class SymbolVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                match = SPANISH_SYMBOL_REGEX.search(node.name)
                if match:
                    issues.append((node.lineno, f"Function Name ('{node.name}')", f"Contains Spanish term '{match.group(0)}'"))
                for arg in node.args.args:
                    arg_match = SPANISH_SYMBOL_REGEX.search(arg.arg)
                    if arg_match:
                        issues.append((node.lineno, f"Parameter Name ('{arg.arg}') in '{node.name}'", f"Contains Spanish term '{arg_match.group(0)}'"))
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

            def visit_ClassDef(self, node):
                match = SPANISH_SYMBOL_REGEX.search(node.name)
                if match:
                    issues.append((node.lineno, f"Class Name ('{node.name}')", f"Contains Spanish term '{match.group(0)}'"))
                self.generic_visit(node)

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    match = SPANISH_SYMBOL_REGEX.search(node.id)
                    if match and len(node.id) > 4:
                        issues.append((node.lineno, f"Variable Assignment ('{node.id}')", f"Contains Spanish term '{match.group(0)}'"))
                self.generic_visit(node)

        visitor = SymbolVisitor()
        visitor.visit(tree)
    except Exception:
        pass

    return issues


def audit_js_vue_file(filepath: Path):
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return issues

    is_vue = filepath.suffix == ".vue"
    if is_vue:
        script_match = re.search(r'<script[^>]*>([\s\S]*?)</script>', content, re.IGNORECASE)
        if not script_match:
            return issues
        script_text = script_match.group(1)
        base_line = content[:script_match.start(1)].count('\n') + 1
    else:
        script_text = content
        base_line = 1

    lines = script_text.splitlines()

    for i, line in enumerate(lines):
        line_no = base_line + i
        comment = extract_comments_from_line(line, is_python=False)
        if comment:
            matched_word = is_spanish_comment(comment)
            if matched_word:
                issues.append((line_no, f"JS/TS Comment in Spanish ('{matched_word}')", line.strip()[:100]))

        decl_match = re.search(r'\b(?:const|let|var|function|async function)\s+([a-zA-Z0-9_$]+)', line)
        if decl_match:
            symbol = decl_match.group(1)
            match = SPANISH_SYMBOL_REGEX.search(symbol)
            if match:
                issues.append((line_no, f"JS Symbol ('{symbol}')", f"Contains Spanish term '{match.group(0)}'"))

    return issues


def check_code_language(
    target_dirs: Optional[List[str]] = None,
    ignore_filter: Optional[GitIgnoreFilter] = None,
    root_dir: Optional[Path] = None
) -> dict:
    root = (root_dir or Path.cwd()).resolve()
    if ignore_filter is None:
        ignore_filter = GitIgnoreFilter(root)

    if not target_dirs:
        candidates = [root / "backend", root / "frontend" / "src", root]
        target_dirs = [str(c) for c in candidates if c.exists()] or [str(root)]

    total_files = 0
    issues_by_file: Dict[str, list] = {}

    for target in target_dirs:
        path = Path(target)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue

        files = [path] if path.is_file() else path.glob("**/*")
        for filepath in files:
            if filepath.is_dir() or ignore_filter.is_ignored(filepath):
                continue

            file_issues = []
            if filepath.suffix == ".py":
                total_files += 1
                file_issues = audit_python_file(filepath)
            elif filepath.suffix in (".vue", ".ts", ".js"):
                total_files += 1
                file_issues = audit_js_vue_file(filepath)

            if file_issues:
                rel_path = str(filepath.relative_to(root) if root in filepath.parents else filepath)
                issues_by_file[rel_path] = file_issues

    total_issues = sum(len(v) for v in issues_by_file.values())
    return {
        "total_files": total_files,
        "flagged_files_count": len(issues_by_file),
        "total_issues": total_issues,
        "issues_by_file": issues_by_file
    }


def main():
    args = sys.argv[1:]
    res = check_code_language(target_dirs=args)
    print("🌐 Auditing Codebase Language (Enforcing English Code Conventions)...\n")
    for file_path, issues in res["issues_by_file"].items():
        print(f"📁 \033[1m{file_path}\033[0m")
        for line_no, category, details in issues[:10]:
            print(f"   Line {line_no} [{category}]: {details}")
        if len(issues) > 10:
            print(f"   ... (+{len(issues) - 10} more warnings)")
        print()

    print(f"Summary: {res['total_issues']} notice(s) across {res['flagged_files_count']} file(s).")
    sys.exit(0 if res["total_issues"] == 0 else 1)


if __name__ == "__main__":
    main()
