import unittest
import tempfile
import shutil
from pathlib import Path
from checklist import (
    load_config,
    init_config_file,
    GitIgnoreFilter,
    clean_py_imports,
    clean_vue_imports,
    check_code_language,
    check_hardcoded,
    generate_llm_prompt,
)


class TestChecklistLibrary(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_config(self):
        config_path = init_config_file(self.test_dir)
        self.assertTrue(config_path.exists())
        config = load_config(self.test_dir)
        self.assertIn("checklist", config)
        self.assertTrue(config["checklist"]["use_gitignore"])

    def test_clean_py_imports(self):
        sample_py = self.test_dir / "sample.py"
        sample_py.write_text("import sys\nimport os\nimport sys\nprint('hello')\n", encoding="utf-8")
        
        res = clean_py_imports(target_dirs=[str(sample_py)], fix=True, root_dir=self.test_dir)
        self.assertEqual(res["modified_count"], 1)
        
        cleaned_content = sample_py.read_text(encoding="utf-8")
        self.assertIn("import sys", cleaned_content)
        self.assertIn("import os", cleaned_content)

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
            "docs": {"total_issues": 0, "modules": {}}
        }
        prompt = generate_llm_prompt(audit_results)
        self.assertIn("# 🤖 Checklist Action Items for LLM / AI Assistant", prompt)


if __name__ == "__main__":
    unittest.main()
