#!/usr/bin/env python3
"""CLI Entrypoint for Dev Quality Checklist.

Separates:
  1. Auto-Fixers (Deterministic automatic code cleaners like import consolidation)
  2. LLM Diagnostic Auditors (Context-aware reports formatted as LLM prompts for AI Agents)
  3. Config Initializer (Generates checklist.toml for project-specific settings)
"""

import argparse
import json
import sys
from pathlib import Path
from .gitignore import GitIgnoreFilter
from .config import load_config, init_config_file
from .py_imports import clean_py_imports
from .vue_imports import clean_vue_imports
from .check_code_language import check_code_language
from .check_hardcoded import check_hardcoded
from .verify_docs import verify_docs
from . import generate_llm_prompt


def main():
    parser = argparse.ArgumentParser(
        prog="checklist",
        description="🛠️ LLM Dev Quality Checklist: Automated import fixers & AI-agent diagnostic auditors."
    )

    subparsers = parser.add_subparsers(dest="mode", help="Command mode to execute")

    # Command: init
    subparsers.add_parser(
        "init",
        help="[Setup] Create default checklist.toml configuration file in project root (auto-detects project structure)"
    )

    # Command: fix
    fix_parser = subparsers.add_parser(
        "fix",
        help="[File Modifying] Run deterministic auto-fixers (consolidate & clean Python/Vue/TS/JS imports)"
    )
    fix_parser.add_argument("paths", nargs="*", help="Specific files or directories to fix (default: from config)")
    fix_parser.add_argument("--dry-run", action="store_true", help="Preview files that would be modified without changing them")
    fix_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed list of modified files")
    fix_parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore rules exclusion")

    # Command: audit
    audit_parser = subparsers.add_parser(
        "audit",
        help="[Read Only] Run context-aware diagnostic auditors (Spanish naming/comments, hardcoded secrets, doc alignment, inline imports)"
    )
    audit_parser.add_argument("paths", nargs="*", help="Specific files or directories to audit (default: from config)")
    audit_parser.add_argument("--format", choices=["text", "json", "llm"], default="text", help="Output format: text (default), json, or llm (Markdown action prompt)")
    audit_parser.add_argument("--llm", action="store_true", help="Shortcut for --format llm")
    audit_parser.add_argument("--verbose", "-v", action="store_true", help="Print line-by-line detailed findings in terminal")
    audit_parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore rules exclusion")

    # Command: run (Default combination)
    all_parser = subparsers.add_parser(
        "run",
        help="[Combined] Run auto-fixers first, followed by diagnostic auditors"
    )
    all_parser.add_argument("paths", nargs="*", help="Specific files or directories to process (default: from config)")
    all_parser.add_argument("--dry-run", action="store_true", help="Preview fixes without modifying files")
    all_parser.add_argument("--format", choices=["text", "json", "llm"], default="text", help="Output format: text (default), json, or llm (Markdown action prompt)")
    all_parser.add_argument("--llm", action="store_true", help="Shortcut for --format llm")
    all_parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed file-by-file results")
    all_parser.add_argument("--no-gitignore", action="store_true", help="Disable .gitignore rules exclusion")

    args = parser.parse_args()

    root = Path.cwd()

    # Handle init subcommand
    if args.mode == "init":
        init_config_file(root)
        sys.exit(0)

    mode = args.mode or "run"

    # Load project configuration
    cfg = load_config(root)
    chk_cfg = cfg.get("checklist", {})

    # Resolve target paths
    cli_paths = getattr(args, "paths", [])
    if cli_paths:
        target_dirs = cli_paths
    else:
        configured_dirs = chk_cfg.get("target_dirs", ["backend", "frontend/src", "scripts"])
        target_dirs = [d for d in configured_dirs if (root / d).exists() or Path(d).exists()]
        if not target_dirs:
            target_dirs = ["."]

    no_gitignore = getattr(args, "no_gitignore", False) or not chk_cfg.get("use_gitignore", True)
    dry_run = getattr(args, "dry_run", False)
    verbose = getattr(args, "verbose", False)

    # Resolve output format: --llm flag is a shortcut for --format llm
    output_format = getattr(args, "format", "text")
    if getattr(args, "llm", False):
        output_format = "llm"

    ignore_filter = None if no_gitignore else GitIgnoreFilter(root)

    # JSON mode: suppress banner output
    is_json = output_format == "json"

    if not is_json:
        print("======================================================================")
        print(f"🛠️  LLM DEV CHECKLIST SUITE — Mode: {mode.upper()}")
        print("======================================================================")
        print(f"📍 Root Directory: {root}")
        print(f"🎯 Target Paths:   {', '.join(target_dirs)}")
        print(f"🛡️  .gitignore Filter: {'Disabled' if no_gitignore else 'Enabled'}")
        if dry_run:
            print("⚠️  Dry Run Active: No files will be modified on disk.")
        print("----------------------------------------------------------------------\n")

    json_output = {}

    # ── CATEGORY 1: AUTOMATED FIXERS ──────────────────────────────────────────
    if mode in ("fix", "run"):
        fix_action_label = "Checking for import cleanups (Dry Run)" if dry_run else "Executing Import Auto-Fixers"
        if not is_json:
            print(f"⚡ [1/2] {fix_action_label}...")

        py_res = clean_py_imports(target_dirs=target_dirs, fix=not dry_run, ignore_filter=ignore_filter, root_dir=root)
        if not is_json:
            print(f"   • Python Imports: Scanned {py_res['total_files']} files | Modified/Fixable: {py_res['modified_count']}")
            if py_res.get("inline_imports"):
                print(f"   • ⚠️  Inline Imports Detected: {len(py_res['inline_imports'])} import(s) inside functions/methods")
            if verbose and py_res['modified_files']:
                for f in py_res['modified_files']:
                    print(f"     └─ [Py Import] {f}")

        vue_res = clean_vue_imports(target_dirs=target_dirs, fix=not dry_run, ignore_filter=ignore_filter, root_dir=root)
        if not is_json:
            print(f"   • Vue/TS/JS Imports: Scanned {vue_res['total_files']} files | Modified/Fixable: {vue_res['modified_count']}")
            if verbose and vue_res['modified_files']:
                for f in vue_res['modified_files']:
                    print(f"     └─ [Vue/JS Import] {f}")
            print()

        json_output["fix"] = {
            "py_imports": py_res,
            "vue_imports": vue_res,
        }

    # ── CATEGORY 2: LLM DIAGNOSTIC AUDITORS ──────────────────────────────────
    if mode in ("audit", "run"):
        if not is_json:
            print("🧠 [2/2] Running Context-Aware Diagnostic Auditors...")

        lang_res = check_code_language(target_dirs=target_dirs, ignore_filter=ignore_filter, root_dir=root)
        hard_res = check_hardcoded(target_dirs=target_dirs, ignore_filter=ignore_filter, root_dir=root)
        docs_res = verify_docs(root_dir=root)

        # Collect inline import warnings from fix step or run fresh
        inline_imports = []
        if "fix" in json_output:
            inline_imports = json_output["fix"]["py_imports"].get("inline_imports", [])
        else:
            py_scan = clean_py_imports(target_dirs=target_dirs, fix=False, ignore_filter=ignore_filter, root_dir=root)
            inline_imports = py_scan.get("inline_imports", [])

        audit_results = {
            "language": lang_res,
            "hardcoded": hard_res,
            "docs": docs_res,
            "inline_imports": inline_imports,
        }

        if is_json:
            json_output["audit"] = audit_results
        elif output_format == "llm":
            print("\n" + "=" * 70)
            print(generate_llm_prompt(audit_results))
            print("=" * 70)
        else:
            print(f"   • 🌐 Language & Naming Audit:    {lang_res['total_issues']} finding(s) across {lang_res['flagged_files_count']} file(s)")
            print(f"   • 🔍 Hardcoded Secrets/IP Audit: {hard_res['total_issues']} finding(s) across {hard_res['flagged_files_count']} file(s)")
            print(f"   • 📚 Documentation Align Audit:  {docs_res['total_issues']} discrepancy(s)")
            print(f"   • 📦 Inline Import Warnings:     {len(inline_imports)} import(s) inside functions/methods")

            if verbose:
                if lang_res["issues_by_file"]:
                    print("\n--- 🌐 Language Findings (Verbose) ---")
                    for path, issues in lang_res["issues_by_file"].items():
                        print(f"  📄 {path}")
                        for lno, cat, details in issues:
                            print(f"     Line {lno} [{cat}]: {details}")
                if hard_res["issues_by_file"]:
                    print("\n--- 🔍 Secrets Findings (Verbose) ---")
                    for path, issues in hard_res["issues_by_file"].items():
                        print(f"  📄 {path}")
                        for issue in issues:
                            print(f"     Line {issue['line_no']} [{issue['type']}]: {issue['matched']}")
                if inline_imports:
                    print("\n--- 📦 Inline Import Warnings (Verbose) ---")
                    for imp in inline_imports:
                        print(f"  📄 {imp['file']}:{imp['line_no']} [{imp['scope']}]: {imp['import_statement']}")

            print("\n💡 Tip: Run `checklist audit --format llm` for an AI Agent action prompt, or `--format json` for CI/CD integration!")

    # ── JSON OUTPUT ───────────────────────────────────────────────────────────
    if is_json:
        print(json.dumps(json_output, indent=2, default=str))


if __name__ == "__main__":
    main()
