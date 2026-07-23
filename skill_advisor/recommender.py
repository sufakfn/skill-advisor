"""
统一推荐引擎 — skill-advisor 的核心

整合:
  - SQLite 缓存搜索 (本地数万技能)
  - 职业合集包匹配
  - 在线搜索兜底
  - 中文语义扩展
"""

import json
import sqlite3
import urllib.request
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = PACKAGE_DIR / "data" / "skill-advisor.db"

# 职业关键词映射
PROFESSION_MAP = [
    (["老师", "教师", "教授", "讲师", "中学", "小学", "幼儿园"], "teacher"),
    (["程序员", "工程师", "码农", "开发"], "developer"),
    (["产品经理", "产品总监", "PM", "产品专员"], "product-manager"),
    (["设计师", "UI", "UX", "美工", "视觉"], "designer"),
    (["HR", "人事", "人力资源", "招聘", "薪酬"], "hr"),
    (["会计", "财务", "出纳", "审计", "税务"], "finance"),
    (["销售", "BD", "客户", "转化"], "sales"),
    (["律师", "法务", "合同"], "lawyer"),
    (["医生", "医师", "护士", "医疗", "临床"], "doctor"),
    (["学生", "大学生", "研究生", "博士生", "中学生"], "student"),
    (["投资", "炒股", "基金", "金融"], "investor"),
    (["电商", "淘宝", "京东", "拼多多", "开店"], "ecommerce"),
    (["自媒体", "博主", "UP主", "主播", "公众号", "小红书"], "content-creator"),
    (["写作", "作家", "写手", "作者"], "writer"),
    (["求职", "找工作", "面试", "跳槽"], "job-seeker"),
]

# 职业包数据 (精简版, 完整数据在 packs/ 目录)
PROFESSION_PACKS = {
    "teacher": {
        "name": "教师全能包",
        "desc": "把 AI 变成教学助手 —— 出卷、批改、课件、家校沟通全包",
        "skills": [
            {"name": "unit-test", "reason": "自动出卷、批改、生成成绩报告", "required": True},
            {"name": "pptx", "reason": "做课件/说课PPT", "required": True},
            {"name": "dataviz", "reason": "成绩图表、各题正确率分析"},
            {"name": "xlsx", "reason": "成绩汇总表、学生档案管理"},
            {"name": "proactive-agent", "reason": "定时提醒考试/家长会/每日作业"},
            {"name": "agent-memory", "reason": "记录学生薄弱知识点，因材施教"},
        ],
        "combo_guide": "先用 unit-test 出卷 → 考完用 xlsx 和 dataviz 做成绩分析 → 用 agent-memory 记录薄弱点 → 用 pptx 做讲评课件 → 用 proactive-agent 定时提醒下次考试。",
    },
    "product-manager": {
        "name": "产品经理包",
        "desc": "PRD → 竞品 → 调研 → 路线图的完整产品工作流",
        "skills": [
            {"name": "product-manager-toolkit", "reason": "PRD模板、竞品分析、用户故事地图", "required": True},
            {"name": "deep-research-pro", "reason": "深度行业调研报告", "required": True},
            {"name": "web-design-analyzer", "reason": "竞品UI分析、设计对标"},
            {"name": "market-research-reports", "reason": "市场调研报告"},
            {"name": "pptx", "reason": "产品汇报、路演PPT"},
        ],
        "combo_guide": "用 deep-research-pro 做行业调研 → 用 web-design-analyzer 分析竞品 → 用 product-manager-toolkit 写PRD → 用 pptx 做汇报。",
    },
    "content-creator": {
        "name": "自媒体创作者包",
        "desc": "从选题到发布的全流程 —— 公众号、小红书、短视频全覆盖",
        "skills": [
            {"name": "wechat-hotspot-publisher", "reason": "热点文自动生成+发布", "required": True},
            {"name": "baoyu-post-to-wechat", "reason": "公众号排版发文", "required": True},
            {"name": "video-creation-suite", "reason": "短视频制作全流程"},
            {"name": "tts-voice-synthesis", "reason": "视频配音、旁白"},
        ],
        "combo_guide": "用 wechat-hotspot-publisher 追热点 → 用 baoyu-post-to-wechat 发公众号 → 用 video-creation-suite + tts-voice-synthesis 做视频版。",
    },
}


