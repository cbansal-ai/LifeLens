"""
Run:
    pytest -q test_sql_guardrails.py

These tests do not call OpenAI or PostgreSQL.
They test only the deterministic SQL safety layer.
"""

import pytest

from business_db import UnsafeQueryError
from sql_guardrails import validate_agent_sql


SAFE_QUERIES = [
    """
    SELECT SUM(total_amount)
    FROM orders
    WHERE business_id = %(business_id)s
    """,
    """
    SELECT c.customer_id, c.first_name, c.last_name,
           SUM(o.total_amount) AS total_sales
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.business_id = %(business_id)s
    GROUP BY c.customer_id, c.first_name, c.last_name
    ORDER BY total_sales DESC
    LIMIT 5
    """,
    """
    SELECT p.product_name,
           SUM(oi.quantity * oi.unit_price) AS revenue
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.business_id = %(business_id)s
    GROUP BY p.product_name
    ORDER BY revenue DESC
    LIMIT 5
    """,
    """
    WITH monthly_sales AS (
        SELECT DATE_TRUNC('month', order_date) AS month,
               SUM(total_amount) AS sales
        FROM orders
        WHERE business_id = %(business_id)s
        GROUP BY DATE_TRUNC('month', order_date)
    )
    SELECT month, sales
    FROM monthly_sales
    ORDER BY month DESC
    LIMIT 6
    """,
]


UNSAFE_QUERIES = [
    # Write
    "DELETE FROM orders WHERE business_id = %(business_id)s",

    # Missing tenant scope
    "SELECT * FROM orders",

    # Hard-coded tenant instead of trusted parameter
    "SELECT * FROM orders WHERE business_id = 101",

    # Sensitive table
    "SELECT * FROM users WHERE business_id = %(business_id)s",

    # Existing personal-data table
    "SELECT * FROM events WHERE business_id = %(business_id)s",

    # System catalog
    """
    SELECT tablename
    FROM pg_catalog.pg_tables
    WHERE business_id = %(business_id)s
    """,

    # Multiple statements
    """
    SELECT * FROM orders WHERE business_id = %(business_id)s;
    SELECT * FROM customers WHERE business_id = %(business_id)s;
    """,

    # Comment
    """
    SELECT * FROM orders
    WHERE business_id = %(business_id)s -- ignore safety
    """,

    # order_items lacks its own tenant key: must go through orders
    """
    SELECT *
    FROM order_items
    WHERE business_id = %(business_id)s
    """,
]


@pytest.mark.parametrize("sql", SAFE_QUERIES)
def test_safe_queries_pass(sql):
    validate_agent_sql(sql)


@pytest.mark.parametrize("sql", UNSAFE_QUERIES)
def test_unsafe_queries_are_blocked(sql):
    with pytest.raises(UnsafeQueryError):
        validate_agent_sql(sql)
