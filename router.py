"""
LifeLens source router.

The router chooses one or more data sources for a question:
- timeline: Gmail-derived structured events in PostgreSQL
- documents: uploaded PDFs in ChromaDB/RAG
- business: structured business analytics in PostgreSQL

Security note:
The router does NOT receive or choose account_email/business_id.
Identity and tenant scope stay in the backend.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

load_dotenv()

MODEL_NAME = os.getenv("ROUTER_MODEL", "gpt-4.1-mini")

SourceName = Literal["timeline", "documents", "business"]


class RouteDecision(BaseModel):
    sources: list[SourceName] = Field(
        description="One or more data sources needed to answer the question."
    )
    reason: str = Field(
        description="Short explanation for why these sources are needed."
    )

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, sources):
        # Preserve order while removing duplicates.
        deduped = list(dict.fromkeys(sources))
        if not deduped:
            raise ValueError("At least one source must be selected.")
        return deduped


def _router_llm() -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=0,
    )


def route_question(question: str) -> RouteDecision:
    """
    Decide which LifeLens source(s) should answer the question.

    The router only decides data-source routing. It never receives tenant IDs.
    """
    prompt = f"""
You are the routing layer for LifeLens.

Available data sources:

1. timeline
   Gmail-derived structured personal events stored in PostgreSQL.
   Use for:
   - travel reservations
   - appointments
   - purchases/orders from personal email
   - deliveries
   - bookings
   - dates and personal timeline history

2. documents
   Uploaded personal PDFs searched with RAG/ChromaDB.
   Use for:
   - insurance policies
   - itineraries or contracts uploaded as PDFs
   - document-specific details
   - questions asking what an uploaded document says

3. business
   Structured small-business PostgreSQL data queried through Text-to-SQL.
   Use for:
   - revenue/sales
   - customers
   - products
   - business orders
   - trends, rankings, aggregates, analytics

Choose ALL sources truly needed.

Examples:
Question: "When is my dentist appointment?"
sources: ["timeline"]

Question: "What does my insurance policy say about the deductible?"
sources: ["documents"]

Question: "What were my sales last month?"
sources: ["business"]

Question: "I'm going to New York next week. Which of my top customers are there?"
sources: ["timeline", "business"]

Question: "What hotel is listed in my uploaded Paris itinerary?"
sources: ["documents"]

Do not choose multiple sources unless the question actually requires combining them.

User question:
{question}
"""

    structured_llm = _router_llm().with_structured_output(RouteDecision)
    return structured_llm.invoke(prompt)
