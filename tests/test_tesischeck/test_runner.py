import unittest
import tempfile
import shutil
from pathlib import Path
from tesischeck import ValidatorRunner, BaseRule, RuleResult, ValidationContext, get_unmsm_rules


class DummyPassRule(BaseRule):
    @property
    def name(self) -> str:
        return "DummyPassRule"

    @property
    def description(self) -> str:
        return "Always passes."

    def validate(self, context: ValidationContext) -> RuleResult:
        return RuleResult(RuleResult.PASS)


class TestTesischeckRunner(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_runner_text_format(self):
        runner = ValidatorRunner(str(self.test_dir))
        runner.add_rule(DummyPassRule())
        res = runner.run(output_format="text")
        self.assertTrue(res["all_passed"])
        self.assertEqual(res["passed"], 1)

    def test_runner_json_format(self):
        runner = ValidatorRunner(str(self.test_dir))
        runner.add_rule(DummyPassRule())
        res = runner.run(output_format="json")
        self.assertIn("results", res)
        self.assertEqual(res["results"][0]["rule"], "DummyPassRule")

    def test_unmsm_rules_count(self):
        rules = get_unmsm_rules()
        self.assertGreater(len(rules), 0)


if __name__ == "__main__":
    unittest.main()
