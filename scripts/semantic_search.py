#!/usr/bin/env python3
"""语义搜索 v1 - 同义词扩展 + FTS5 匹配（仅已验证技能）"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

SYNONYM_MAP = {
    "演示": ["演示", "汇报", "幻灯片", "ppt", "presentation"],
    "前端": ["前端", "frontend", "react", "vue", "css", "html"],
    "后端": ["后端", "backend", "server", "api", "database"],
    "测试": ["测试", "test", "testing", "jest", "pytest"],
    "部署": ["部署", "deploy", "deployment", "docker", "kubernetes"],
    "数据库": ["数据库", "database", "sql", "postgres", "mysql"],
    "安全": ["安全", "security", "auth", "oauth", "jwt"],
    "文档": ["文档", "documentation", "docs", "readme"],
    "支付": ["支付", "payment", "stripe", "paypal"],
    "搜索": ["搜索", "search", "find", "filter", "query"],
    "登录": ["登录", "login", "signin", "auth"],
    "注册": ["注册", "signup", "register", "onboarding"],
    "动画": ["动画", "animation", "motion", "transition"],
    "图表": ["图表", "chart", "graph", "plot", "d3"],
    "可视化": ["可视化", "visualization", "dataviz", "dashboard"],
    "机器学习": ["机器学习", "machine-learning", "ml", "ai"],
    "人工智能": ["人工智能", "ai", "gpt", "llm", "claude"],
    "重构": ["重构", "refactor", "refactoring"],
    "性能": ["性能", "performance", "optimize", "cache"],
    "监控": ["监控", "monitoring", "alert", "log", "sentry"],
    "API": ["API", "api", "rest", "graphql", "endpoint"],
    "错误": ["错误", "error", "exception", "bug"],
    "构建": ["构建", "build", "bundle", "webpack"],
    "发布": ["发布", "release", "publish", "deploy"],
}


def expand_query(query):
    terms = set()
    terms.add(query)
    for key, synonyms in SYNONYM_MAP.items():
        if key in query:
            terms.update(synonyms)
    for key, synonyms in SYNONYM_MAP.items():
        for syn in synonyms:
            if syn in query:
                terms.add(key)
                terms.update(synonyms)
    for w in query.lower().split():
        terms.add(w)
        for key, synonyms in SYNONYM_MAP.items():
            if w in synonyms:
                terms.add(key)
                terms.update(synonyms)
    return list(terms)


def semantic_search(query, limit=10, db_path=DB_PATH):
    terms = expand_query(query)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    results = []
    seen_ids = set()

    for term in terms:
        if len(term) < 2:
            continue
        try:
            rows = conn.execute(
                "SELECT m.id, m.name, m.description, m.source, m.installs, "
                "m.topics, m.urls, m.quality_score, bm25(skills_fts) AS relevance "
                "FROM skills_fts fts JOIN skills_merged m ON m.id = fts.rowid "
                "WHERE m.verified = 1 AND skills_fts MATCH ? ORDER BY relevance LIMIT ?",
                (term, limit)).fetchall()
            for row in rows:
                if row["id"] not in seen_ids:
                    results.append(dict(row))
                    seen_ids.add(row["id"])
        except Exception:
            pass

    if len(results) < limit:
        for term in terms:
            like = "%" + term + "%"
            rows = conn.execute(
                "SELECT id, name, description, source, installs, topics, urls, quality_score, 0 AS relevance "
                "FROM skills_merged "
                "WHERE verified = 1 AND (name LIKE ? OR description LIKE ?) AND id NOT IN (" +
                (",".join(str(i) for i in seen_ids) if seen_ids else "0") + ") LIMIT ?",
                (like, like, limit - len(results))).fetchall()
            for row in rows:
                if row["id"] not in seen_ids:
                    results.append(dict(row))
                    seen_ids.add(row["id"])

    conn.close()
    results.sort(key=lambda x: (-(x.get("relevance") or 0), -x.get("quality_score", 0)))
    return {"query": query, "expanded_terms": terms, "results": results[:limit], "total": len(results[:limit])}


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "前端开发"
    limit = 10
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])
    result = semantic_search(query, limit=limit)
    print(json.dumps({
        "query": result["query"],
        "expanded_terms": result["expanded_terms"],
        "total": result["total"],
        "results": [{"name": r["name"], "description": (r.get("description") or "")[:100], "source": r.get("source", ""), "quality_score": r.get("quality_score", 0)} for r in result["results"]]
    }, ensure_ascii=False, indent=2))
