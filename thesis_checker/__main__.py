import argparse
import json
import sys
import os

from .runner import ValidatorRunner
from .unmsm_rules import get_unmsm_rules


def main():
    parser = argparse.ArgumentParser(
        prog="tesischeck",
        description="📝 LaTeX Manuscript Validator — Validates thesis structure against UNMSM guidelines"
    )
    parser.add_argument("--target", required=True, help="Path to the LaTeX project directory")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format: text (default) or json")
    args = parser.parse_args()

    target_dir = args.target
    if not os.path.isdir(target_dir):
        print(f"Error: Target directory '{target_dir}' does not exist.")
        sys.exit(1)

    runner = ValidatorRunner(target_dir)

    for rule in get_unmsm_rules():
        runner.add_rule(rule)

    results = runner.run(output_format=args.format)

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))

    if not results["all_passed"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
