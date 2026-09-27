"""Workflow worker entry point.

In Pilot mode the worker runs in-process (the API executes workflows inline) so a
single container is enough. When Temporal is enabled, run this module as the
standalone worker process: `python -m backend.worker`.
"""

from __future__ import annotations

import signal
import time

from shared.config import settings
from shared.database import SessionLocal, init_db
from shared.logging import get_logger

logger = get_logger("workflow")


def main() -> None:
    init_db()
    logger.info("workflow worker started (temporal_host=%s)", settings.temporal_host)
    running = True

    def _stop(*_args) -> None:
        nonlocal running
        running = False
        logger.info("workflow worker stopping")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    with SessionLocal():
        pass

    while running:
        time.sleep(5)


if __name__ == "__main__":
    main()
