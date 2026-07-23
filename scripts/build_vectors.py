#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量索引构建器 — 对有描述的技能生成嵌入，写入 SQLite。

支持两种模式:
  1. sqlite-vss 可用 → ANN 快速检索
  2. sqlite-vss 不可用 → 降级为纯 Python 余弦相似度

用法:
  python scripts/build_vectors.py                        # 全量构建
  python scripts/build_vectors.py --incremental          # 增量（仅新技能）
  python scripts/build_vectors.py --model BAAI/bge-small-zh-v1.5  # 指定模型
  python scripts/build_vectors.py --force                # 强制重建所有嵌入
  python scripts/build_vectors.py --stats                # 查看索引统计
  python scripts/build_vectors.py --batch-size 64        # 批处理大小
"""

import argparse
import json
import os
import sqlite3
import struct
import sys
import time
from pathlib import Path

# 修复 Windows GBK 编码
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "data" / "skill-advisor.db"

# 全局模型单例（避免重复加载）
_model = None
_model_name = None


def load_model(model_name="BAAI/bge-small-zh-v1.5"):
    """加载 sentence-transformers 模型（全局单例）"""
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers 未安装。请运行: pip install -e '.[vector]'"
        )

    print(f"  📦 加载模型: {model_name} ...")
    start = time.time()
    _model = SentenceTransformer(model_name)
    _model_name = model_name
    elapsed = time.time() - start
    print(f"  ✅ 模型加载完成 ({elapsed:.1f}s)")
    return _model


def check_sqlite_vss():
    """检查 sqlite-vss 是否可用"""
    try:
        import sqlite_vec
        # 尝试加载扩展
        conn = sqlite3.connect(":memory:")
        try:
            sqlite_vec.load(conn)
            conn.close()
            return True
        except Exception:
            conn.close()
            return False
    except ImportError:
        return False


def ensure_vss_table(conn, dimensions):
    """确保 sqlite-vss 虚拟表存在"""
    if not check_sqlite_vss():
        return False

    try:
        import sqlite_vec
        sqlite_vec.load(conn)
        # 检查表是否已存在
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='skills_vss'"
        ).fetchone()
        if not existing:
            conn.execute(
                f"CREATE VIRTUAL TABLE skills_vss USING vec0(embedding float[{dimensions}])"
            )
            print(f"  ✅ 创建 skills_vss 虚拟表 (float[{dimensions}])")
        conn.commit()
        return True
    except Exception as e:
        print(f"  ⚠️ sqlite-vss 初始化失败: {e}")
        return False


def serialize_embedding(embedding):
    """将 numpy array 序列化为 BLOB（float32 小端序）"""
    return struct.pack(f"<{len(embedding)}f", *embedding.tolist())


def deserialize_embedding(blob, dimensions):
    """将 BLOB 反序列化为 list[float]"""
    size = struct.calcsize(f"<{dimensions}f")
    values = struct.unpack(f"<{dimensions}f", blob[:size])
    return list(values)


def build_all(conn=None, model_name="BAAI/bge-small-zh-v1.5", force=False, incremental=True,
              batch_size=64, db_path=None):
    """
    对所有有描述的技能构建向量嵌入。

    参数:
        conn: SQLite 连接（可选，用于被 build_cache.py 调用时复用连接）
        model_name: 嵌入模型名
        force: 强制重建所有嵌入
        incremental: 增量模式（仅处理无嵌入的技能）
        batch_size: 批处理大小
        db_path: 数据库路径（当 conn 为 None 时使用）

    返回:
        dict: {built, skipped, total, elapsed_seconds, engine}
    """
    start_time = time.time()
    close_conn = False

    if conn is None:
        if db_path is None:
            db_path = DB_PATH
        conn = sqlite3.connect(str(db_path))
        close_conn = True

    # 加载模型
    try:
        model = load_model(model_name)
    except ImportError as e:
        print(f"  ❌ {e}")
        if close_conn:
            conn.close()
        return {"built": 0, "skipped": 0, "total": 0, "elapsed_seconds": 0, "engine": "unavailable"}

    dimensions = model.get_sentence_embedding_dimension()

    # 检查 sqlite-vss
    use_vss = ensure_vss_table(conn, dimensions)
    engine = "vss" if use_vss else "cosine"
    print(f"  🔧 向量引擎: {engine}")

    # 获取需要处理的技能
    if force:
        # 强制重建：清除所有现有嵌入
        conn.execute("DELETE FROM skills_vectors")
        if use_vss:
            conn.execute("DELETE FROM skills_vss")
        conn.commit()
        rows = conn.execute(
            "SELECT id, name, description, topics FROM skills_merged WHERE description != ''"
        ).fetchall()
    elif incremental:
        # 增量：仅处理还没有嵌入的技能
        rows = conn.execute("""
            SELECT m.id, m.name, m.description, m.topics
            FROM skills_merged m
            LEFT JOIN skills_vectors v ON m.id = v.skill_id
            WHERE m.description != '' AND v.skill_id IS NULL
        """).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, description, topics FROM skills_merged WHERE description != ''"
        ).fetchall()

    total = len(rows)
    print(f"  📊 需要处理: {total} 条技能 (有描述)")

    if total == 0:
        if close_conn:
            conn.close()
        return {
            "built": 0, "skipped": 0, "total": 0,
            "elapsed_seconds": time.time() - start_time,
            "engine": engine
        }

    # 批量处理
    built = 0
    batch_texts = []
    batch_ids = []

    def flush_batch():
        """批量写入向量到数据库（每 100 条提交一次）"""
        nonlocal built, batch_texts, batch_ids
        if not batch_texts:
            return

        # 生成嵌入
        embeddings = model.encode(batch_texts, batch_size=batch_size, show_progress_bar=False)

        for i, (emb, skill_id) in enumerate(zip(embeddings, batch_ids)):
            blob = serialize_embedding(emb)
            conn.execute("""
                INSERT OR REPLACE INTO skills_vectors (skill_id, embedding, model, dimensions)
                VALUES (?, ?, ?, ?)
            """, (skill_id, blob, model_name, dimensions))

            # 如果 vss 可用，也写入虚拟表
            if use_vss:
                conn.execute(
                    "INSERT OR REPLACE INTO skills_vss(rowid, embedding) VALUES (?, ?)",
                    (skill_id, json.dumps(emb.tolist()))
                )

            built += 1

        conn.commit()
        batch_texts = []
        batch_ids = []

    for idx, (skill_id, name, desc, topics_json) in enumerate(rows):
        # 构造嵌入文本：name + description + topics
        text = name
        if desc:
            text += ". " + desc
        if topics_json:
            try:
                topics = json.loads(topics_json)
                if topics:
                    text += " (" + ", ".join(topics[:5]) + ")"
            except (json.JSONDecodeError, TypeError):
                pass

        batch_texts.append(text)
        batch_ids.append(skill_id)

        # 批量 flush
        if len(batch_texts) >= batch_size:
            flush_batch()
            elapsed = time.time() - start_time
            rate = built / elapsed if elapsed > 0 else 0
            print(f"  ... {built}/{total} ({rate:.0f} 技能/秒)")

        # 每 1000 条额外 commit 一次（防止事务过大）
        if (idx + 1) % 1000 == 0 and batch_texts:
            flush_batch()

    # 最后一批
    flush_batch()

    elapsed = time.time() - start_time
    skipped = total - built

    print(f"  ✅ 构建完成: {built} 条嵌入, {skipped} 跳过, 耗时 {elapsed:.1f}s")

    if close_conn:
        conn.close()

    return {
        "built": built,
        "skipped": skipped,
        "total": total,
        "elapsed_seconds": round(elapsed, 1),
        "engine": engine,
        "model": model_name,
        "dimensions": dimensions,
    }


def show_stats(db_path=None):
    """显示向量索引统计"""
    if db_path is None:
        db_path = DB_PATH

    if not Path(db_path).exists():
        print("❌ 数据库不存在")
        return

    conn = sqlite3.connect(str(db_path))

    # 向量数量
    vec_count = conn.execute("SELECT COUNT(*) FROM skills_vectors").fetchone()[0]
    total_with_desc = conn.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != ''"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]

    # 模型信息
    models = conn.execute(
        "SELECT model, dimensions, COUNT(*) FROM skills_vectors GROUP BY model, dimensions"
    ).fetchall()

    # 覆盖率
    coverage = (vec_count / total_with_desc * 100) if total_with_desc > 0 else 0

    # DB 文件大小
    db_size = Path(db_path).stat().st_size / 1024 / 1024 if Path(db_path).exists() else 0

    print(f"📊 向量索引统计")
    print(f"{'=' * 40}")
    print(f"  总技能数:         {total:,}")
    print(f"  有描述的技能:     {total_with_desc:,}")
    print(f"  已索引嵌入:       {vec_count:,}")
    print(f"  描述覆盖率:       {coverage:.1f}%")
    print(f"  DB 文件大小:      {db_size:.1f} MB")
    print(f"")
    print(f"  模型信息:")
    for model, dims, cnt in models:
        print(f"    {model} ({dims}维): {cnt:,} 条")

    conn.close()


def main():
    """向量索引构建器主入口 — 对有描述的技能生成嵌入向量"""
    parser = argparse.ArgumentParser(description="向量索引构建器")
    parser.add_argument("--db", default=str(DB_PATH), help="数据库路径")
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5", help="嵌入模型名")
    parser.add_argument("--force", action="store_true", help="强制重建所有嵌入")
    parser.add_argument("--incremental", action="store_true", default=True,
                        help="增量构建（默认）")
    parser.add_argument("--no-incremental", action="store_true", help="禁用增量模式")
    parser.add_argument("--batch-size", type=int, default=64, help="批处理大小（默认64）")
    parser.add_argument("--stats", action="store_true", help="显示索引统计")
    args = parser.parse_args()

    if args.stats:
        show_stats(args.db)
        return

    incremental = not args.no_incremental
    print("=" * 50)
    print("🚀 向量索引构建器")
    print("=" * 50)
    print(f"  数据库:    {args.db}")
    print(f"  模型:      {args.model}")
    print(f"  模式:      {'增量' if incremental else '全量'}")
    print(f"  批大小:    {args.batch_size}")
    print()

    result = build_all(
        model_name=args.model,
        force=args.force,
        incremental=incremental,
        batch_size=args.batch_size,
        db_path=args.db,
    )

    if result["engine"] == "unavailable":
        print("\n❌ 向量引擎不可用。安装依赖:")
        print("   pip install -e '.[vector]'")

    print(f"\n结果: {result}")


if __name__ == "__main__":
    main()
