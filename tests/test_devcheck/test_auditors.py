import unittest
import tempfile
import shutil
from pathlib import Path
from devcheck import check_code_language, check_hardcoded, generate_llm_prompt


class TestDevcheckAuditors(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

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


if __name__ == "__main__":
    unittest.main()
