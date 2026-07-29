#!/usr/bin/env python3
"""Module to scan Vue 3 (.vue), TypeScript (.ts), and JavaScript (.js) files to:
  1. Consolidate duplicate imports from the same source module.
  2. Detect unused imported symbols.
  3. Clean up and re-format imports in <script> blocks.
"""

import re
import sys
from pathlib import Path
from typing import Optional, List, Tuple
from .gitignore import GitIgnoreFilter

IMPORT_REGEX = re.compile(
    r'import\s+(?:(?P<default>[a-zA-Z0-9_$]+)\s*,?\s*)?(?:\{\s*(?P<named>[^}]+)\s*\})?\s*from\s*["\'](?P<module>[^"\']+)["\'];?',
    re.MULTILINE
)


def extract_script_content(content: str, is_vue: bool):
    if not is_vue:
        return content, None, None

    script_match = re.search(r'(<script[^>]*>)([\s\S]*?)(</script>)', content, re.IGNORECASE)
    if script_match:
        tag_open = script_match.group(1)
        script_body = script_match.group(2)
        tag_close = script_match.group(3)
        return script_body, script_match.span(2), (tag_open, tag_close)
    return "", None, None


def parse_and_clean_imports(content: str, full_file_text: str, fix_mode: bool = False):
    imports_by_module = {}
    spans_to_remove = []
    unused_symbols = []

    for match in IMPORT_REGEX.finditer(content):
        spans_to_remove.append(match.span())
        mod = match.group("module")
        default_imp = match.group("default")
        named_raw = match.group("named")

        if mod not in imports_by_module:
            imports_by_module[mod] = {"default": None, "named": set()}

        if default_imp:
            imports_by_module[mod]["default"] = default_imp

        if named_raw:
            for item in named_raw.split(","):
                clean_item = item.strip()
                if clean_item:
                    parts = clean_item.split(" as ")
                    local_name = parts[-1].strip()
                    imports_by_module[mod]["named"].add((clean_item, local_name))

    if not imports_by_module:
        return content, False, []

    content_sans_imports = IMPORT_REGEX.sub('', full_file_text)
    cleaned_imports_code = []

    for mod, data in sorted(imports_by_module.items()):
        used_default = None
        if data["default"]:
            def_name = data["default"]
            matches = len(re.findall(r'\b' + re.escape(def_name) + r'\b', content_sans_imports))
            if matches > 0:
                used_default = def_name
            else:
                unused_symbols.append((mod, def_name))

        used_named = []
        for orig_str, local_name in sorted(data["named"], key=lambda x: x[1]):
            matches = len(re.findall(r'\b' + re.escape(local_name) + r'\b', content_sans_imports))
            if matches > 0:
                used_named.append(orig_str)
            else:
                unused_symbols.append((mod, local_name))

        if used_default or used_named:
            parts = []
            if used_default:
                parts.append(used_default)
            if used_named:
                parts.append("{ " + ", ".join(used_named) + " }")
            
            imp_stmt = f"import {', '.join(parts)} from '{mod}'"
            cleaned_imports_code.append(imp_stmt)

    if fix_mode:
        new_script = IMPORT_REGEX.sub('', content).strip()
        new_imports_block = "\n".join(cleaned_imports_code)
        
        if new_imports_block:
            new_content = (new_imports_block + "\n\n" + new_script) if new_script else new_imports_block
        else:
            new_content = new_script
            
        if new_content.strip() != content.strip():
            return new_content.strip(), True, unused_symbols

    return content, False, unused_symbols


def process_file(filepath: Path, fix_mode: bool):
    is_vue = filepath.suffix == ".vue"
    try:
        full_text = filepath.read_text(encoding="utf-8")
    except Exception:
        return False, []

    script_body, span, tags = extract_script_content(full_text, is_vue)
    if is_vue and not script_body:
        return False, []

    target_content = script_body if is_vue else full_text
    new_target, modified, unused = parse_and_clean_imports(target_content, full_text, fix_mode)

    if fix_mode and modified:
        if is_vue:
            updated_full = full_text[:span[0]] + "\n" + new_target + "\n" + full_text[span[1]:]
        else:
            updated_full = new_target + "\n"

        if updated_full != full_text:
            filepath.write_text(updated_full, encoding="utf-8")
            return True, unused

    return False, unused


def clean_vue_imports(
    target_dirs: Optional[List[str]] = None,
    fix: bool = True,
    ignore_filter: Optional[GitIgnoreFilter] = None,
    root_dir: Optional[Path] = None
) -> dict:
    root = (root_dir or Path.cwd()).resolve()
    if ignore_filter is None:
        ignore_filter = GitIgnoreFilter(root)

    if not target_dirs:
        candidates = [root / "frontend" / "src", root / "src", root]
        target_dirs = [str(c) for c in candidates if c.exists()] or [str(root)]

    total_files = 0
    modified_files = []
    all_unused = []

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
            if filepath.suffix not in (".vue", ".ts", ".js"):
                continue

            total_files += 1
            mod, unused = process_file(filepath, fix)
            if mod:
                modified_files.append(str(filepath.relative_to(root) if root in filepath.parents else filepath))
            if unused:
                all_unused.extend(unused)

    return {
        "total_files": total_files,
        "modified_count": len(modified_files),
        "modified_files": modified_files,
        "unused_imports": all_unused
    }


def main():
    fix_mode = "--check" not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    res = clean_vue_imports(target_dirs=args, fix=fix_mode)
    print(f"🧹 Vue/TS/JS Import Cleanup ({'FIX' if fix_mode else 'CHECK'}): Scanned {res['total_files']} files. Modified: {res['modified_count']}.")
    for f in res["modified_files"]:
        print(f"   • {f}")


if __name__ == "__main__":
    main()
