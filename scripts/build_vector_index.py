#!/usr/bin/env python3
"""构建向量索引 - 只为有真实描述的技能生成嵌入向量"""

import json
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"


def init_vector_table(db):
    db.enable_load_extension(True)
    try:
        import sqlite_vec
        sqlite_vec.load(db)
    except Exception as e:
        print(f"Error loading sqlite-vec: {e}")
        print("Install with: pip install sqlite-vec")
        sys.exit(1)
    db.enable_load_extension(False)
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS skills_vec USING vec0(embedding float[384])")
    db.commit()


def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("intfloat/multilingual-e5-small")


def build_index(db_path=DB_PATH, incremental=False):
    conn = sqlite3.connect(str(db_path))
    init_vector_table(conn)
    model = get_model()

    # 只为 verified = 1 的技能构建索引
    if incremental:
        existing = conn.execute("SELECT rowid FROM skills_vec").fetchall()
        existing_ids = {r[0] for r in existing}
        rows = conn.execute(
            "SELECT id, name, description, topics FROM skills_merged WHERE verified = 1"
        ).fetchall()
        rows = [r for r in rows if r[0] not in existing_ids]
    else:
        conn.execute("DELETE FROM skills_vec")
        conn.commit()
        rows = conn.execute(
            "SELECT id, name, description, topics FROM skills_merged WHERE verified = 1"
        ).fetchall()

    print(f"Indexing {len(rows)} verified skills...")

    batch_size = 100
    start = time.time()

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        ids = [r[0] for r in batch]
        texts = []
        for r in batch:
            text = r[1] + ". " + (r[2] or "")
            if r[3]:
                try:
                    topics = json.loads(r[3]) if isinstance(r[3], str) else r[3]
                    if topics:
                        text += " (" + ", ".join(topics[:5]) + ")"
                except:
                    pass
            texts.append(text)

        embeddings = model.encode(texts, show_progress_bar=False)
        for j, emb in enumerate(embeddings):
            conn.execute(
                "INSERT INTO skills_vec(rowid, embedding) VALUES (?, ?)",
                (ids[j], json.dumps(emb.tolist()))
            )
        conn.commit()
        print(f"  Batch {i//batch_size + 1}/{(len(rows)-1)//batch_size + 1} done")

    elapsed = time.time() - start
    total = conn.execute("SELECT COUNT(*) FROM skills_vec").fetchone()[0]
    print(f"Done. {total} vectors in {elapsed:.1f}s")
    conn.close()


if __name__ == "__main__":
    if "--stats" in sys.argv:
        conn = sqlite3.connect(str(DB_PATH))
        total = conn.execute("SELECT COUNT(*) FROM skills_vec").fetchone()[0]
        print(f"Vector index: {total} entries")
        conn.close()
    elif "--incremental" in sys.argv:
        build_index(incremental=True)
    else:
        build_index()
