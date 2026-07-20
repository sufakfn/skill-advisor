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


def _calc_weighted_score(relevance, stars):
    """
    计算加权排序分数

    公式: final_score = relevance_normalized * 0.7 + stars_normalized * 0.3

    relevance: FTS5 bm25 (负值，越小越好) 或 0 (LIKE 模式)
    stars: GitHub stars 数量
    """
    # 将 relevance 归一化到 0-1
    if relevance < 0:
        # FTS5 bm25: 转换为 0-1 (取绝对值后反转)
        rel_score = 1.0 / (1.0 + abs(relevance))
    else:
        # LIKE 模式或无相关性分数
        rel_score = 0.5

    # Stars 归一化到 0-1 (上限 1000)
    stars_score = min(stars or 0, 1000) / 1000.0

    return rel_score * 0.7 + stars_score * 0.3


def _rerank_with_stars(results):
    """对结果进行 stars 加权重排序"""
    for r in results:
        r["_score"] = _calc_weighted_score(
            r.get("relevance", 0),
            r.get("stars", 0)
        )
    results.sort(key=lambda x: x["_score"], reverse=True)
    return results


def search_local(query, limit=10, db_path=None):
    """
    本地 SQLite 搜索（带 stars 加权排序）

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
                WHERE verified = 1 AND (name LIKE ? OR name_aliases LIKE ? OR description LIKE ? OR topics LIKE ?)
                ORDER BY quality_score DESC, installs DESC
                LIMIT ?
            """, (like_pattern, like_pattern, like_pattern, like_pattern, limit * 3)).fetchall()
        else:
            # 英文长查询 → FTS5 trigram
            rows = conn.execute("""
                SELECT m.id, m.name, m.description, m.source, m.installs,
                       m.stars, m.topics, m.urls, m.quality_score,
                       bm25(skills_fts) AS relevance
                FROM skills_fts fts
                JOIN skills_merged m ON m.id = fts.rowid
                WHERE verified = 1 AND skills_fts MATCH ?
                ORDER BY relevance
                LIMIT ?
            """, (query, limit * 3)).fetchall()

        for row in rows:
            if row["id"] not in seen_ids:
                results.append(dict(row))
                seen_ids.add(row["id"])
    except Exception:
        pass

    # 策略2: 中文拆词补充
    if has_chinese and len(results) < limit * 3 and len(query) > 2:
        remaining = limit * 3 - len(results)
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
                WHERE verified = 1 AND ({conditions}) AND id NOT IN ({not_in})
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

    # Stars 加权重排序
    results = _rerank_with_stars(results)

    # 返回前 limit 个
    return results[:limit]


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

    # 2. 本地未命中 → 在线搜索
    online_results = []
    if online and len(local_results) < min(3, limit):
        online_results = _search_skills_sh(query, limit)
        if not online_results:
            online_results = _search_clawhub(query, limit)

    elapsed = (time.time() - start) * 1000

    # Add safety markers
    for r in local_results:
        r["safety"] = _check_safety(r.get("urls", []))
    for r in online_results:
        r["safety"] = _check_safety(r.get("urls", []))

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

def _check_safety(urls):
    """Quick safety check based on source URLs"""
    safe_domains = ["github.com", "gitlab.com", "clawhub.ai"]
    if urls:
        for u in urls:
            u_str = str(u)
            for d in safe_domains:
                if d in u_str:
                    return "safe"
    return "unverified"


# === 向量语义搜索 (Phase P0-1) ===

_vec_model = None
_vec_db_path = None

def _get_vec_model():
    """懒加载嵌入模型（只加载一次）"""
    global _vec_model
    if _vec_model is None:
        from sentence_transformers import SentenceTransformer
        _vec_model = SentenceTransformer("intfloat/multilingual-e5-small")
    return _vec_model

def _get_vec_db(db_path):
    """获取加载了 sqlite-vec 的数据库连接"""
    global _vec_db_path
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # 检查是否有向量表
    has_vec = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='skills_vec'").fetchone()
    if not has_vec:
        conn.close()
        return None
    # 加载 sqlite-vec 扩展
    conn.enable_load_extension(True)
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except Exception:
        pass
    conn.enable_load_extension(False)
    _vec_db_path = str(db_path)
    return conn

def search_semantic(query, limit=10, db_path=None):
    """
    向量语义搜索

    使用 multilingual-e5-small 模型生成查询嵌入，
    通过 sqlite-vec 进行 KNN 搜索。

    参数:
        query: 自然语言查询（中英文均可）
        limit: 返回数量
        db_path: 数据库路径

    返回: {query, local_results, total, elapsed_ms, source}
    """
    start = time.time()

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not Path(db_path).exists():
        return {"query": query, "local_results": [], "total": 0, "elapsed_ms": 0, "source": "none"}

    # 获取数据库连接
    conn = _get_vec_db(db_path)
    if conn is None:
        # 无向量表，回退到普通搜索
        return search_skills(query, limit, online=False, db_path=db_path)

    try:
        # 生成查询嵌入
        model = _get_vec_model()
        query_emb = model.encode([query])[0]

        # 向量搜索（获取更多候选用于重排序）
        rows = conn.execute("""
            SELECT m.id, m.name, m.description, m.source, m.installs,
                   m.stars, m.topics, m.urls, m.quality_score,
                   vec_distance_cosine(sv.embedding, ?) AS distance
            FROM skills_vec sv
            JOIN skills_merged m ON m.id = sv.rowid
            WHERE m.verified = 1
            ORDER BY distance
            LIMIT ?
        """, (json.dumps(query_emb.tolist()), limit * 3)).fetchall()

        results = [dict(r) for r in rows]
    except Exception:
        results = []
    finally:
        conn.close()

    # Stars 加权重排序（向量距离转为 relevance）
    for r in results:
        distance = r.get("distance", 2.0)
        r["relevance"] = 1.0 - (distance / 2.0)  # 转换为 0-1

    results = _rerank_with_stars(results)

    elapsed = (time.time() - start) * 1000

    return {
        "query": query,
        "local_results": results[:limit],
        "online_results": [],
        "total": len(results[:limit]),
        "elapsed_ms": round(elapsed, 1),
        "source": "vector",
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
