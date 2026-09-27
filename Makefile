.PHONY: help install dev test smoke seed check migrate lint

help:
	@echo "install  - 安装依赖（含 dev）"
	@echo "test     - 运行全量测试"
	@echo "smoke    - 端到端冒烟测试"
	@echo "seed     - 初始化数据库并注入演示数据"
	@echo "check    - Pilot 每日巡检"
	@echo "migrate  - 执行数据库迁移"
	@echo "lint     - ruff 静态检查"

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

smoke:
	python scripts/smoke_test.py

seed:
	python scripts/seed.py

check:
	python monitoring/daily_check.py

migrate:
	alembic upgrade head

lint:
	python -m ruff check .

dev:
	python -m uvicorn backend.main:app --reload
