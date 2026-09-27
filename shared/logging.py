"""Logging setup. Log outputs follow the layout documented in the runbook: logs/<service>/."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from shared.config import settings

_CONFIGURED: set[str] = set()

SERVICE_LOG_DIRS = ("backend", "agent", "workflow", "skill", "system")


def configure_logging(service: str = "system", level: int = logging.INFO) -> logging.Logger:
    """Configure a namespaced logger writing to both stdout and logs/<service>/<service>.log."""
    if service not in SERVICE_LOG_DIRS:
        service = "system"

    logger = logging.getLogger(f"ai_company.{service}")
    logger.setLevel(level)
    logger.propagate = False

    if service in _CONFIGURED:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    log_file: Path = settings.log_dir_path / service / f"{service}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _CONFIGURED.add(service)
    return logger


def get_logger(service: str = "system") -> logging.Logger:
    return configure_logging(service)
