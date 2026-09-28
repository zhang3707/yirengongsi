"""Built-in skills matching the Pilot test scenarios (research / analysis / content / flow)."""

from skill_runtime.builtin.analysis import analysis_skill
from skill_runtime.builtin.content import content_skill
from skill_runtime.builtin.ecommerce_publish import ecommerce_publish_skill
from skill_runtime.builtin.market_discovery import (
    market_analysis_skill,
    market_research_skill,
    opportunity_discovery_skill,
    project_feasibility_skill,
)
# T-113a: 导入 market_sources 以触发数据源自动注册
from skill_runtime.builtin import market_sources  # noqa: F401
# T-113b: 注册外部无风控数据源（google_trends / hacker_news）
from skill_runtime.builtin.market_sources_external import register_external_sources
register_external_sources()
from skill_runtime.builtin.market_research_web import market_research_web_skill
from skill_runtime.builtin.report import report_skill
from skill_runtime.builtin.search import search_skill

BUILTIN_SKILLS = (
    search_skill,
    analysis_skill,
    report_skill,
    content_skill,
    ecommerce_publish_skill,
    market_research_skill,
    market_research_web_skill,
    market_analysis_skill,
    opportunity_discovery_skill,
    project_feasibility_skill,
)
