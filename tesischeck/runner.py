from typing import List, Dict, Any

from .core import BaseRule, ValidationContext, RuleResult


class ValidatorRunner:
    """Orchestrates the execution of multiple validation rules."""

    def __init__(self, target_dir: str):
        self.context = ValidationContext(target_dir)
        self.rules: List[BaseRule] = []

    def add_rule(self, rule: BaseRule):
        self.rules.append(rule)

    def run(self, output_format: str = "text") -> Dict[str, Any]:
        """Runs all rules and returns structured results.

        Args:
            output_format: 'text' prints to terminal, 'json' returns dict silently.

        Returns:
            Dict with 'all_passed', 'total_rules', 'passed', 'failed', 'warnings', 'results'.
        """
        if output_format == "text":
            print(f"=== Starting ThesisChecker ===")
            print(f"Target Directory: {self.context.target_dir}")
            print(f"Rules Loaded: {len(self.rules)}\n")

        all_passed = True
        results_list = []

        for rule in self.rules:
            result = rule.validate(self.context)

            entry = {
                "rule": rule.name,
                "description": rule.description,
                "status": result.status,
                "messages": result.messages,
            }
            results_list.append(entry)

            if result.status == RuleResult.FAIL:
                all_passed = False

            if output_format == "text":
                if result.status == RuleResult.PASS:
                    print(f"[PASS] {rule.name}")
                elif result.status == RuleResult.WARNING:
                    print(f"[WARNING] {rule.name}")
                else:
                    print(f"[FAIL] {rule.name}")

                for msg in result.messages:
                    prefix = "  -> " if result.status != RuleResult.FAIL else "  [X] "
                    print(f"{prefix}{msg}")

        passed_count = sum(1 for r in results_list if r["status"] == RuleResult.PASS)
        failed_count = sum(1 for r in results_list if r["status"] == RuleResult.FAIL)
        warning_count = sum(1 for r in results_list if r["status"] == RuleResult.WARNING)

        if output_format == "text":
            print(f"\n=== Validation Complete ===")
            print(f"Results: {passed_count} passed, {failed_count} failed, {warning_count} warnings")
            if all_passed:
                print("Status: SUCCESS")
            else:
                print("Status: FAILED")

        return {
            "all_passed": all_passed,
            "total_rules": len(self.rules),
            "passed": passed_count,
            "failed": failed_count,
            "warnings": warning_count,
            "results": results_list,
        }
