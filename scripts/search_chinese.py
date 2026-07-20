#!/usr/bin/env python3
"""Phase 2.16 - Chinese Search Enhancement with jieba"""

import sqlite3, re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

def has_chinese(text):
    return any('一' <= c <= '鿿' for c in text)

def tokenize_chinese(text):
    """Tokenize Chinese text using jieba + bigram fallback"""
    try:
        import jieba
        words = list(jieba.cut(text))
    except ImportError:
        # Fallback: character bigrams
        words = []
        for i in range(len(text) - 1):
            words.append(text[i] + text[i + 1])
    # Also add bigrams for short queries
    if len(text) >= 2:
        for i in range(len(text) - 1):
            bigram = text[i] + text[i + 1]
            if bigram not in words:
                words.append(bigram)
    return words

def search_chinese_enhanced(query, limit=10):
    """Enhanced Chinese search with jieba tokenization"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    tokens = tokenize_chinese(query)
    if not tokens:
        conn.close()
        return []
    
    # Build dynamic WHERE clause for each token
    conditions = []
    params = []
    for token in tokens:
        conditions.append("(name LIKE ? OR name_aliases LIKE ? OR description LIKE ? OR topics LIKE ?)")
        like = "%" + token + "%"
        params.extend([like, like, like, like])
    
    where_clause = " OR ".join(conditions)
    
    # Score: count how many tokens match
    score_parts = []
    for token in tokens:
        score_parts.append("(CASE WHEN name LIKE ? THEN 30 WHEN description LIKE ? THEN 20 WHEN topics LIKE ? THEN 10 ELSE 0 END)")
        like = "%" + token + "%"
        params.extend([like, like, like])
    
    score_expr = " + ".join(score_parts)
    params.extend([limit])
    
    sql = "SELECT name, description, quality_score, (" + score_expr + ") AS score FROM skills_merged WHERE " + where_clause + " ORDER BY score DESC, quality_score DESC LIMIT ?"
    
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        # Fallback to simple LIKE
        like = "%" + query + "%"
        rows = conn.execute("SELECT name, description, quality_score, quality_score AS score FROM skills_merged WHERE name LIKE ? OR description LIKE ? ORDER BY score DESC LIMIT ?", (like, like, limit)).fetchall()
    
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "前端开发"
    results = search_chinese_enhanced(q)
    for r in results[:5]:
        d = (r["description"] or "")[:40]
        print("  " + r["name"][:20] + " score=" + str(r["score"]) + "  desc=" + d)
