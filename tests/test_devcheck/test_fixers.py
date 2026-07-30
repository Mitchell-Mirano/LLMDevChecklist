import unittest
import tempfile
import shutil
from pathlib import Path
from checklist import clean_py_imports, detect_inline_imports


class TestDevcheckFixers(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clean_py_imports(self):
        sample_py = self.test_dir / "sample.py"
        sample_py.write_text("import sys\nimport os\nimport sys\nprint('hello')\n", encoding="utf-8")

        res = clean_py_imports(target_dirs=[str(sample_py)], fix=True, root_dir=self.test_dir)
        self.assertEqual(res["modified_count"], 1)

        cleaned_content = sample_py.read_text(encoding="utf-8")
        self.assertIn("import sys", cleaned_content)
        self.assertIn("import os", cleaned_content)

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


if __name__ == "__main__":
    unittest.main()
