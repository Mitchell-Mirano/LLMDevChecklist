#!/usr/bin/env python3
"""Module to consolidate and clean Python top-level imports.

Also detects inline imports inside functions/methods for audit warnings.
"""

import ast
import sys
from pathlib import Path
from typing import Optional, List, Tuple
from .gitignore import GitIgnoreFilter


class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: List[Tuple[ast.AST, bool, bool]] = []
        self.inline_imports: List[Tuple[ast.AST, str]] = []  # (node, scope_description)
        self.current_scope: List[str] = ["module"]
        self.in_module_try_except: bool = False
        self.saw_sys_path_setup: bool = False

    def visit_Expr(self, node):
        try:
            code_str = ast.unparse(node)
            if "sys.path" in code_str or "load_dotenv" in code_str:
                self.saw_sys_path_setup = True
        except Exception:
            pass
        self.generic_visit(node)

    def visit_Try(self, node):
        prev_try = self.in_module_try_except
        if self.current_scope == ["module"]:
            self.in_module_try_except = True
        self.generic_visit(node)
        self.in_module_try_except = prev_try

    def visit_FunctionDef(self, node):
        self.current_scope.append(f"func_{node.name}")
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_AsyncFunctionDef(self, node):
        self.current_scope.append(f"async_func_{node.name}")
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_ClassDef(self, node):
        self.current_scope.append(f"class_{node.name}")
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_Import(self, node):
        is_top = (self.current_scope == ["module"]) and not self.saw_sys_path_setup
        is_guarded = self.in_module_try_except or self.saw_sys_path_setup
        self.imports.append((node, is_top, is_guarded))
        if self.current_scope != ["module"]:
            scope_desc = self.current_scope[-1]
            self.inline_imports.append((node, scope_desc))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        is_top = (self.current_scope == ["module"]) and not self.saw_sys_path_setup
        is_guarded = self.in_module_try_except or self.saw_sys_path_setup
        self.imports.append((node, is_top, is_guarded))
        if self.current_scope != ["module"]:
            scope_desc = self.current_scope[-1]
            self.inline_imports.append((node, scope_desc))
        self.generic_visit(node)


def unparse_import(node: ast.AST) -> str:
    if isinstance(node, ast.Import):
        names = [f"{alias.name} as {alias.asname}" if alias.asname else alias.name for alias in node.names]
        return f"import {', '.join(names)}"
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        level = "." * node.level
        names = [f"{alias.name} as {alias.asname}" if alias.asname else alias.name for alias in node.names]
        return f"from {level}{module} import {', '.join(names)}"
    return ""


def clean_file_imports(filepath: Path, fix: bool = True) -> bool:
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except Exception:
        return False

    visitor = ImportVisitor()
    visitor.visit(tree)

    if not visitor.imports:
        return False

    lines = content.splitlines()
    remove_lines = set()
    unified_import_strings = []
    seen_imports = set()

    for node, is_top, is_guarded in visitor.imports:
        if not is_top or is_guarded:
            continue

        imp_str = unparse_import(node)
        if imp_str:
            if imp_str not in seen_imports:
                seen_imports.add(imp_str)
                unified_import_strings.append(imp_str)

            for lineno in range(node.lineno, node.end_lineno + 1):
                remove_lines.add(lineno)

    if not remove_lines:
        return False

    if not fix:
        return True

    insert_idx = 0
    in_docstring = False
    docstring_quote = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if idx == 0 and (stripped.startswith("#!") or "coding" in stripped):
            insert_idx = idx + 1
            continue

        if not stripped or stripped.startswith("#"):
            if insert_idx == idx:
                insert_idx = idx + 1
            continue

        if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            quote = stripped[:3]
            if stripped.count(quote) >= 2 and len(stripped) > 3:
                insert_idx = idx + 1
                continue
            else:
                in_docstring = True
                docstring_quote = quote
                continue

        if in_docstring:
            if docstring_quote and docstring_quote in stripped:
                in_docstring = False
                insert_idx = idx + 1
            continue

        break

    new_lines = []
    for idx, line in enumerate(lines, start=1):
        if idx in remove_lines:
            continue
        new_lines.append(line)

    import_block = "\n".join(unified_import_strings)
    result_lines = new_lines[:insert_idx] + [import_block] + new_lines[insert_idx:]
    new_content = "\n".join(result_lines) + "\n"

    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return True

    return False


def detect_inline_imports(filepath: Path, root_dir: Optional[Path] = None) -> List[dict]:
    """Detect imports inside functions/methods (not at module top-level).
    
    Returns a list of findings with file, line_no, scope, and import_statement.
    These are audit-only warnings — inline imports may be intentional (lazy loading,
    circular dependency guards).
    """
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except Exception:
        return findings

    visitor = ImportVisitor()
    visitor.visit(tree)

    root = (root_dir or Path.cwd()).resolve()
    rel_path = str(filepath.relative_to(root) if root in filepath.parents else filepath)

    for node, scope_desc in visitor.inline_imports:
        imp_str = unparse_import(node)
        if imp_str:
            findings.append({
                "file": rel_path,
                "line_no": node.lineno,
                "scope": scope_desc,
                "import_statement": imp_str,
            })

    return findings


def clean_py_imports(
    target_dirs: Optional[List[str]] = None,
    fix: bool = True,
    ignore_filter: Optional[GitIgnoreFilter] = None,
    root_dir: Optional[Path] = None
) -> dict:
    root = (root_dir or Path.cwd()).resolve()
    if ignore_filter is None:
        ignore_filter = GitIgnoreFilter(root)

    if not target_dirs:
        candidates = [root / "backend", root / "app", root]
        target_dirs = [str(c) for c in candidates if c.exists()] or [str(root)]

    modified_files = []
    all_inline_imports = []
    total_files = 0

    for target in target_dirs:
        path = Path(target)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue

        files = [path] if path.is_file() else path.glob("**/*.py")
        for filepath in files:
            if filepath.is_dir() or ignore_filter.is_ignored(filepath):
                continue

            total_files += 1
            if clean_file_imports(filepath, fix=fix):
                modified_files.append(str(filepath.relative_to(root) if root in filepath.parents else filepath))
            
            inline = detect_inline_imports(filepath, root_dir=root)
            all_inline_imports.extend(inline)

    return {
        "total_files": total_files,
        "modified_count": len(modified_files),
        "modified_files": modified_files,
        "inline_imports": all_inline_imports,
    }


def main():
    fix_mode = "--check" not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    res = clean_py_imports(target_dirs=args, fix=fix_mode)
    print(f"✨ Python Import Cleanup ({'FIX' if fix_mode else 'CHECK'}): Scanned {res['total_files']} files. Modified: {res['modified_count']}.")
    for f in res["modified_files"]:
        print(f"   • {f}")


if __name__ == "__main__":
    main()
