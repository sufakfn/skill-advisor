#!/usr/bin/env python3
"""Phase 2.15 - Enhanced Search with Weighted Relevance"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

def search_weighted(query, limit=10):
    """Multi-field weighted relevance search.
    
    Scoring:
    - name exact match: +100
    - name partial match: +50
    - alias match: +40
    - description match: +30
    - topics match: +20
    - quality_score * 0.3
    - log10(installs) * 5
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    has_chinese = any('一' <= c <= '鿿' for c in query)
    like = "%" + query + "%"
    
    if has_chinese or len(query) < 3:
        rows = conn.execute(
            """SELECT name, description, quality_score, installs,
                ((CASE WHEN LOWER(name) = LOWER(?) THEN 100 ELSE 0 END) +
                 (CASE WHEN name LIKE ? THEN 50 ELSE 0 END) +
                 (CASE WHEN name_aliases LIKE ? THEN 40 ELSE 0 END) +
                 (CASE WHEN description LIKE ? THEN 30 ELSE 0 END) +
                 (CASE WHEN topics LIKE ? THEN 20 ELSE 0 END) +
                 quality_score * 0.3) AS score
            FROM skills_merged
            WHERE name LIKE ? OR name_aliases LIKE ? OR description LIKE ? OR topics LIKE ?
            ORDER BY score DESC LIMIT ?""",
            (query, like, like, like, like, like, like, like, like, limit)
        ).fetchall()
    else:
        try:
            rows = conn.execute(
                """SELECT m.name, m.description, m.quality_score, m.installs,
                    ((CASE WHEN LOWER(m.name) = LOWER(?) THEN 100 ELSE 0 END) +
                     (bm25(skills_fts) * -10) +
                     (m.quality_score * 0.3) +
                     (COALESCE(LOG(CASE WHEN installs > 0 installs ELSE 1 END), 0) * 3)) AS score
                FROM skills_fts fts
                JOIN skills_merged m ON m.id = fts.rowid
                WHERE skills_fts MATCH ?
                ORDER BY score DESC LIMIT ?""",
                (query, query, limit)
            ).fetchall()
        except:
            rows = conn.execute(
                """SELECT name, description, quality_score, installs, quality_score AS score
                FROM skills_merged WHERE name LIKE ? OR description LIKE ?
                ORDER BY score DESC LIMIT ?""",
                (like, like, limit)
            ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "react"
    results = search_weighted(q)
    for r in results[:5]:
        print(f"  {r["name"]:25s} score={r["score"]:.0f}  desc={str(r["description"])[:40]}")
