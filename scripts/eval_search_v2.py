#!/usr/bin/env python3
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from search_weighted import search_weighted

EVAL_FILE = Path(__file__).parent.parent / "tests" / "eval_queries.json"

def evaluate():
    eval_queries = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    results = []
    for q in eval_queries:
        query = q["query"]
        expected = q.get("expected", [])
        start = time.time()
        hits = search_weighted(query, limit=10)
        elapsed = (time.time() - start) * 1000
        hit_names = [h["name"].lower() for h in hits]
        top5 = hit_names[:5]
        relevant = sum(1 for h in top5 if any(e.lower() in h or h in e.lower() for e in expected))
        p5 = relevant / 5 if top5 else 0
        found = sum(1 for e in expected if any(e.lower() in h or h in e.lower() for h in hit_names))
        r10 = found / len(expected) if expected else 0
        mrr = 0
        for i, h in enumerate(hit_names):
            if any(e.lower() in h or h in e.lower() for e in expected):
                mrr = 1.0 / (i + 1)
                break
        results.append({"query": query, "p5": p5, "r10": r10, "mrr": mrr, "elapsed_ms": round(elapsed, 1)})
    avg_p5 = sum(r["p5"] for r in results) / len(results)
    avg_r10 = sum(r["r10"] for r in results) / len(results)
    avg_mrr = sum(r["mrr"] for r in results) / len(results)
    avg_time = sum(r["elapsed_ms"] for r in results) / len(results)
    print("Evaluation (weighted search, {} queries)".format(len(eval_queries)))
    print("=" * 50)
    print("  Precision@5: {:.3f}".format(avg_p5))
    print("  Recall@10:   {:.3f}".format(avg_r10))
    print("  MRR:         {:.3f}".format(avg_mrr))
    print("  Avg time:    {:.1f}ms".format(avg_time))
    categories = {}
    for q, r in zip(eval_queries, results):
        cat = q.get("category", "unknown")
        categories.setdefault(cat, []).append(r["p5"])
    print("  Per-category Precision@5:")
    for cat, scores in sorted(categories.items()):
        print("    {}: {:.3f}".format(cat, sum(scores)/len(scores)))

if __name__ == "__main__":
    evaluate()
