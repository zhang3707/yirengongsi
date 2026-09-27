"""ecommerce_publish: submit a listing task to the EcomAutopilot browser-service.

Integration contract (see EcomAutopilot docs/architecture/publish-service.md):
  * HTTP-only; we do NOT import EcomAutopilot internals (its R1/R9 rules stay intact).
  * Default is dry_run=True — we never touch a real browser without explicit approval.
  * Real publish requires policy_approval={"allowed": True, "token": "publish"}.
  * Every step is persisted so the AI-company console can show a full audit trail.
"""

from __future__ import annotations

from typing import Any

import httpx

from shared.config import settings
from shared.logging import get_logger
from skill_runtime.base import SkillContext, SkillDefinition

logger = get_logger("skill")

_URL_BUILD = "/publish/build"
_URL_VALIDATE = "/publish/validate"
_URL_RUN = "/publish/run"
_URL_STATUS = "/publish/runs/"


class EcomAutopilotError(RuntimeError):
    pass


def _base_url() -> str:
    return (settings.ecom_autopilot_base_url or "").rstrip("/")


def _token() -> str:
    return settings.ecom_autopilot_token or "dev-token"


def _post(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    response = client.post(url, json=payload, timeout=settings.ecom_autopilot_timeout_seconds)
    if response.status_code >= 400:
        raise EcomAutopilotError(f"POST {path} -> {response.status_code}: {response.text[:300]}")
    data = response.json()
    if not isinstance(data, dict):
        raise EcomAutopilotError(f"unexpected response from {path}: {str(data)[:200]}")
    return data


def _get(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(f"{_base_url()}{path}", timeout=settings.ecom_autopilot_timeout_seconds)
    if response.status_code >= 400:
        raise EcomAutopilotError(f"GET {path} -> {response.status_code}: {response.text[:300]}")
    data = response.json()
    if not isinstance(data, dict):
        raise EcomAutopilotError(f"unexpected response from {path}: {str(data)[:200]}")
    return data


def _render_markdown(product_dir: str, build: dict, validation: dict, run: dict) -> str:
    lines = [f"# 电商发布报告 · {product_dir}", ""]
    build_report = build.get("report") or []
    if build_report:
        lines += ["## 一、构建来源 / 回填报告"]
        lines += [f"- {item}" for item in build_report]

    issues = validation.get("issues") if isinstance(validation.get("issues"), list) else []
    lines += ["", f"## 二、离线校验 · {validation.get('ok', 'unknown')}"]
    lines += [f"- {item}" for item in issues] or ["- 无问题"]

    lines += ["", "## 三、run 状态"]
    for key, label in (
        ("status", "状态"), ("runId", "runId"), ("goodsId", "goodsId"),
        ("failedStep", "失败步骤"), ("exitStatus", "退出状态"),
    ):
        if run.get(key) is not None:
            lines.append(f"- {label}: {run[key]}")
    return "\n".join(lines)


def _handler(context: SkillContext, inputs: dict[str, Any]) -> dict[str, Any]:
    product_dir = str(inputs.get("product_dir") or inputs.get("productDir") or "").strip()
    if not product_dir:
        raise EcomAutopilotError("input error: product_dir is required")

    mode = str(inputs.get("mode") or "draft")
    recipe = str(inputs.get("recipe") or "product.create-basic")
    account = str(inputs.get("account") or "default")
    dry_run = bool(inputs.get("dry_run", True))       # 默认 dry run
    approval = inputs.get("policy_approval")          # 必须显式传入才能真跑

    if not dry_run and not approval:
        raise EcomAutopilotError(
            "real publish requires policy_approval={'allowed': True, 'token': 'publish'}; "
            "dry_run only when absent"
        )

    base = _base_url()
    if not base:
        raise EcomAutopilotError(
            "ECOM_AUTOPILOT_BASE_URL is empty; set it in .env before using this skill"
        )

    headers = {"X-Exec-Token": _token()}
    started = context.extra.get("started_at") or "n/a"
    logger.info("ecommerce_publish %s product=%s mode=%s dry_run=%s",
                started, product_dir, mode, dry_run)

    with httpx.Client(headers=headers) as client:
        build = _post(client, "/publish/build", {"productDir": product_dir, "mode": mode})
        validation = _post(client, "/publish/validate",
                           {"request": build.get("request"), "recipe": recipe})
        if not validation.get("ok", False):
            logger.warning("ecommerce_publish validation failed for %s: %s",
                           product_dir, validation.get("issues"))
            run = {"status": "blocked", "reason": "validation_failed",
                   "validation": validation}
        else:
            submit_payload = {
                "request": build.get("request"),
                "recipe": recipe,
                "account": account,
                "dryRun": dry_run,
            }
            if approval:
                submit_payload["policyApproval"] = approval
            submitted = _post(client, "/publish/run", submit_payload)
            if dry_run:
                # browser-service dry_run 同步返回，不产生 runId； 归一化为 run dict
                raw = submitted.get("data") or {}
                run = {
                    "status": "finished",
                    "dry_run": True,
                    "ok": bool(submitted.get("ok")),
                    "code": submitted.get("code"),
                    "results_count": len(raw.get("results") or []),
                    "logTail": (raw.get("logTail") or "")[:600],
                }
            else:
                run_id = (submitted.get("data") or {}).get("runId") or submitted.get("runId")
                if not run_id:
                    run = {
                        "status": "failed",
                        "reason": "no runId in submit response",
                        "raw": submitted,
                    }
                else:
                    status_response = _get(client, f"/publish/runs/{run_id}")
                    run = dict(status_response.get("data") or {})
                    run["ok"] = bool(status_response.get("ok"))
                    run["code"] = status_response.get("code")
                    run["message"] = status_response.get("message")

    markdown = _render_markdown(product_dir, build, validation, run)
    return {
        "product_dir": product_dir,
        "mode": mode,
        "recipe": recipe,
        "dry_run": dry_run,
        "validation_ok": bool(validation.get("ok", False)),
        "run": run,
        "build_report_count": len(build.get("report") or []),
        "report_markdown": markdown,
        "summary": f"[{mode}] {product_dir} · validation={validation.get('ok')} · run={run.get('status')}",
    }


ecommerce_publish_skill = SkillDefinition(
    name="ecommerce_publish",
    category="ecommerce",
    description=(
        "把一个商品（products/DJ-YYYY-XXX）发给 EcomAutopilot 的 browser-service "
        "做构建/校验/异步发布（默认干跑）。"
    ),
    handler=_handler,
    input_schema={
        "product_dir": "string",
        "mode": "string?",
        "recipe": "string?",
        "account": "string?",
        "dry_run": "boolean?",
        "policy_approval": "object?",
    },
    output_schema={
        "product_dir": "string",
        "validation_ok": "boolean",
        "run": "object",
        "report_markdown": "string",
    },
)
