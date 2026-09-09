"""Deterministic router accuracy evaluation."""

import json
from pathlib import Path

from router import route_question

CASES_PATH = Path("eval/router_cases.json")


def main():
    cases = json.loads(CASES_PATH.read_text())
    correct = 0

    print("LifeLens router evaluation")
    print("=" * 60)

    for case in cases:
        decision = route_question(case["question"])
        expected = set(case["expected_sources"])
        predicted = set(decision.sources)
        passed = expected == predicted
        correct += int(passed)

        print(
            f"{'PASS' if passed else 'FAIL'} | "
            f"expected={sorted(expected)} predicted={sorted(predicted)} | "
            f"{case['question']}"
        )

    accuracy = correct / len(cases) if cases else 0
    print(f"\nRouting accuracy: {accuracy:.1%} ({correct}/{len(cases)})")


if __name__ == "__main__":
    main()
