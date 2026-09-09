"""
LifeLens Step 5 - Text-to-SQL Guardrails

Uses sqlglot to parse generated PostgreSQL instead of relying only on regex.

This is stronger than the Step 4 MVP validator, but production tenant isolation
should still also use a read-only DB role and PostgreSQL Row Level Security.
"""

import re
from typing import Iterable

import sqlglot
from sqlglot import exp

from business_db import UnsafeQueryError, validate_read_only_sql


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


def _normalise_for_parser(sql: str) -> str:
    """
    sqlglot does not understand psycopg's %(business_id)s placeholder.
    Replace it with a harmless numeric literal only for AST parsing.

    The original SQL is what gets executed.
    """
    return sql.replace("%(business_id)s", "0")


def _parse_one_statement(sql: str) -> exp.Expression:
    try:
        statements = sqlglot.parse(_normalise_for_parser(sql), read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise UnsafeQueryError(f"SQL could not be parsed safely: {exc}") from exc

    if len(statements) != 1:
        raise UnsafeQueryError("Exactly one SQL statement is allowed.")

    return statements[0]


def _table_names(tree: exp.Expression) -> set[str]:
    """
    Return physical table names while excluding CTE aliases.
    """
    cte_names = {
        cte.alias_or_name.lower()
        for cte in tree.find_all(exp.CTE)
        if cte.alias_or_name
    }

    names = set()
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name not in cte_names:
            names.add(name)
    return names


def _contains_forbidden_operation(tree: exp.Expression) -> bool:
    forbidden_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Merge,
    )
    return any(tree.find(node_type) is not None for node_type in forbidden_types)


def _has_business_id_predicate(sql: str) -> bool:
    """
    Require the trusted psycopg named parameter in a comparison involving
    business_id.

    This intentionally checks the ORIGINAL SQL, not the parser-normalised SQL.
    """
    return bool(
        re.search(
            r"\bbusiness_id\b\s*=\s*%\(business_id\)s",
            sql,
            flags=re.IGNORECASE,
        )
        or re.search(
            r"%\(business_id\)s\s*=\s*[\w\"\.]*\bbusiness_id\b",
            sql,
            flags=re.IGNORECASE,
        )
    )


def validate_agent_sql(sql: str) -> None:
    """
    Validate LLM-generated SQL before execution.

    Enforces:
    - SELECT/WITH only
    - one statement only
    - parsable PostgreSQL
    - no comments
    - no blocked/system tables
    - only approved business tables
    - trusted %(business_id)s tenant parameter
    - order_items must be joined to orders for tenant scoping
    """
    if not isinstance(sql, str) or not sql.strip():
        raise UnsafeQueryError("SQL is empty.")

    # Reuse the Step 3/4 read-only validator first.
    validate_read_only_sql(sql)

    cleaned = sql.strip()
    lower_sql = cleaned.lower()

    if "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise UnsafeQueryError("SQL comments are not allowed.")

    if "%(business_id)s" not in cleaned:
        raise UnsafeQueryError(
            "Generated SQL is missing the trusted %(business_id)s parameter."
        )

    tree = _parse_one_statement(cleaned)

    # Root must ultimately be a query.
    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        # WITH queries generally parse to the SELECT they wrap.
        if tree.find(exp.Select) is None:
            raise UnsafeQueryError("Only SELECT/WITH queries are allowed.")

    if _contains_forbidden_operation(tree):
        raise UnsafeQueryError("Write or DDL operations are not allowed.")

    tables = _table_names(tree)

    blocked = tables & BLOCKED_TABLES
    if blocked:
        raise UnsafeQueryError(
            f"Blocked table access: {', '.join(sorted(blocked))}"
        )

    # Explicitly reject system schemas/catalogs.
    if any(
        token in lower_sql
        for token in (
            "pg_catalog",
            "information_schema",
            "pg_roles",
            "pg_user",
            "pg_shadow",
        )
    ):
        raise UnsafeQueryError("System catalog access is not allowed.")

    unexpected = tables - ALLOWED_TABLES
    if unexpected:
        raise UnsafeQueryError(
            "Query references table(s) outside the approved schema: "
            + ", ".join(sorted(unexpected))
        )

    if not _has_business_id_predicate(cleaned):
        raise UnsafeQueryError(
            "Query is not tenant-scoped with %(business_id)s."
        )

    # order_items does not contain business_id itself.
    if "order_items" in tables and "orders" not in tables:
        raise UnsafeQueryError(
            "order_items must be joined to orders for tenant isolation."
        )


def assert_safe_sql(sql: str) -> str:
    """
    Convenience helper: validate and return the SQL unchanged.
    """
    validate_agent_sql(sql)
    return sql
