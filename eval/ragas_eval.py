"""RAGAS evaluation for the LifeLens PDF/RAG path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ragas import EvaluationDataset, evaluate
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from rag.retrieve import search_documents_with_details


def load_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text())
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation file must contain a non-empty JSON list.")

    for index, case in enumerate(cases, start=1):
        if not case.get("question"):
            raise ValueError(f"Case {index} is missing question.")
        if not case.get("reference"):
            raise ValueError(
                f"Case {index} is missing reference. "
                "Use a manually verified ground-truth answer."
            )
        if case["question"].startswith("REPLACE:") or case["reference"].startswith("REPLACE:"):
            raise ValueError(
                "Replace the template questions/references in "
                "eval/ragas_cases.json before running evaluation."
            )
    return cases


def build_dataset(email: str, cases: list[dict]) -> EvaluationDataset:
    samples = []

    for case in cases:
        result = search_documents_with_details(
            question=case["question"],
            user_id=email,
        )
        samples.append(
            SingleTurnSample(
                user_input=case["question"],
                response=result["answer"],
                retrieved_contexts=result["contexts"],
                reference=case["reference"],
            )
        )

    return EvaluationDataset(samples=samples)


def run(email: str, cases_path: Path, output_path: Path):
    cases = load_cases(cases_path)
    dataset = build_dataset(email=email, cases=cases)

    result = evaluate(
        dataset=dataset,
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
    )

    df = result.to_pandas()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print("\nLifeLens RAGAS evaluation")
    print("=" * 60)
    for metric in (
        "context_precision",
        "context_recall",
        "faithfulness",
        "answer_relevancy",
    ):
        if metric in df.columns:
            print(f"{metric:20s}: {df[metric].mean():.3f}")

    print(f"\nDetailed results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("eval/ragas_cases.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results/ragas_results.csv"),
    )
    args = parser.parse_args()

    run(
        email=args.email.strip().lower(),
        cases_path=args.cases,
        output_path=args.output,
    )
