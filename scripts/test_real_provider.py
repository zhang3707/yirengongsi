"""Smoke: real model provider end-to-end through a task."""
import sys, pathlib, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
# Reuse existing .env config; make sure provider picks up the openai branch
from skill_runtime.bootstrap import load_builtin_skills
load_builtin_skills()
from shared.config import settings
from skill_runtime.base import SkillContext
from skill_runtime.executor import SkillExecutor
from shared.model_provider import get_model_provider

provider = get_model_provider()
print('provider:', provider.provider)
assert provider.provider == 'openai', 'provider should be openai with current .env'

output, ms = SkillExecutor().execute(
    'search', {'query': 'AI 公司 Pilot 阶段目标', 'limit': 3},
    context=SkillContext(model=settings.model_name),
)
print(f'search output ({ms}ms):')
import json
print(json.dumps(output, ensure_ascii=False, indent=2)[:1500])