class SkillRecommender:
    """
    技能推荐引擎

    用法:
        recommender = SkillRecommender()
        result = recommender.recommend("我是数学老师")
        print(result["profession_pack"])
        # 或
        result = recommender.recommend("股票分析")
        print(result["recommendations"])
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    def recommend(self, user_input):
        """
        根据用户输入生成推荐

        返回 dict 包含:
          - profession_pack: 如果匹配到职业
          - recommendations: {required, suggested, later, best_combination}
          - search_results: 原始搜索结果
        """
        result = {
            "user_input": user_input,
            "profession_pack": None,
            "recommendations": {"required": [], "suggested": [], "later": [], "best_combination": []},
            "search_results": None,
        }

        # 1. 检测职业身份
        profession = self._detect_profession(user_input)
        if profession and profession in PROFESSION_PACKS:
            pack = PROFESSION_PACKS[profession]
            pack["slug"] = profession
            result["profession_pack"] = self._enrich_pack(pack)
            return result

        # 2. 非职业 → 语义搜索
        search_result = self._search(user_input)
        result["search_results"] = search_result

        all_skills = search_result.get("local_results", []) + search_result.get("online_results", [])
        if not all_skills:
            return result

        # 3. 分级
        for skill in all_skills:
            entry = {
                "name": skill.get("name", "?"),
                "desc": (skill.get("description") or "")[:200],
                "installs": skill.get("installs", 0),
                "quality": skill.get("quality_score", 0),
            }
            if skill.get("quality_score", 0) >= 40 or skill.get("installs", 0) >= 10000:
                result["recommendations"]["required"].append(entry)
            elif skill.get("quality_score", 0) >= 20 or skill.get("installs", 0) >= 1000:
                result["recommendations"]["suggested"].append(entry)
            else:
                result["recommendations"]["later"].append(entry)

        result["recommendations"]["required"] = result["recommendations"]["required"][:6]
        result["recommendations"]["suggested"] = result["recommendations"]["suggested"][:6]

        # 4. 最佳组合
        combo = result["recommendations"]["required"][:3] + result["recommendations"]["suggested"][:2]
        result["recommendations"]["best_combination"] = combo[:5]

        return result

    def _detect_profession(self, query):
        """检测用户职业身份"""
        for keywords, profession in PROFESSION_MAP:
            for kw in keywords:
                if kw in query:
                    return profession
        return None

    def _enrich_pack(self, pack):
        """检查职业包中各技能的安装状态"""
        installed = self._get_installed_skills()
        pack["skills_status"] = []
        for skill in pack.get("skills", []):
            name = skill["name"]
            base = name.split("（")[0].strip().lower().replace("-", "")
            is_installed = any(
                base in d or d.startswith(base) for d in installed
            )
            pack["skills_status"].append({
                **skill,
                "installed": is_installed,
            })
        pack["installed_count"] = sum(1 for s in pack["skills_status"] if s["installed"])
        return pack

    def _get_installed_skills(self):
        """获取本地已安装的 skill 目录名"""
        skill_dirs = [
            Path.home() / ".claude" / "skills",
            Path.home() / ".cursor" / "skills",
            Path.home() / ".codex" / "skills",
            Path.home() / ".agents" / "skills",
        ]
        installed = set()
        for base_dir in skill_dirs:
            if base_dir.exists():
                for d in base_dir.iterdir():
                    if d.is_dir():
                        installed.add(d.name.lower().replace("-", ""))
        return installed

    def _search(self, query):
        """搜索技能"""
        from .search import search_skills
        return search_skills(query, limit=15, online=True, db_path=str(self.db_path))


def recommend(user_input, db_path=None):
    """convenience function"""
    r = SkillRecommender(db_path)
    return r.recommend(user_input)


def main():
    """CLI entry point - called by pyproject.toml [project.scripts]"""
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "teacher"
    r = SkillRecommender()
    result = r.recommend(query)

    if result["profession_pack"]:
        pack = result["profession_pack"]
        installed = pack["installed_count"]
        total = len(pack["skills_status"])
        print(f"PACK: {pack['name']} ({installed}/{total} installed)")
        print()
        for s in pack["skills_status"]:
            if s["installed"]:
                icon = "[OK]"
            elif s.get("required"):
                icon = "[REQ]"
            else:
                icon = "[  ]"
            print(f"  {icon} {s['name']} - {s['reason']}")
        print()
        print(f"COMBO: {pack.get('combo_guide', '')}")
    else:
        rec = result["recommendations"]
        if rec["required"]:
            print("[REQ] Required:")
            for s in rec["required"]:
                print(f"  - {s['name']}: {s['desc'][:60]}")
        if rec["suggested"]:
            print("[SUG] Suggested:")
            for s in rec["suggested"]:
                print(f"  - {s['name']}: {s['desc'][:60]}")
        if rec["later"]:
            print("[LTR] Later:")
            for s in rec["later"]:
                print(f"  - {s['name']}: {s['desc'][:60]}")
        if rec["best_combination"]:
            print()
            print("[TOP] Best Combo:")
            for s in rec["best_combination"]:
                print(f"  - {s['name']}: {s['desc'][:60]}")
