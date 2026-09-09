"""General input guardrails for LifeLens."""

import logging
import re

from constants import SUSPICIOUS_PHRASES
from llm_extractor import classify_question

logger = logging.getLogger("lifelens.guardrails")
MAX_QUESTION_LENGTH = 1000

INJECTION_PATTERNS = (
    r"\bignore (all|any|the|your|previous|prior) instructions?\b",
    r"\bdisregard (all|any|the|your|previous|prior) instructions?\b",
    r"\breveal (the )?(system|developer) prompt\b",
    r"\bshow (me )?(the )?(system|developer) prompt\b",
    r"\bprint (the )?(system|developer) prompt\b",
    r"\bact as (the )?system\b",
    r"\bbypass (the )?(guardrails?|safety|security)\b",
)

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def validate_input(question: str):
    if question is None:
        return False, "Question cannot be empty."

    question = question.strip()
    if not question:
        logger.warning("Empty question")
        return False, "Question cannot be empty."

    if len(question) > MAX_QUESTION_LENGTH:
        logger.warning("Question too long")
        return False, f"Question cannot exceed {MAX_QUESTION_LENGTH} characters."

    if CONTROL_CHAR_RE.search(question):
        logger.warning("Control characters detected")
        return False, "Question contains unsupported control characters."

    lowered = question.lower()

    if any(phrase.lower() in lowered for phrase in SUSPICIOUS_PHRASES):
        logger.warning("Prompt injection phrase detected")
        return False, "Prompt injection attempt detected."

    if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in INJECTION_PATTERNS):
        logger.warning("Prompt injection pattern detected")
        return False, "Prompt injection attempt detected."

    return is_out_of_scope(question)


def is_out_of_scope(question: str):
    prompt = f"""
You are an intent classifier for LifeLens.

Return ONLY one word: YES or NO.

Return YES if the question requires information stored in the user's LifeLens
account, including personal data OR the user's small-business data.

Personal data includes Gmail-derived events, appointments, travel reservations,
purchases, deliveries, timeline/history, uploaded PDFs, insurance policies,
contracts, itineraries, and other personal documents.

Business data includes sales, revenue, customers, products, business orders,
business trends, rankings, aggregates, and business analytics.

Return NO for requests that do not need the user's stored LifeLens data, such as
general knowledge, programming/coding help, weather, news, recipes, general
math, or unrelated questions.

Examples:
"What were my sales last month?" -> YES
"Who are my top five customers?" -> YES
"What does my uploaded insurance policy say?" -> YES
"When is my next trip?" -> YES
"What is the capital of France?" -> NO

Question:
{question}
"""
    try:
        response = classify_question(prompt).strip().upper()
        if response.startswith("YES"):
            return True, ""
        return False, (
            "I can only answer questions that use your personal or business "
            "data stored in LifeLens."
        )
    except Exception:
        logger.exception("Scope classification failed")
        return False, "Unable to validate your request at the moment."
