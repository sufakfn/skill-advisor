"""基础测试 — 验证搜索引擎和推荐引擎"""

import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from skill_advisor.search import search_local, search_skills, get_stats
from skill_advisor.recommender import SkillRecommender


class TestSearch(unittest.TestCase):
    """搜索功能测试"""

    def test_search_english(self):
        """英文搜索"""
        results = search_local("react", limit=5)
        self.assertIsInstance(results, list)
        if results:
            self.assertIn("name", results[0])

    def test_search_chinese(self):
        """中文搜索"""
        results = search_local("ppt", limit=5)
        self.assertIsInstance(results, list)

    def test_search_no_match(self):
        """无匹配查询"""
        results = search_local("xyznonexistent123", limit=5)
        self.assertIsInstance(results, list)

    def test_get_stats(self):
        """统计信息"""
        stats = get_stats()
        self.assertIn("total_skills", stats)
        self.assertGreater(stats["total_skills"], 0)


class TestRecommender(unittest.TestCase):
    """推荐引擎测试"""

    def test_profession_teacher(self):
        """教师身份识别"""
        r = SkillRecommender()
        result = r.recommend("我是数学老师")
        self.assertIsNotNone(result["profession_pack"])

    def test_profession_pm(self):
        """产品经理身份识别"""
        r = SkillRecommender()
        result = r.recommend("我是产品经理")
        self.assertIsNotNone(result["profession_pack"])

    def test_generic_search(self):
        """通用搜索推荐"""
        r = SkillRecommender()
        result = r.recommend("react前端开发")
        self.assertIsNotNone(result["recommendations"])

    def test_empty_input(self):
        """空输入"""
        r = SkillRecommender()
        result = r.recommend("")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
