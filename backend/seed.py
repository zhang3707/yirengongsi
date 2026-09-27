"""Demo seed data for the Pilot environment (agents, knowledge, sample content)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from knowledge_service.service import KnowledgeService
from shared.logging import get_logger
from skill_runtime.bootstrap import load_builtin_skills, sync_skills_to_db

logger = get_logger("system")

AGENTS = [
    {
        "name": "Research Agent",
        "role": "负责信息分析",
        "description": "负责收集和整理信息，输出可复核的资料线索。",
        "domain": "research",
        "skills": ["search", "analysis", "report"],
    },
    {
        "name": "Analytics Agent",
        "role": "负责业务数据分析",
        "description": "分析业务数据，发现异常并给出建议。",
        "domain": "analysis",
        "skills": ["analysis", "report"],
    },
    {
        "name": "Content Agent",
        "role": "负责内容生产",
        "description": "根据资料生成方案、文章、报告与总结。",
        "domain": "content",
        "skills": ["content", "report"],
    },
    {
        "name": "Workflow Agent",
        "role": "负责流程管理",
        "description": "负责任务分配、执行跟踪与结果汇总。",
        "domain": "workflow",
        "skills": ["analysis", "report"],
    },
]

KNOWLEDGE = [
    {
        "title": "Pilot 阶段开发规则",
        "content": (
            "P0 立即修复：系统不可用、数据错误、核心流程失败。P1 进入优化：高频问题、"
            "明确影响。P2 进入需求池：体验优化、效率提升。P3 暂不处理：偶发、无明显价值。"
        ),
        "tags": ["pilot", "规则", "优先级"],
        "source": "01_真实运行Pilot计划",
    },
    {
        "title": "Pilot 启动检查清单",
        "content": (
            "每日检查：API、Database、Redis、Temporal；Agent 在线状态、Workflow 状态、"
            "异常任务；任务数量、错误数量、运行时间。"
        ),
        "tags": ["运维", "检查清单"],
        "source": "02_部署与运行手册",
    },
    {
        "title": "首批用户评价维度",
        "content": (
            "结果质量 1-5 分；节省时间（原耗时 / AI 耗时 / 节省比例）；使用体验（易用、"
            "可理解、愿意继续使用）；信任程度（是否需要人工检查、是否敢直接用）。"
        ),
        "tags": ["用户测试", "评价", "反馈"],
        "source": "03_首批用户测试方案",
    },
]


def seed_demo_data(db: Session) -> dict:
    load_builtin_skills()
    skill_count = sync_skills_to_db(db)

    registry = AgentRegistry(db)
    agent_count = 0
    for payload in AGENTS:
        if registry.get_by_name(payload["name"]) is None:
            registry.create(**payload)
            agent_count += 1

    knowledge_service = KnowledgeService(db)
    existing_titles = {entry.title for entry in knowledge_service.list(limit=200)}
    knowledge_count = 0
    for payload in KNOWLEDGE:
        if payload["title"] not in existing_titles:
            knowledge_service.create(**payload)
            knowledge_count += 1

    db.commit()
    logger.info(
        "seed complete: skills=%s agents=%s knowledge=%s",
        skill_count,
        agent_count,
        knowledge_count,
    )
    return {
        "skills": skill_count,
        "agents_created": agent_count,
        "knowledge_created": knowledge_count,
    }
