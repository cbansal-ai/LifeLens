"""
LifeLens Text-to-SQL Agent
==========================

Step 4 of the LifeLens business assistant.

Flow:
    user question
        -> backend resolves email -> business_id / role
        -> LLM generates PostgreSQL SELECT
        -> SQL guardrails validate it
        -> PostgreSQL executes it read-only
        -> LLM explains the result

Important security boundary:
The LLM NEVER chooses the user's business_id or role.
Those values come from business_db.py.
"""

import json
import os
import re
from datetime import date
from decimal import Decimal
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from business_db import (
    execute_read_only_query,
    get_business_context,
)
from sql_guardrails import validate_agent_sql


load_dotenv()

MODEL_NAME = os.getenv("SQL_AGENT_MODEL", "gpt-4.1-mini")
MAX_RESULT_ROWS = 100


# ---------------------------------------------------------------------------
# Schema exposed to the LLM
# ---------------------------------------------------------------------------

BUSINESS_SCHEMA = """
PostgreSQL schema available to you:

customers
- customer_id INTEGER PRIMARY KEY
- business_id INTEGER
- first_name VARCHAR
- last_name VARCHAR
- email VARCHAR
- city VARCHAR
- state VARCHAR
- created_at DATE

products
- product_id INTEGER PRIMARY KEY
- business_id INTEGER
- product_name VARCHAR
- category VARCHAR
- unit_price NUMERIC

orders
- order_id INTEGER PRIMARY KEY
- business_id INTEGER
- customer_id INTEGER
- order_date DATE
- status VARCHAR
- total_amount NUMERIC

order_items
- order_item_id INTEGER PRIMARY KEY
- order_id INTEGER
- product_id INTEGER
- quantity INTEGER
- unit_price NUMERIC

Relationships:
- orders.customer_id = customers.customer_id
- order_items.order_id = orders.order_id
- order_items.product_id = products.product_id

Business rules:
- Revenue / sales should normally use orders.total_amount.
- Unless the user explicitly asks otherwise, use COMPLETED orders for realized sales/revenue.
- order_items has no business_id, so when using order_items you MUST join orders and
  scope through orders.business_id.
"""


ALLOWED_TABLES = {
    "customers",
    "products",
    "orders",
    "order_items",
}

BLOCKED_TABLES = {
    "users",
    "businesses",
    "events",
}


# ---------------------------------------------------------------------------
# Structured LLM output
# ---------------------------------------------------------------------------

class SQLPlan(BaseModel):
    sql: str = Field(
        description=(
            "One PostgreSQL SELECT/WITH query. It must use "
            "%(business_id)s for tenant scoping."
        )
    )
    explanation: str = Field(
        description="A short explanation of what the SQL calculates."
    )


def _llm() -> ChatOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=0,
    )


# ---------------------------------------------------------------------------
# SQL generation
# ---------------------------------------------------------------------------

def generate_sql(
    question: str,
    business_id: int,
) -> SQLPlan:
    """
    Ask the LLM to generate SQL.

    business_id is shown for context, but the LLM must reference it through
    the %(business_id)s parameter. It must not hard-code the numeric value.
    """
    today = date.today().isoformat()

    prompt = f"""
You are a PostgreSQL Text-to-SQL component for a multi-tenant business assistant.

Today's date: {today}

{BUSINESS_SCHEMA}

The authenticated backend has already resolved:
business_id = {business_id}

User question:
{question}

Generate exactly ONE read-only PostgreSQL query.

STRICT RULES:
1. Only SELECT or WITH queries.
2. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, CALL, or DO.
3. Only use these business-data tables:
   customers, products, orders, order_items.
4. Never query users, businesses, events, pg_catalog, information_schema,
   or any system table.
5. Every query MUST be tenant-scoped with:
       %(business_id)s
6. Never hard-code the numeric business_id.
7. If customers appears, scope customers.business_id = %(business_id)s.
8. If products appears, scope products.business_id = %(business_id)s.
9. If orders appears, scope orders.business_id = %(business_id)s.
10. If order_items appears, join it to orders and scope orders.business_id
    = %(business_id)s.
11. Do not use SQL comments.
12. Do not generate more than one SQL statement.
13. For detail/list queries, return at most {MAX_RESULT_ROWS} rows.
14. For relative dates such as "last month", calculate the date range from
    today's date shown above.
15. Use PostgreSQL syntax.
"""

    structured_llm = _llm().with_structured_output(SQLPlan)
    return structured_llm.invoke(prompt)


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------

def execute_generated_sql(
    sql: str,
    business_id: int,
) -> list[dict[str, Any]]:
    validate_agent_sql(sql)

    # business_id comes from the trusted backend context, not the LLM.
    return execute_read_only_query(
        sql,
        {"business_id": business_id},
    )


# ---------------------------------------------------------------------------
# Result formatting / answer generation
# ---------------------------------------------------------------------------

def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date,)):
        return value.isoformat()
    return value


def _serialize_rows(rows: list[dict[str, Any]]) -> str:
    safe_rows = [
        {key: _json_safe(value) for key, value in row.items()}
        for row in rows[:MAX_RESULT_ROWS]
    ]
    return json.dumps(safe_rows, indent=2, default=str)


def generate_answer(
    question: str,
    sql: str,
    rows: list[dict[str, Any]],
) -> str:
    """
    Convert SQL results into a concise user-facing answer.

    The model is explicitly restricted to the returned rows.
    """
    if not rows:
        return "I didn't find any matching business data for that question."

    result_json = _serialize_rows(rows)

    prompt = f"""
You are answering a business analytics question.

User question:
{question}

SQL executed:
{sql}

Database result:
{result_json}

Answer the question using ONLY the database result above.
Do not invent values.
Be concise.
For money, use normal currency formatting when appropriate.
If the result contains multiple rows, summarize the important result clearly.
"""

    response = _llm().invoke(prompt)
    return response.content


# ---------------------------------------------------------------------------
# End-to-end agent
# ---------------------------------------------------------------------------

def ask_business(
    email: str,
    question: str,
) -> dict[str, Any]:
    """
    End-to-end Text-to-SQL pipeline.

    Returns SQL and rows as well as the final answer so the pipeline is
    observable and easy to debug/evaluate during development.
    """
    context = get_business_context(email)
    business_id = context["business_id"]

    plan = generate_sql(
        question=question,
        business_id=business_id,
    )

    rows = execute_generated_sql(
        sql=plan.sql,
        business_id=business_id,
    )

    answer = generate_answer(
        question=question,
        sql=plan.sql,
        rows=rows,
    )

    return {
        "answer": answer,
        "sql": plan.sql,
        "sql_explanation": plan.explanation,
        "row_count": len(rows),
        "rows": rows,
        "business_context": {
            "business_id": business_id,
            "role": context["role"],
        },
    }


if __name__ == "__main__":
    test_email = "demolifelens@gmail.com"
    test_question = "What were my total sales last month?"

    result = ask_business(
        email=test_email,
        question=test_question,
    )

    print("\nQUESTION:")
    print(test_question)

    print("\nGENERATED SQL:")
    print(result["sql"])

    print("\nROWS:")
    print(result["rows"])

    print("\nANSWER:")
    print(result["answer"])
