"""LifeLens multi-source orchestrator with structured observability."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from llm_extractor import ask_llm
from observability import log_event, new_trace_id, observed_step, user_hash
from rag.retrieve import search_documents_with_details
from router import route_question
from sql_agent import ask_business
from supabase_client import get_all_events

load_dotenv()

MODEL_NAME = os.getenv("ORCHESTRATOR_MODEL", "gpt-4.1-mini")


def _llm() -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return ChatOpenAI(model=MODEL_NAME, temperature=0)


def _timeline_answer(account_email: str, question: str) -> str:
    events = get_all_events(account_email)
    if not events:
        return "No matching Gmail-derived timeline events are available."
    return ask_llm(events, question)


def _document_answer(account_email: str, question: str) -> dict[str, Any]:
    return search_documents_with_details(
        question=question,
        user_id=account_email,
    )


def _business_answer(account_email: str, question: str) -> dict[str, Any]:
    return ask_business(email=account_email, question=question)


def _synthesize(question: str, source_answers: dict[str, str]) -> str:
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
    trace_id: str | None = None,
) -> dict[str, Any]:
    email = (account_email or "").strip().lower()
    question = (question or "").strip()

    if not email:
        raise ValueError("An active LifeLens account is required.")
    if not question:
        raise ValueError("Question cannot be empty.")

    trace_id = trace_id or new_trace_id()
    hashed_user = user_hash(email)

    log_event(
        "request.received",
        trace_id=trace_id,
        user=hashed_user,
        question_length=len(question),
    )

    with observed_step("router", trace_id=trace_id, user=hashed_user) as obs:
        decision = route_question(question)
        obs["sources"] = decision.sources
        obs["reason"] = decision.reason

    source_answers: dict[str, str] = {}
    details: dict[str, Any] = {}

    for source in decision.sources:
        try:
            with observed_step(
                f"source.{source}",
                trace_id=trace_id,
                user=hashed_user,
            ) as obs:
                if source == "timeline":
                    answer = _timeline_answer(email, question)
                    source_answers["timeline"] = answer

                elif source == "documents":
                    document_result = _document_answer(email, question)
                    source_answers["documents"] = document_result["answer"]
                    details["documents"] = {
                        "retrieved_context_count": len(document_result["contexts"]),
                        "retrieved_metadata": document_result["metadata"],
                    }
                    obs["retrieved_context_count"] = len(
                        document_result["contexts"]
                    )

                elif source == "business":
                    business_result = _business_answer(email, question)
                    source_answers["business"] = business_result["answer"]
                    details["business"] = {
                        "sql": business_result.get("sql"),
                        "sql_explanation": business_result.get("sql_explanation"),
                        "row_count": business_result.get("row_count"),
                    }
                    obs["row_count"] = business_result.get("row_count")

        except Exception as exc:
            logging.exception("LifeLens source failed: %s", source)
            source_answers[source] = (
                f"{source} source could not be queried successfully."
            )
            details.setdefault("errors", {})[source] = str(exc)

    if len(source_answers) == 1:
        final_answer = next(iter(source_answers.values()))
    else:
        with observed_step(
            "synthesis",
            trace_id=trace_id,
            source_count=len(source_answers),
        ):
            final_answer = _synthesize(
                question=question,
                source_answers=source_answers,
            )

    log_event(
        "request.completed",
        trace_id=trace_id,
        user=hashed_user,
        sources=decision.sources,
        source_count=len(source_answers),
        error_sources=list(details.get("errors", {}).keys()),
    )

    return {
        "answer": final_answer,
        "sources": decision.sources,
        "route_reason": decision.reason,
        "source_answers": source_answers,
        "details": details,
        "trace_id": trace_id,
    }
