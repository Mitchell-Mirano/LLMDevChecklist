import unittest
import json
import subprocess
import sys
from pathlib import Path


class TestDevcheckCLI(unittest.TestCase):

    def test_cli_json_output(self):
        """devcheck audit --format json should produce valid JSON."""
        project_root = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "checklist", "audit", "--format", "json"],
            capture_output=True, text=True, cwd=str(project_root)
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("audit", data)


if __name__ == "__main__":
    unittest.main()
