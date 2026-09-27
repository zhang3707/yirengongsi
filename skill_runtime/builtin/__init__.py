"""Built-in skills matching the Pilot test scenarios (research / analysis / content / flow)."""

from skill_runtime.builtin.analysis import analysis_skill
from skill_runtime.builtin.content import content_skill
from skill_runtime.builtin.report import report_skill
from skill_runtime.builtin.search import search_skill

BUILTIN_SKILLS = (search_skill, analysis_skill, report_skill, content_skill)
