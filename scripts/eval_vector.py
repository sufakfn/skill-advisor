#!/usr/bin/env python3
"""评估向量搜索质量"""

import json
import sys
import time
sys.path.insert(0, str(__file__).rsplit('/', 1)[0])
sys.path.insert(0, str(__file__).rsplit('/', 1)[0] + '/..')

from skill_advisor.search import search_semantic

EVAL_FILE = 'tests/eval_queries.json'

def evaluate():
    with open(EVAL_FILE, encoding='utf-8') as f:
        eval_queries = json.load(f)
    
    results = []
    for q in eval_queries:
        query = q['query']
        expected = q.get('expected', [])
        
        start = time.time()
        hits = search_semantic(query, limit=10)
        elapsed = (time.time() - start) * 1000
        
        hit_names = [h['name'].lower() for h in hits['local_results']]
        
        # Precision@5
        top5 = hit_names[:5]
        relevant = sum(1 for h in top5 if any(e.lower() in h or h in e.lower() for e in expected))
        p5 = relevant / 5 if top5 else 0
        
        # Recall@10
        found = sum(1 for e in expected if any(e.lower() in h or h in e.lower() for h in hit_names))
        r10 = found / len(expected) if expected else 0
        
        # MRR
        mrr = 0
        for i, h in enumerate(hit_names):
            if any(e.lower() in h or h in e.lower() for e in expected):
                mrr = 1.0 / (i + 1)
                break
        
        results.append({'query': query, 'p5': p5, 'r10': r10, 'mrr': mrr, 'elapsed_ms': round(elapsed, 1)})
    
    avg_p5 = sum(r['p5'] for r in results) / len(results)
    avg_r10 = sum(r['r10'] for r in results) / len(results)
    avg_mrr = sum(r['mrr'] for r in results) / len(results)
    avg_time = sum(r['elapsed_ms'] for r in results) / len(results)
    
    print(f'Vector Search Evaluation ({len(eval_queries)} queries)')
    print('=' * 50)
    print(f'  Precision@5: {avg_p5:.3f}')
    print(f'  Recall@10:   {avg_r10:.3f}')
    print(f'  MRR:         {avg_mrr:.3f}')
    print(f'  Avg time:    {avg_time:.1f}ms')
    
    # 保存结果
    output = {'aggregate': {'p5': avg_p5, 'r10': avg_r10, 'mrr': avg_mrr, 'avg_ms': avg_time}, 'details': results}
    with open('tests/eval_vector_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, ensure_ascii=False, indent=2, fp=f)

if __name__ == '__main__':
    evaluate()
