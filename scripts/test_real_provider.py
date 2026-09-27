"""Smoke: real model provider end-to-end through a skill (requires .env)."""

from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shared.config import settings  # noqa: E402
from shared.model_provider import get_model_provider  # noqa: E402
from skill_runtime.base import SkillContext  # noqa: E402
from skill_runtime.bootstrap import load_builtin_skills  # noqa: E402
from skill_runtime.executor import SkillExecutor  # noqa: E402

load_builtin_skills()

provider = get_model_provider()
print("provider:", provider.provider)
print("model:", settings.model_name, "in", os.getenv("ENVIRONMENT", "development"), "env")
assert provider.provider == "openai", "provider should be openai with current .env"

output, ms = SkillExecutor().execute(
    "search",
    {"query": "AI 公司 Pilot 阶段目标", "limit": 3},
    context=SkillContext(model=settings.model_name),
)
print(f"search output ({ms}ms):")
print(json.dumps(output, ensure_ascii=False, indent=2)[:1500])
