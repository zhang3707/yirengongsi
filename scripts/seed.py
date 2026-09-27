"""Initialize the database and seed Pilot demo data.

Usage:
    python scripts/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.seed import seed_demo_data
from shared.config import settings
from shared.database import SessionLocal, init_db
from shared.logging import get_logger

logger = get_logger("system")


def main() -> int:
    logger.info("initializing database (%s)", settings.environment)
    init_db()
    with SessionLocal() as db:
        summary = seed_demo_data(db)
    print("seed 完成：", summary)
    print("启动服务：python -m uvicorn backend.main:app --reload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
