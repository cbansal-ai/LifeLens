"""Structured observability helpers for LifeLens."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("lifelens")


def new_trace_id() -> str:
    return uuid.uuid4().hex


def user_hash(email: str) -> str:
    normalized = (email or "").strip().lower()
    if not normalized:
        return "anonymous"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def _safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    return str(value)


def log_event(event: str, *, trace_id: str, level: int = logging.INFO, **fields: Any) -> None:
    payload = {
        "event": event,
        "trace_id": trace_id,
        **{key: _safe(value) for key, value in fields.items()},
    }
    logger.log(level, json.dumps(payload, sort_keys=True))


@contextmanager
def observed_step(step: str, *, trace_id: str, **fields: Any) -> Iterator[dict[str, Any]]:
    started = time.perf_counter()
    state: dict[str, Any] = {}
    log_event(f"{step}.start", trace_id=trace_id, **fields)

    try:
        yield state
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            f"{step}.error",
            trace_id=trace_id,
            level=logging.ERROR,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
            error=str(exc),
            **fields,
        )
        raise
    else:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            f"{step}.success",
            trace_id=trace_id,
            latency_ms=latency_ms,
            **fields,
            **state,
        )
