"""增强版测试 — 搜索边界 + 推荐引擎边界"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from skill_advisor.search import search_local, search_skills, get_stats
from skill_advisor.recommender import SkillRecommender


class TestSearchBoundary(unittest.TestCase):
    """搜索边界测试"""

    def test_empty_string(self):
        """空字符串查询"""
        results = search_local("", limit=5)
        self.assertIsInstance(results, list)

    def test_special_characters(self):
        """特殊字符"""
        results = search_local("!@#$%^&*()", limit=5)
        self.assertIsInstance(results, list)

    def test_sql_injection_attempt(self):
        """SQL 注入尝试"""
        results = search_local("'; DROP TABLE skills_merged; --", limit=5)
        self.assertIsInstance(results, list)
        # 确认表还在
        stats = get_stats()
        self.assertGreater(stats["total_skills"], 0)

    def test_very_long_query(self):
        """超长查询"""
        long_query = "a" * 10000
        results = search_local(long_query, limit=5)
        self.assertIsInstance(results, list)

    def test_chinese_english_mix(self):
        """中英文混合"""
        results = search_local("react前端开发", limit=5)
        self.assertIsInstance(results, list)

    def test_unicode_emoji(self):
        """Unicode 和 emoji"""
        results = search_local("python 搜索", limit=5)
        self.assertIsInstance(results, list)

    def test_whitespace_only(self):
        """仅空白字符"""
        results = search_local("   \n\t  ", limit=5)
        self.assertIsInstance(results, list)

    def test_single_char(self):
        """单字符"""
        results = search_local("a", limit=5)
        self.assertIsInstance(results, list)

    def test_search_result_structure(self):
        """搜索结果结构完整性"""
        results = search_local("react", limit=3)
        for r in results:
            self.assertIn("name", r)
            self.assertIsInstance(r["name"], str)

    def test_limit_zero(self):
        """limit=0"""
        results = search_local("python", limit=0)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_chinese_only(self):
        """纯中文查询"""
        results = search_local("数据分析", limit=5)
        self.assertIsInstance(results, list)


class TestSearchIntegration(unittest.TestCase):
    """搜索集成测试"""

    def test_search_skills_online_flag(self):
        """在线开关"""
        result = search_skills("react", limit=3, online=False)
        self.assertIn("query", result)
        self.assertIn("local_results", result)
        self.assertIn("total", result)
        self.assertEqual(result["query"], "react")

    def test_get_stats_structure(self):
        """统计信息结构"""
        stats = get_stats()
        self.assertIn("total_skills", stats)
        self.assertIn("with_description", stats)
        self.assertIn("database_size_mb", stats)
        self.assertIn("database_path", stats)


class TestRecommenderBoundary(unittest.TestCase):
    """推荐引擎边界测试"""

    def setUp(self):
        self.recommender = SkillRecommender()

    def test_no_match_input(self):
        """无匹配输入"""
        result = self.recommender.recommend("xyznonexistent999")
        self.assertIsNotNone(result)
        self.assertIn("recommendations", result)

    def test_all_professions_detected(self):
        """所有可识别职业"""
        test_cases = [
            ("我是数学老师", "teacher"),
            ("我是产品经理", "product-manager"),
            ("我是自媒体博主", "content-creator"),
        ]
        for query, expected_key in test_cases:
            result = self.recommender.recommend(query)
            self.assertIsNotNone(
                result["profession_pack"],
                f"Failed to detect profession for: {query}"
            )

    def test_numeric_input(self):
        """数字输入"""
        result = self.recommender.recommend("12345")
        self.assertIsNotNone(result)

    def test_recommendations_structure(self):
        """推荐结果结构"""
        result = self.recommender.recommend("react")
        rec = result["recommendations"]
        self.assertIn("required", rec)
        self.assertIn("suggested", rec)
        self.assertIn("later", rec)
        self.assertIn("best_combination", rec)

    def test_profession_pack_has_combo_guide(self):
        """职业包包含组合指南"""
        result = self.recommender.recommend("老师")
        pack = result["profession_pack"]
        self.assertIsNotNone(pack)
        self.assertIn("combo_guide", pack)
        self.assertTrue(len(pack["combo_guide"]) > 0)

    def test_profession_pack_skills_status(self):
        """职业包技能安装状态"""
        result = self.recommender.recommend("老师")
        pack = result["profession_pack"]
        self.assertIn("skills_status", pack)
        self.assertIn("installed_count", pack)
        self.assertGreaterEqual(pack["installed_count"], 0)

    def test_special_chars_input(self):
        """特殊字符输入"""
        result = self.recommender.recommend("!@#$%^")
        self.assertIsNotNone(result)

    def test_recommend_returns_dict(self):
        """推荐返回值类型"""
        result = self.recommender.recommend("anything")
        self.assertIsInstance(result, dict)
        self.assertIn("user_input", result)

    def test_keyword_function(self):
        """recommend 快捷函数"""
        from skill_advisor.recommender import recommend
        result = recommend("老师")
        self.assertIsNotNone(result["profession_pack"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
