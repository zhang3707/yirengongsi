"""Run-log writer: persists structured events into the `logs` table."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models import LogEntry


def record_event(
    db: Session,
    event: str,
    *,
    service: str = "system",
    level: str = "INFO",
    message: str = "",
    context: dict[str, Any] | None = None,
) -> LogEntry:
    entry = LogEntry(
        level=level,
        service=service,
        event=event,
        message=message,
        context=context or {},
    )
    db.add(entry)
    db.flush()

    logger = get_logger(service)
    rendered = f"{event} | {message}" if message else event
    if level == "ERROR":
        logger.error(rendered)
    elif level == "WARNING":
        logger.warning(rendered)
    else:
        logger.info(rendered)
    return entry
