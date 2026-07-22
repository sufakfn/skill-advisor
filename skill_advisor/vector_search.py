"""
向量语义搜索 — ANN 召回 + quality_score 重排。

支持三种引擎模式:
  1. "vss"      — sqlite-vss 扩展可用，ANN 快速检索（最快）
  2. "cosine"   — 纯 Python 余弦相似度（慢但无需额外扩展）
  3. "unavailable" — sentence-transformers 未安装，不可用

降级策略:
  - 模型未安装 → 返回空结果，由 search_hybrid() 回退 FTS5
  - 向量表不存在 → 返回空结果，由 search_hybrid() 回退 FTS5
  - sqlite-vss 不可用 → 降级到纯 Python 余弦计算

用法:
  from skill_advisor.vector_search import search_vector, get_engine_status

  # 搜索
  result = search_vector("make a presentation", limit=10)
  # result = {
  #   "results": [...],
  #   "engine": "vss" | "cosine" | "unavailable",
  #   "elapsed_ms": float,
  #   "model": "BAAI/bge-small-zh-v1.5"
  # }

  # 检查引擎状态
  status = get_engine_status()
  # status = {"engine": "vss", "model": "BAAI/bge-small-zh-v1.5", "dimensions": 384, "count": 5000}
"""

import json
import sqlite3
import struct
import time
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = PACKAGE_DIR / "data" / "skill-advisor.db"

# 全局模型单例（避免重复加载）
_model = None
_model_name = None
_dimensions = None


def _load_model(model_name="BAAI/bge-small-zh-v1.5"):
    """懒加载 sentence-transformers 模型（全局单例）"""
    global _model, _model_name, _dimensions
    if _model is not None and _model_name == model_name:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None

    _model = SentenceTransformer(model_name)
    _model_name = model_name
    _dimensions = _model.get_embedding_dimension()
    return _model


def _check_sqlite_vss(conn):
    """检查 sqlite-vss 是否可用"""
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        return True
    except Exception:
        return False


def _deserialize_embedding(blob, dimensions):
    """将 BLOB 反序列化为 list[float]"""
    size = struct.calcsize(f"<{dimensions}f")
    return list(struct.unpack(f"<{dimensions}f", blob[:size]))


def get_engine_status(model_name="BAAI/bge-small-zh-v1.5", db_path=None):
    """
    检查向量搜索当前可用状态。

    返回:
      {
        "engine": "vss" | "cosine" | "unavailable",
        "model": str | None,
        "dimensions": int | None,
        "count": int,         # 已索引的向量数
        "total_skills": int,  # 总技能数（有描述的）
      }
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    if not Path(db_path).exists():
        return {"engine": "unavailable", "model": None, "dimensions": None, "count": 0, "total_skills": 0}

    # 检查模型
    model = _load_model(model_name)
    if model is None:
        return {"engine": "unavailable", "model": None, "dimensions": None, "count": 0, "total_skills": 0}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 检查向量数量
    vec_count = conn.execute("SELECT COUNT(*) FROM skills_vectors").fetchone()[0]
    total_with_desc = conn.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != ''"
    ).fetchone()[0]

    # 检查 sqlite-vss 是否可用
    use_vss = _check_sqlite_vss(conn)

    conn.close()

    return {
        "engine": "vss" if use_vss else "cosine",
        "model": model_name,
        "dimensions": model.get_embedding_dimension(),
        "count": vec_count,
        "total_skills": total_with_desc,
    }


def _cosine_similarity(a, b):
    """计算两个向量的余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def search_vector(query, limit=10, model_name="BAAI/bge-small-zh-v1.5", db_path=None):
    """
    向量语义搜索。

    参数:
        query: 搜索词/短语（中英文均可，但模型对英文效果更好）
        limit: 返回结果数量
        model_name: 嵌入模型名
        db_path: 数据库路径

    返回:
      {
        "results": [{name, description, source, installs, stars, topics, urls, quality_score, relevance}, ...],
        "engine": "vss" | "cosine" | "unavailable",
        "elapsed_ms": float,
        "model": str | None,
      }
    """
    start = time.time()

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # 检查数据库是否存在
    if not Path(db_path).exists():
        elapsed = (time.time() - start) * 1000
        return {"results": [], "engine": "unavailable", "elapsed_ms": round(elapsed, 1), "model": None}

    # 检查模型
    model = _load_model(model_name)
    if model is None:
        elapsed = (time.time() - start) * 1000
        return {"results": [], "engine": "unavailable", "elapsed_ms": round(elapsed, 1), "model": None}

    dimensions = model.get_embedding_dimension()

    # 生成查询嵌入
    query_emb = model.encode([query])[0].tolist()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 检查向量表是否有数据
    vec_count = conn.execute("SELECT COUNT(*) FROM skills_vectors").fetchone()[0]
    if vec_count == 0:
        conn.close()
        elapsed = (time.time() - start) * 1000
        return {"results": [], "engine": "unavailable", "elapsed_ms": round(elapsed, 1), "model": model_name}

    results = []

    # 尝试用 sqlite-vss 做 ANN 查询
    use_vss = _check_sqlite_vss(conn)
    if use_vss:
        try:
            rows = conn.execute("""
                SELECT m.*, 1.0 - vec_distance_cosine(sv.embedding, ?) AS relevance
                FROM skills_vec sv
                JOIN skills_merged m ON m.id = sv.rowid
                ORDER BY vec_distance_cosine(sv.embedding, ?) ASC
                LIMIT ?
            """, (json.dumps(query_emb), json.dumps(query_emb), limit * 3)).fetchall()

            for row in rows:
                r = dict(row)
                r["relevance"] = r.get("relevance", 0.0)
                results.append(r)
        except Exception:
            # vss 查询失败，降级到 cosine
            use_vss = False

    if not use_vss:
        # 纯 Python 余弦相似度（慢但可靠）
        rows = conn.execute("""
            SELECT m.*, v.embedding
            FROM skills_vectors v
            JOIN skills_merged m ON m.id = v.skill_id
        """).fetchall()

        scored = []
        for row in rows:
            r = dict(row)
            emb_blob = r.pop("embedding")
            emb = _deserialize_embedding(emb_blob, dimensions)
            r["relevance"] = _cosine_similarity(query_emb, emb)
            scored.append(r)

        # 按相似度排序
        scored.sort(key=lambda x: x["relevance"], reverse=True)
        results = scored[:limit * 3]

    conn.close()

    # 重排：0.7 * vector_relevance + 0.3 * quality_normalized
    for r in results:
        quality_norm = min(r.get("quality_score", 0) / 100.0, 1.0)
        installs_norm = min(r.get("installs", 0) / 10000.0, 1.0)
        r["relevance"] = 0.7 * r.get("relevance", 0.0) + 0.2 * quality_norm + 0.1 * installs_norm

    results.sort(key=lambda x: x["relevance"], reverse=True)
    results = results[:limit]

    elapsed = (time.time() - start) * 1000

    return {
        "results": results,
        "engine": "vss" if use_vss else "cosine",
        "elapsed_ms": round(elapsed, 1),
        "model": model_name,
    }
