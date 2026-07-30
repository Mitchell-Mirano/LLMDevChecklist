import unittest
import tempfile
import shutil
from pathlib import Path
from devcheck import load_config, init_config_file
from devcheck.config import detect_target_dirs


class TestDevcheckConfig(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
