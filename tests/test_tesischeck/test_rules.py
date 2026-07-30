import unittest
from unittest.mock import MagicMock

from thesis_checker.core import RuleResult, ValidationContext
from thesis_checker.rules.structure import FileExistenceRule
from thesis_checker.rules.advanced import NoHardcodedTablesRule, OrphanLabelRule, EquationEnvironmentRule


class TestTesischeckRules(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=ValidationContext)
        self.context.target_dir = "/dummy/dir"

    def test_file_existence_rule(self):
        import os
        original_exists = os.path.exists

        def mock_exists(path):
            if path.endswith("exists.tex"):
                return True
            return False

        os.path.exists = mock_exists

        rule = FileExistenceRule(["exists.tex", "missing.tex"])
        result = rule.validate(self.context)

        os.path.exists = original_exists

        self.assertEqual(result.status, RuleResult.FAIL)
        self.assertTrue(any("missing.tex" in msg for msg in result.messages))

    def test_no_hardcoded_tables_rule_pass(self):
        self.context.get_file_content.return_value = "This is a normal text with \\input{tables/tab1.tex}."

        rule = NoHardcodedTablesRule("test.tex")
        result = rule.validate(self.context)

        self.assertEqual(result.status, RuleResult.PASS)

    def test_no_hardcoded_tables_rule_fail(self):
        self.context.get_file_content.return_value = "Here is a table:\n\\begin{tabular}{cc}\n1 & 2\\\\\n\\end{tabular}"

        rule = NoHardcodedTablesRule("test.tex")
        result = rule.validate(self.context)

        self.assertEqual(result.status, RuleResult.FAIL)
        self.assertTrue(any("Hardcoded" in msg for msg in result.messages))

    def test_orphan_label_rule_pass(self):
        self.context.get_file_content.return_value = "Define \\label{eq:1}. Reference \\ref{eq:1}."

        rule = OrphanLabelRule(["test.tex"])
        result = rule.validate(self.context)

        self.assertEqual(result.status, RuleResult.PASS)

    def test_orphan_label_rule_fail(self):
        self.context.get_file_content.return_value = "Define \\label{eq:1}. No reference here."

        rule = OrphanLabelRule(["test.tex"])
        result = rule.validate(self.context)

        self.assertEqual(result.status, RuleResult.FAIL)
        self.assertTrue(any("eq:1" in msg for msg in result.messages))

    def test_equation_environment_rule_fail(self):
        self.context.get_file_content.return_value = "Bad equation $$ E = mc^2 $$."

        rule = EquationEnvironmentRule(["test.tex"])
        result = rule.validate(self.context)

        self.assertEqual(result.status, RuleResult.FAIL)


if __name__ == "__main__":
    unittest.main()
