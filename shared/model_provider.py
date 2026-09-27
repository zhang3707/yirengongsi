"""Unified model provider layer used by builtin skills.

Contracts:
  * providers implement `complete(system: str, user: str, context: SkillContext) -> str`
  * `settings.model_provider` selects the implementation ("mock" | "openai"); an
    unknown value falls back to the deterministic mock with a loud warning.
  * real providers honour MODEL_BASE_URL / MODEL_API_KEY / MODEL_NAME /
    MODEL_TIMEOUT_SECONDS; failures raise ModelProviderError so the workflow
    step can retry / fail loudly instead of silently degrading.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from shared.config import settings
from shared.logging import get_logger
from skill_runtime.base import SkillContext

logger = get_logger("skill")


class ModelProviderError(RuntimeError):
    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(f"model provider '{provider}' failed: {reason}")
        self.provider = provider
        self.reason = reason


def extract_json_block(text: str) -> Any:
    """Best-effort JSON extraction from a model reply."""
    match = re.search(r"```(?:json)?\s*(.+?)```", text, flags=re.DOTALL)
    if match:
        text = match.group(1)
    start = text.find("{")
    alt = text.find("[")
    if alt != -1 and (start == -1 or alt < start):
        start = alt
    if start == -1:
        raise ValueError("no JSON payload in model reply")
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start : end + 1])


class MockProvider:
    """Deterministic fallback used for tests and the default Pilot state."""

    provider = "mock"

    def complete(self, system: str, user: str, context: SkillContext | None = None) -> str:
        return json.dumps(
            {"reply": f"[mock] {user.strip()[:160]}", "system": system.strip()[:120]},
            ensure_ascii=False,
        )


class OpenAICompatibleProvider:
    """Works with OpenAI, DeepSeek, Moonshot, Qwen and any /chat/completions server."""

    provider = "openai"

    def __init__(self) -> None:
        if not settings.model_api_key:
            raise ModelProviderError(
                self.provider, "MODEL_API_KEY is empty; set it in .env before using this provider"
            )
        if not settings.model_base_url:
            raise ModelProviderError(
                self.provider,
                "MODEL_BASE_URL is empty; e.g. https://api.openai.com/v1 or https://api.deepseek.com/v1",
            )

    def complete(self, system: str, user: str, context: SkillContext | None = None) -> str:
        url = settings.model_base_url.rstrip("/") + "/chat/completions"
        model = settings.model_name or "gpt-4o-mini"
        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {settings.model_api_key}"}
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=settings.model_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise ModelProviderError(self.provider, f"{exc.__class__.__name__}: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelProviderError(self.provider, f"unexpected response shape: {exc}") from exc


def get_model_provider() -> Any:
    name = (settings.model_provider or "mock").strip().lower()
    if name == "mock":
        provider = MockProvider()
    elif name in {"openai", "openai_compatible", "openai-compatible"}:
        provider = OpenAICompatibleProvider()
    else:
        logger.warning("unknown MODEL_PROVIDER=%s, falling back to mock", name)
        provider = MockProvider()
    logger.debug("model provider resolved: %s", provider.provider)
    return provider
