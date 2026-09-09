"""
LifeLens multi-source orchestrator.

Routes a question to:
- Gmail-derived timeline events
- PDF RAG
- Business Text-to-SQL

For hybrid questions, it calls multiple specialized paths and synthesizes
one final answer from their grounded outputs.
"""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from llm_extractor import ask_llm
from rag.retrieve import search_documents
from router import route_question
from sql_agent import ask_business
from supabase_client import get_all_events

load_dotenv()

MODEL_NAME = os.getenv("ORCHESTRATOR_MODEL", "gpt-4.1-mini")


def _llm() -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=0,
    )


def _timeline_answer(account_email: str, question: str) -> str:
    """
    Search structured Gmail-derived events already stored in PostgreSQL.
    """
    events = get_all_events(account_email)
    if not events:
        return "No matching Gmail-derived timeline events are available."

    return ask_llm(events, question)


def _document_answer(account_email: str, question: str) -> str:
    """
    Search only PDFs belonging to the active LifeLens user.
    """
    return search_documents.invoke(
        {
            "question": question,
            "user_id": account_email,
        }
    )


def _business_answer(account_email: str, question: str) -> dict[str, Any]:
    """
    Run the guarded Text-to-SQL business pipeline.

    account_email is used by the backend to resolve the trusted business_id.
    """
    return ask_business(
        email=account_email,
        question=question,
    )


def _synthesize(
    question: str,
    source_answers: dict[str, str],
) -> str:
    """
    Combine multiple grounded source answers.

    The synthesis model gets only source outputs, not direct DB/vector access.
    """
    source_text = "\n\n".join(
        f"{source.upper()} RESULT:\n{answer}"
        for source, answer in source_answers.items()
    )

    prompt = f"""
You are the final response layer for LifeLens.

Answer the user's question using ONLY the source results below.
Do not invent missing facts.
If the sources do not contain enough information, say so clearly.
When combining personal and business information, explain the connection
concisely.

User question:
{question}

Source results:
{source_text}
"""

    response = _llm().invoke(prompt)
    return response.content


def ask_lifelens(
    account_email: str,
    question: str,
) -> dict[str, Any]:
    """
    Main LifeLens orchestration entry point.

    Identity boundary:
    - The backend supplies account_email.
    - The router never selects account_email or business_id.
    - The business agent resolves business_id deterministically from email.
    """
    email = (account_email or "").strip().lower()
    question = (question or "").strip()

    if not email:
        raise ValueError("An active LifeLens account is required.")
    if not question:
        raise ValueError("Question cannot be empty.")

    decision = route_question(question)
    logging.info(
        "LifeLens route selected: %s | reason=%s",
        decision.sources,
        decision.reason,
    )

    source_answers: dict[str, str] = {}
    details: dict[str, Any] = {}

    for source in decision.sources:
        try:
            if source == "timeline":
                answer = _timeline_answer(email, question)
                source_answers["timeline"] = answer

            elif source == "documents":
                answer = _document_answer(email, question)
                source_answers["documents"] = answer

            elif source == "business":
                business_result = _business_answer(email, question)
                source_answers["business"] = business_result["answer"]

                # Keep SQL visible for development/evaluation/observability.
                details["business"] = {
                    "sql": business_result.get("sql"),
                    "sql_explanation": business_result.get("sql_explanation"),
                    "row_count": business_result.get("row_count"),
                }

        except Exception as exc:
            logging.exception("LifeLens source failed: %s", source)
            source_answers[source] = (
                f"{source} source could not be queried successfully."
            )
            details.setdefault("errors", {})[source] = str(exc)

    if len(source_answers) == 1:
        final_answer = next(iter(source_answers.values()))
    else:
        final_answer = _synthesize(
            question=question,
            source_answers=source_answers,
        )

    return {
        "answer": final_answer,
        "sources": decision.sources,
        "route_reason": decision.reason,
        "source_answers": source_answers,
        "details": details,
    }


if __name__ == "__main__":
    test_email = "demolifelens@gmail.com"

    examples = [
        "When is my next trip?",
        "What were my total sales last month?",
        "What does my uploaded insurance document say about the deductible?",
        "I'm going to New York next week. Which of my top customers are there?",
    ]

    for q in examples:
        print("\n" + "=" * 80)
        print("QUESTION:", q)
        result = ask_lifelens(test_email, q)
        print("SOURCES:", result["sources"])
        print("ANSWER:", result["answer"])
