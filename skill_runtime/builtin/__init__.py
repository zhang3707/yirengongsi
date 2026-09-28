"""Built-in skills matching the Pilot test scenarios (research / analysis / content / flow)."""

# T-113a/b: 导入即触发数据源自动注册（副作用导入，需在其它 import 之前/之后的追加行）
from skill_runtime.builtin import (
    market_sources,  # noqa: F401,E402  - registers taobao/pdd/manual_import/mock
)
from skill_runtime.builtin.market_sources_external import register_external_sources  # noqa: E402

register_external_sources()  # registers google_trends / hacker_news

from skill_runtime.builtin.analysis import analysis_skill  # noqa: E402
from skill_runtime.builtin.content import content_skill  # noqa: E402
from skill_runtime.builtin.ecommerce_publish import ecommerce_publish_skill  # noqa: E402
from skill_runtime.builtin.market_discovery import (  # noqa: E402
    market_analysis_skill,
    market_research_skill,
    opportunity_discovery_skill,
    project_feasibility_skill,
)
from skill_runtime.builtin.market_research_web import market_research_web_skill  # noqa: E402
from skill_runtime.builtin.report import report_skill  # noqa: E402
from skill_runtime.builtin.search import search_skill  # noqa: E402

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
