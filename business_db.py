"""
LifeLens business database service.

This version intentionally uses direct PostgreSQL SQL rather than an ORM.
That keeps the business analytics layer explicit and makes SQL logic easy
to inspect, test, and discuss in interviews.

Responsibilities:
- Connect to PostgreSQL.
- Resolve email -> user_id, business_id, role.
- Run parameterized read-only SQL.
- Scope business queries using business_id from the backend.
"""

import os
import re
from typing import Any, Sequence

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


class BusinessDBError(Exception):
    """Base exception for business database errors."""


class BusinessUserNotFoundError(BusinessDBError):
    """Raised when no business user exists for the supplied email."""


class UnsafeQueryError(BusinessDBError):
    """Raised when a non-read-only SQL statement is attempted."""


def get_connection():
    """
    Create a PostgreSQL connection.

    Add your Postgres connection string to .env:

        DATABASE_URL=postgresql://...
    """
    if not DATABASE_URL:
        raise BusinessDBError(
            "DATABASE_URL is not configured in the environment."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def get_business_user(email: str) -> dict[str, Any]:
    """
    Resolve the user's business identity from PostgreSQL.

    The backend performs this lookup.
    The LLM must never decide or invent business_id or role.
    """
    normalized_email = email.strip().lower()

    sql = """
        SELECT
            user_id,
            email,
            business_id,
            role
        FROM users
        WHERE LOWER(email) = %s
        LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (normalized_email,))
            user = cur.fetchone()

    if not user:
        raise BusinessUserNotFoundError(
            f"No business user found for email: {normalized_email}"
        )

    return dict(user)


def get_business_context(email: str) -> dict[str, Any]:
    """
    Return trusted business context for downstream agent/tool calls.
    """
    user = get_business_user(email)

    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "business_id": user["business_id"],
        "role": user["role"],
    }


def validate_read_only_sql(sql: str) -> None:
    """
    MVP SQL safety validation.

    Allows SELECT and WITH queries.
    Blocks write/DDL/admin operations.

    A database-level read-only role should still be used in production.
    """
    if not sql or not sql.strip():
        raise UnsafeQueryError("SQL query is empty.")

    cleaned = sql.strip()

    # Remove leading comments before checking the first statement.
    cleaned = re.sub(
        r"^(?:\s*--[^\n]*\n|\s*/\*.*?\*/\s*)+",
        "",
        cleaned,
        flags=re.S,
    )

    first_keyword = cleaned.split(None, 1)[0].upper()

    if first_keyword not in {"SELECT", "WITH"}:
        raise UnsafeQueryError(
            "Only SELECT and WITH queries are allowed."
        )

    blocked_keywords = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "COPY",
        "CALL",
        "DO",
    }

    upper_sql = cleaned.upper()

    for keyword in blocked_keywords:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise UnsafeQueryError(
                f"Blocked SQL keyword detected: {keyword}"
            )


def execute_read_only_query(
    sql: str,
    params: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Execute parameterized read-only SQL.

    This function will later be used by the Text-to-SQL layer after
    generated SQL has passed validation and tenant-scope checks.
    """
    validate_read_only_sql(sql)

    with get_connection() as conn:
        # Database-level protection for the current transaction.
        conn.execute("SET TRANSACTION READ ONLY")

        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()

    return [dict(row) for row in rows]


def get_customers(
    email: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Fetch customers for the authenticated/demo user's business.
    """
    context = get_business_context(email)

    sql = """
        SELECT
            customer_id,
            business_id,
            first_name,
            last_name,
            email,
            city,
            state,
            created_at
        FROM customers
        WHERE business_id = %s
        ORDER BY customer_id
        LIMIT %s;
    """

    return execute_read_only_query(
        sql,
        (context["business_id"], limit),
    )


def get_products(
    email: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Fetch products for the user's business.
    """
    context = get_business_context(email)

    sql = """
        SELECT *
        FROM products
        WHERE business_id = %s
        ORDER BY product_id
        LIMIT %s;
    """

    return execute_read_only_query(
        sql,
        (context["business_id"], limit),
    )


def get_orders(
    email: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Fetch recent orders for the user's business.
    """
    context = get_business_context(email)

    sql = """
        SELECT *
        FROM orders
        WHERE business_id = %s
        ORDER BY order_date DESC
        LIMIT %s;
    """

    return execute_read_only_query(
        sql,
        (context["business_id"], limit),
    )


def get_business_summary(email: str) -> dict[str, Any]:
    """
    Simple SQL-based smoke test for Step 3.
    """
    context = get_business_context(email)
    business_id = context["business_id"]

    sql = """
        SELECT
            (SELECT COUNT(*)
             FROM customers
             WHERE business_id = %s) AS customer_count,

            (SELECT COUNT(*)
             FROM products
             WHERE business_id = %s) AS product_count,

            (SELECT COUNT(*)
             FROM orders
             WHERE business_id = %s) AS order_count;
    """

    rows = execute_read_only_query(
        sql,
        (business_id, business_id, business_id),
    )

    return {
        "user": context,
        "summary": rows[0] if rows else {},
    }


if __name__ == "__main__":
    result = get_business_summary("demolifelens@gmail.com")
    print(result)
