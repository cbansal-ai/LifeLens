"""
Simple router smoke tests.

These call the LLM router, so OPENAI_API_KEY must be configured.

Run:
    pytest -q test_router.py
"""

import pytest

from router import route_question


@pytest.mark.parametrize(
    "question, expected_source",
    [
        ("When is my dentist appointment?", "timeline"),
        ("What were my sales last month?", "business"),
        (
            "What does my uploaded insurance policy say about my deductible?",
            "documents",
        ),
    ],
)
def test_single_source_routes(question, expected_source):
    decision = route_question(question)
    assert expected_source in decision.sources


def test_hybrid_route():
    decision = route_question(
        "I'm going to New York next week. Which of my top customers are there?"
    )
    assert "timeline" in decision.sources
    assert "business" in decision.sources
