"""
skill-advisor — 智能技能推荐引擎

根据用户身份、职业、场景或具体需求，从数万技能中智能推荐。
支持 Claude Code、Cursor、Codex CLI、Gemini CLI 等任何 SKILL.md 兼容智能体。

用法:
    from skill_advisor import SkillRecommender
    recommender = SkillRecommender()
    result = recommender.recommend("我是数学老师")
"""

__version__ = "6.1.0"
__author__ = "skill-advisor contributors"

from .recommender import SkillRecommender, recommend
from .search import search_skills, search_local, get_stats

__all__ = [
    "SkillRecommender",
    "recommend",
    "search_skills",
    "search_local",
    "get_stats",
    "__version__",
]
