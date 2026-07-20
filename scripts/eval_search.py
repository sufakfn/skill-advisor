#!/usr/bin/env python3
"""Phase 2.14 - Search Quality Evaluation"""

import json, re, sqlite3, time
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "skills.db"
EVAL_FILE = Path(__file__).parent.parent / "tests" / "eval_queries.json"

def search(query, limit=10):
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    has_chinese = any('一' <= c <= '鿿' for c in query)
    if has_chinese or len(query) < 3:
        like = "%" + query + "%"
        rows = conn.execute(
            "SELECT m.name, m.description, m.topics FROM skills_merged m WHERE m.name LIKE ? OR m.name_aliases LIKE ? OR m.description LIKE ? OR m.topics LIKE ? ORDER BY m.quality_score DESC LIMIT ?",
            (like, like, like, like, limit)
        ).fetchall()
    else:
        try:
            rows = conn.execute(
                "SELECT m.name, m.description, m.topics, bm25(skills_fts) AS r FROM skills_fts fts JOIN skills_merged m ON m.id = fts.rowid WHERE skills_fts MATCH ? ORDER BY r LIMIT ?",
                (query, limit)
            ).fetchall()
        except:
            like = "%" + query + "%"
            rows = conn.execute(
                "SELECT m.name, m.description, m.topics FROM skills_merged m WHERE m.name LIKE ? OR m.description LIKE ? ORDER BY m.quality_score DESC LIMIT ?",
                (like, like, limit)
            ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def evaluate():
    eval_queries = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    results = []
    for q in eval_queries:
        query = q["query"]
        expected = q.get("expected", [])
        start = time.time()
        hits = search(query, limit=10)
        elapsed = (time.time() - start) * 1000
        hit_names = [h["name"].lower() for h in hits]
        # Precision@5: top 5 results that match expected
        top5 = hit_names[:5]
        relevant = sum(1 for h in top5 if any(e.lower() in h or h in e.lower() for e in expected))
        p5 = relevant / 5 if top5 else 0
        # Recall@10: expected skills found in top 10
        found = sum(1 for e in expected if any(e.lower() in h or h in e.lower() for h in hit_names))
        r10 = found / len(expected) if expected else 0
        # MRR: reciprocal rank of first relevant result
        mrr = 0
        for i, h in enumerate(hit_names):
            if any(e.lower() in h or h in e.lower() for e in expected):
                mrr = 1.0 / (i + 1)
                break
        results.append({"query": query, "p5": p5, "r10": r10, "mrr": mrr, "elapsed_ms": round(elapsed, 1)})
    # Aggregate
    avg_p5 = sum(r["p5"] for r in results) / len(results)
    avg_r10 = sum(r["r10"] for r in results) / len(results)
    avg_mrr = sum(r["mrr"] for r in results) / len(results)
    avg_time = sum(r["elapsed_ms"] for r in results) / len(results)
    print(f"Evaluation Results ({len(eval_queries)} queries)")
    print("=" * 50)
    print(f"  Precision@5: {avg_p5:.3f}")
    print(f"  Recall@10:   {avg_r10:.3f}")
    print(f"  MRR:         {avg_mrr:.3f}")
    print(f"  Avg time:    {avg_time:.1f}ms")
    # Save detailed results
    output = {"aggregate": {"p5": avg_p5, "r10": avg_r10, "mrr": avg_mrr, "avg_ms": avg_time}, "details": results}
    Path("tests/eval_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return avg_p5, avg_r10, avg_mrr

if __name__ == "__main__":
    evaluate()
