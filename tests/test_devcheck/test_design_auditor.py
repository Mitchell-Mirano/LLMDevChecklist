import shutil
import tempfile
import unittest
from pathlib import Path
from devcheck import check_design, generate_llm_prompt
from devcheck.design.contrast import contrast_ratio, parse_color


class TestDesignAuditor(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_colors_and_alpha_compositing(self):
        self.assertEqual(parse_color("#fff"), (255, 255, 255, 1.0))
        self.assertEqual(parse_color("rgb(255 0 128 / 0.5)"), (255, 0, 128, 0.5))
        self.assertIsNotNone(parse_color("hsl(120, 100%, 50%)"))

        # Low-opacity white on dark background has much lower contrast than opaque white
        cr_opaque = contrast_ratio("#ffffff", "#121212")
        cr_alpha = contrast_ratio("rgba(255, 255, 255, 0.2)", "#121212")
        self.assertIsNotNone(cr_opaque)
        self.assertIsNotNone(cr_alpha)
        self.assertGreater(cr_opaque, 15.0)
        self.assertLess(cr_alpha, 3.0)

    def test_tokens_file_excluded_and_components_audited(self):
        assets = self.test_dir / "src" / "assets"
        assets.mkdir(parents=True)
        main_css = assets / "main.css"
        main_css.write_text(
            ":root {\n"
            "  --bg-dark: #121212;\n"
            "  --text-primary: #ffffff;\n"
            "  --text-muted: #444444;\n"
            "}\n",
            encoding="utf-8",
        )

        comp = self.test_dir / "src" / "Card.vue"
        comp.write_text(
            "<template>\n"
            '  <div class="card" style="padding: 8px">\n'
            '    <span>🔥 Alert</span>\n'
            '    <img src="x.png" />\n'
            '    <button><svg></svg></button>\n'
            "  </div>\n"
            "</template>\n"
            "<style scoped>\n"
            ".card {\n"
            "  color: #ff0000;\n"
            "  background: var(--bg-dark);\n"
            "  border-color: var(--non-existent);\n"
            "  z-index: 9999;\n"
            "}\n"
            "</style>\n",
            encoding="utf-8",
        )

        res = check_design(
            target_dirs=["src"],
            root_dir=self.test_dir,
            design_cfg={"tokens_files": ["src/assets/main.css"]},
        )

        # main.css should not be flagged for defining :root hex colors
        self.assertNotIn("src/assets/main.css", res["issues_by_file"])
        self.assertIn("src/Card.vue", res["issues_by_file"])

        rules_found = {i["rule"] for i in res["issues_by_file"]["src/Card.vue"]}
        self.assertIn("hardcoded-color", rules_found)
        self.assertIn("undefined-token", rules_found)
        self.assertIn("unicode-icon", rules_found)
        self.assertIn("inline-style", rules_found)
        self.assertIn("magic-z-index", rules_found)
        self.assertIn("svg-missing-viewbox", rules_found)
        self.assertIn("a11y-img-alt", rules_found)
        self.assertIn("a11y-icon-button", rules_found)

        # Contrast audit should detect --text-muted (#444444) on --bg-dark (#121212) failing AA
        self.assertGreater(res["contrast"]["failures_count"], 0)

    def test_suppressions_and_comments_ignored(self):
        src = self.test_dir / "src"
        src.mkdir(parents=True)
        (src / "main.css").write_text(":root { --primary: #1a73e8; }\n", encoding="utf-8")
        comp = src / "Clean.vue"
        comp.write_text(
            "<template>\n"
            "  <!-- 🔥 ignored in HTML comment -->\n"
            '  <div class="ok">ok</div>\n'
            "</template>\n"
            "<style scoped>\n"
            ".ok {\n"
            "  /* #123456 ignored in CSS comment */\n"
            "  /* devcheck-ignore-next-line(hardcoded-color) */\n"
            "  color: #abcdef;\n"
            "  background: var(--primary);\n"
            "}\n"
            "</style>\n",
            encoding="utf-8",
        )

        res = check_design(target_dirs=["src"], root_dir=self.test_dir)
        self.assertEqual(res["issues_by_file"], {})
        self.assertEqual(res["metrics"]["tokenization_rate"], 100.0)

    def test_llm_prompt_includes_design_section(self):
        audit_results = {
            "language": {"total_issues": 0, "issues_by_file": {}},
            "hardcoded": {"total_issues": 0, "issues_by_file": {}},
            "docs": {"total_issues": 0, "modules": {}},
            "design": {
                "total_issues": 1,
                "issues_by_file": {
                    "src/App.vue": [
                        {
                            "line_no": 12,
                            "rule": "hardcoded-color",
                            "matched": "#ff0000",
                            "message": "Hardcoded hex color `#ff0000`.",
                        }
                    ]
                },
                "metrics": {"tokens_files": ["src/main.css"]},
                "contrast": {"checked_pairs": [], "failures_count": 0},
            },
        }
        prompt = generate_llm_prompt(audit_results)
        self.assertIn("Design System, Contrast & SVG Icons", prompt)
        self.assertIn("hardcoded-color", prompt)
        self.assertIn("src/App.vue:L12", prompt)

    def test_duplicate_tokens_important_and_style_rules_in_token_file(self):
        src = self.test_dir / "src"
        src.mkdir(parents=True)
        style_css = src / "style.css"
        style_css.write_text(
            ":root {\n"
            "  --accent-orange: #f97316;\n"
            "  --attr-str: #f97316;\n"
            "  --bg-dark: #080b12;\n"
            "}\n"
            ".badge {\n"
            "  color: #ffffff !important;\n"
            "}\n",
            encoding="utf-8",
        )

        res = check_design(target_dirs=["src"], root_dir=self.test_dir)
        self.assertIn("src/style.css", res["issues_by_file"])
        rules = {i["rule"] for i in res["issues_by_file"]["src/style.css"]}
        self.assertIn("duplicate-color-token", rules)
        self.assertIn("important-override", rules)
        self.assertIn("hardcoded-color", rules)
        self.assertEqual(res["metrics"]["duplicate_tokens"], 1)


if __name__ == "__main__":
    unittest.main()
