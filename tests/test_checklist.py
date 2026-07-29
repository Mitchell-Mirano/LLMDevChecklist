import unittest
import tempfile
import shutil
import json
import subprocess
import sys
from pathlib import Path
from checklist import load_config, init_config_file, GitIgnoreFilter, clean_py_imports, clean_vue_imports, detect_inline_imports, check_code_language, check_hardcoded, generate_llm_prompt
from checklist.config import detect_target_dirs


class TestChecklistLibrary(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ── Config & Init ─────────────────────────────────────────────────────────

    def test_init_config(self):
        config_path = init_config_file(self.test_dir)
        self.assertTrue(config_path.exists())
        config = load_config(self.test_dir)
        self.assertIn("checklist", config)
        self.assertTrue(config["checklist"]["use_gitignore"])

    def test_smart_init_detects_dirs(self):
        """checklist init should auto-detect existing project directories."""
        (self.test_dir / "backend").mkdir()
        (self.test_dir / "src").mkdir()
        detected = detect_target_dirs(self.test_dir)
        self.assertIn("backend", detected)
        self.assertIn("src", detected)

    def test_smart_init_fallback(self):
        """Falls back to ['.'] when no known directories exist."""
        detected = detect_target_dirs(self.test_dir)
        self.assertEqual(detected, ["."])

    def test_smart_init_writes_detected_dirs(self):
        """Init should write detected dirs into checklist.toml content."""
        (self.test_dir / "app").mkdir()
        init_config_file(self.test_dir)
        content = (self.test_dir / "checklist.toml").read_text()
        self.assertIn('"app"', content)

    # ── Auto-Fixers ──────────────────────────────────────────────────────────

    def test_clean_py_imports(self):
        sample_py = self.test_dir / "sample.py"
        sample_py.write_text("import sys\nimport os\nimport sys\nprint('hello')\n", encoding="utf-8")

        res = clean_py_imports(target_dirs=[str(sample_py)], fix=True, root_dir=self.test_dir)
        self.assertEqual(res["modified_count"], 1)

        cleaned_content = sample_py.read_text(encoding="utf-8")
        self.assertIn("import sys", cleaned_content)
        self.assertIn("import os", cleaned_content)

    # ── Inline Import Detection ──────────────────────────────────────────────

    def test_detect_inline_imports(self):
        """Inline imports inside functions should be detected as audit warnings."""
        sample_py = self.test_dir / "inline_test.py"
        sample_py.write_text(
            "import os\n\ndef my_func():\n    import json\n    return json.dumps({})\n",
            encoding="utf-8"
        )
        findings = detect_inline_imports(sample_py, root_dir=self.test_dir)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["scope"], "func_my_func")
        self.assertIn("import json", findings[0]["import_statement"])

    def test_inline_imports_in_clean_py_result(self):
        """clean_py_imports should include inline_imports in result dict."""
        sample_py = self.test_dir / "test_inline.py"
        sample_py.write_text(
            "def startup():\n    from db import connect\n    connect()\n",
            encoding="utf-8"
        )
        res = clean_py_imports(target_dirs=[str(sample_py)], fix=False, root_dir=self.test_dir)
        self.assertIn("inline_imports", res)
        self.assertGreater(len(res["inline_imports"]), 0)

    # ── Auditors ─────────────────────────────────────────────────────────────

    def test_check_code_language(self):
        spanish_py = self.test_dir / "spanish.py"
        spanish_py.write_text("# Este es un comentario en espanol\ndef obtener_usuarios():\n    pass\n", encoding="utf-8")

        res = check_code_language(target_dirs=[str(spanish_py)], root_dir=self.test_dir)
        self.assertGreater(res["total_issues"], 0)

    def test_check_hardcoded(self):
        secret_py = self.test_dir / "secret.py"
        secret_py.write_text("API_KEY = 'secret_123456789'\n", encoding="utf-8")

        res = check_hardcoded(target_dirs=[str(secret_py)], root_dir=self.test_dir)
        self.assertGreater(res["total_issues"], 0)

    # ── LLM Prompt Generation ────────────────────────────────────────────────

    def test_generate_llm_prompt(self):
        audit_results = {
            "language": {"total_issues": 1, "issues_by_file": {"test.py": [(1, "Comment", "details")]}},
            "hardcoded": {"total_issues": 0, "issues_by_file": {}},
            "docs": {"total_issues": 0, "modules": {}},
        }
        prompt = generate_llm_prompt(audit_results)
        self.assertIn("# 🤖 Checklist Action Items for LLM / AI Assistant", prompt)

    def test_generate_llm_prompt_with_inline_imports(self):
        audit_results = {
            "language": {"total_issues": 0, "issues_by_file": {}},
            "hardcoded": {"total_issues": 0, "issues_by_file": {}},
            "docs": {"total_issues": 0, "modules": {}},
            "inline_imports": [
                {"file": "main.py", "line_no": 10, "scope": "func_startup", "import_statement": "from db import connect"}
            ],
        }
        prompt = generate_llm_prompt(audit_results)
        self.assertIn("Inline Imports", prompt)
        self.assertIn("from db import connect", prompt)

    # ── CLI JSON Output ──────────────────────────────────────────────────────

    def test_cli_json_output(self):
        """checklist audit --format json should produce valid JSON."""
        # Run from project root where checklist module is importable
        project_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "checklist", "audit", "--format", "json"],
            capture_output=True, text=True, cwd=str(project_root)
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("audit", data)


if __name__ == "__main__":
    unittest.main()
