"""
SQLite 搜索引擎 — 基于 skill-advisor.db 的快速搜索

支持:
  - FTS5 全文搜索 (名字 + 描述 + 标签)
  - LIKE 模糊匹配 (中文友好)
  - 在线搜索兜底 (skills.sh + ClawHub)
"""

import json
import os
import re
import sqlite3
import time
import urllib.request
from pathlib import Path

# 默认数据库路径: 包内 data/ 目录
PACKAGE_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = PACKAGE_DIR / "data" / "skills.db"

# 在线搜索端点
SKILLS_SH_API = "https://skills.sh/api/search"
CLAWHUB_API = "https://clawhub.ai/api/v1/skills"


def search_local(query, limit=10, db_path=None):
    """
    本地 SQLite 搜索

    参数:
        query: 搜索词 (中英文均可)
        limit: 返回数量
        db_path: 数据库路径 (默认使用包内 data/skill-advisor.db)

    返回: [{name, description, installs, stars, ...}, ...]
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not Path(db_path).exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    results = []
    seen_ids = set()

    # 判断查询类型: 中文 → LIKE, 英文 → FTS5
    has_chinese = any('一' <= c <= '鿿' for c in query)

    try:
        if has_chinese or len(query) < 3:
            # 中文查询 或 短查询 → LIKE 搜索
            like_pattern = f"%{query}%"
            rows = conn.execute("""
                SELECT id, name, description, source, installs, stars,
                       topics, urls, quality_score, 0 AS relevance
                FROM skills_merged
                WHERE name LIKE ? OR name_aliases LIKE ? OR description LIKE ? OR topics LIKE ?
                ORDER BY quality_score DESC, installs DESC
                LIMIT ?
            """, (like_pattern, like_pattern, like_pattern, like_pattern, limit)).fetchall()
        else:
            # 英文长查询 → FTS5 trigram
            rows = conn.execute("""
                SELECT m.id, m.name, m.description, m.source, m.installs,
                       m.stars, m.topics, m.urls, m.quality_score,
                       bm25(skills_fts) AS relevance
                FROM skills_fts fts
                JOIN skills_merged m ON m.id = fts.rowid
                WHERE skills_fts MATCH ?
                ORDER BY relevance
                LIMIT ?
            """, (query, limit)).fetchall()

        for row in rows:
            if row["id"] not in seen_ids:
                results.append(dict(row))
                seen_ids.add(row["id"])
    except Exception:
        pass

    # 策略2: 中文拆词补充
    if has_chinese and len(results) < limit and len(query) > 2:
        remaining = limit - len(results)
        cn_chars = re.findall(r'[一-鿿]', query)
        words = set()
        words.add(query)
        for i in range(len(cn_chars) - 1):
            words.add(cn_chars[i] + cn_chars[i + 1])
        words = list(words)

        conditions = " OR ".join(
            ["name LIKE ? OR name_aliases LIKE ? OR description LIKE ?"] * len(words)
        )
        params = []
        for w in words:
            params.extend([f"%{w}%", f"%{w}%", f"%{w}%"])
        not_in = ",".join(str(i) for i in seen_ids) if seen_ids else "0"
        params.extend([remaining])

        try:
            rows = conn.execute(f"""
                SELECT id, name, description, source, installs, stars,
                       topics, urls, quality_score, 0 AS relevance
                FROM skills_merged
                WHERE ({conditions}) AND id NOT IN ({not_in})
                ORDER BY quality_score DESC, installs DESC
                LIMIT ?
            """, params).fetchall()

            for row in rows:
                if row["id"] not in seen_ids:
                    results.append(dict(row))
                    seen_ids.add(row["id"])
        except Exception:
            pass

    conn.close()
    return results


def search_skills(query, limit=10, online=True, db_path=None):
    """
    统一搜索入口: 本地优先 + 在线兜底

    返回: {
        "query": str,
        "local_results": [...],
        "online_results": [...],
        "total": int,
        "elapsed_ms": float,
        "source": str
    }
    """
    start = time.time()

    # 1. 本地搜索
    local_results = search_local(query, limit, db_path)

    # 2. 本地结果不足 → 尝试向量语义搜索
    vector_results = []
    if len(local_results) < min(3, limit):
        try:
            vector_results = search_hybrid(query, limit=limit, db_path=db_path)
            # search_hybrid 返回 dict，提取其中的 results 列表
            if isinstance(vector_results, dict):
                vector_results = vector_results.get("results", [])
        except Exception:
            vector_results = []

    # 3. 本地未命中 → 在线搜索
    online_results = []
    if online and len(local_results) < min(3, limit) and not vector_results:
        online_results = _search_skills_sh(query, limit)
        if not online_results:
            online_results = _search_clawhub(query, limit)

    elapsed = (time.time() - start) * 1000

    if local_results and online_results:
        source = "local+online"
    elif local_results:
        source = "local"
    else:
        source = "online_only"

    return {
        "query": query,
        "local_results": local_results,
        "online_results": online_results,
        "total": len(local_results) + len(online_results),
        "elapsed_ms": round(elapsed, 1),
        "source": source,
    }


def _search_skills_sh(query, limit=10):
    """在线搜索 skills.sh"""
    url = f"{SKILLS_SH_API}?q={query}&limit={limit}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "skill-advisor/6.0",
        "Accept": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = []
        for s in data.get("skills", []):
            results.append({
                "name": s.get("name", ""),
                "description": "",
                "source": "skills_sh_online",
                "installs": s.get("installs", 0),
                "stars": 0,
                "topics": [],
                "urls": [f"https://skills.sh/skill/{s.get('id', '')}"],
                "quality_score": min(30, int((s.get("installs", 0) ** 0.5) * 0.3)),
                "online": True,
            })
        return results
    except Exception:
        return []


def _search_clawhub(query, limit=10):
    """在线搜索 ClawHub"""
    url = f"{CLAWHUB_API}?q={query}&limit={limit}&sort=downloads&dir=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "skill-advisor/6.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = []
        for item in data.get("items", []):
            stats = item.get("stats", {})
            results.append({
                "name": item.get("displayName", item.get("slug", "")),
                "description": item.get("description", item.get("summary", "")),
                "source": "clawhub_online",
                "installs": stats.get("installs", stats.get("downloads", 0)),
                "stars": stats.get("stars", 0),
                "topics": item.get("topics", []),
                "urls": [f"https://clawhub.ai/skills/{item.get('slug', '')}"],
                "quality_score": 50,
                "online": True,
            })
        return results
    except Exception:
        return []


def search_hybrid(query, limit=10, db_path=None):
    """
    混合搜索：向量召回 + FTS5 + LIKE，三路结果融合。

    三路召回策略：
      1. 向量召回（vector_search）→ 语义理解，命中模糊需求
      2. FTS5 召回（search_local 现有逻辑）→ 精确关键词匹配
      3. LIKE 兜底（search_local 中的中文逻辑）→ 防止遗漏

    融合规则：
      - 三路结果按 normalized_name 去重
      - 向量命中的结果排在前面
      - 最终按 relevance + quality_score 重排

    返回: {
        "results": [...],
        "sources": {"vector": n, "fts5+like": n},
        "elapsed_ms": float,
        "engine": "vss" | "cosine" | "fts5-only"
    }
    """
    start = time.time()

    # 1. FTS5 + LIKE 召回（现有逻辑）
    fts_results = search_local(query, limit=limit, db_path=db_path)

    # 2. 向量召回（可选，模型不可用时跳过）
    vector_results = []
    vector_engine = "unavailable"
    try:
        from .vector_search import search_vector
        vec_resp = search_vector(query, limit=limit, db_path=db_path)
        vector_results = vec_resp.get("results", [])
        vector_engine = vec_resp.get("engine", "unavailable")
    except Exception:
        pass

    # 3. 融合去重
    seen_names = set()
    merged = []

    # 向量结果优先
    for r in vector_results:
        norm = r.get("normalized_name", r.get("name", "").lower().strip())
        if norm not in seen_names:
            seen_names.add(norm)
            r["_from_vector"] = True
            merged.append(r)

    # FTS5 结果补充
    for r in fts_results:
        norm = r.get("normalized_name", r.get("name", "").lower().strip())
        if norm not in seen_names:
            seen_names.add(norm)
            r["_from_vector"] = False
            merged.append(r)

    # 4. 最终重排
    for r in merged:
        quality_norm = min(r.get("quality_score", 0) / 100.0, 1.0)
        relevance = r.get("relevance", 0.0)
        if r.get("_from_vector"):
            # 向量结果：relevance 来自余弦相似度（0~1）
            r["_final_score"] = 0.7 * relevance + 0.3 * quality_norm
        else:
            # FTS5 结果：relevance 来自 bm25（已归一化为正值）
            r["_final_score"] = 0.5 * relevance + 0.5 * quality_norm

    merged.sort(key=lambda x: x.get("_final_score", 0), reverse=True)
    merged = merged[:limit]

    # 清理临时字段
    for r in merged:
        r.pop("_from_vector", None)
        r.pop("_final_score", None)

    elapsed = (time.time() - start) * 1000

    # 确定引擎标签
    if vector_results and fts_results:
        engine = vector_engine
    elif vector_results:
        engine = vector_engine
    else:
        engine = "fts5-only"

    return {
        "results": merged,
        "sources": {
            "vector": len(vector_results),
            "fts5+like": len(fts_results),
        },
        "elapsed_ms": round(elapsed, 1),
        "engine": engine,
    }


def get_stats(db_path=None):
    """获取缓存统计"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not Path(db_path).exists():
        return {"error": "Database not found", "path": str(db_path)}

    conn = sqlite3.connect(str(db_path))
    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    with_desc = conn.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != ''"
    ).fetchone()[0]
    conn.close()

    size_mb = Path(db_path).stat().st_size / 1024 / 1024
    return {
        "total_skills": total,
        "with_description": with_desc,
        "database_size_mb": round(size_mb, 1),
        "database_path": str(db_path),
    }
