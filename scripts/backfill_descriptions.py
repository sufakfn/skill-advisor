#!/usr/bin/env python3
"""Phase 2 - Description Backfill (Local + Network)"""

import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

# ============================================================
# PART 1: Local table backfill (already working)
# ============================================================

def extract_fm_description(content):
    """Extract YAML frontmatter description from SKILL.md content.""" 
    if not content:
        return ""
    fm_match = re.match(r'^---\s*
(.*?)
---', content, re.DOTALL)
    if not fm_match:
        return ""
    fm = fm_match.group(1)
    desc_match = re.search(r'^description:\s*["']?(.+?)["']?\s*$', fm, re.MULTILINE)
    if desc_match:
        desc = desc_match.group(1).strip().strip('"').strip("'")
        return desc[:300]
    return ""

def extract_first_para(content):
    """Fallback: first non-empty, non-heading paragraph.""" 
    if not content:
        return ""
    lines_content = content.strip().split('
')
    para = []
    for line in lines_content:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('---'):
            continue
        if line.startswith('>'):
            continue
        para.append(line)
        if len(para) >= 2:
            break
    return ' '.join(para)[:300]

def backfill_local(db_path, execute=False):
    """Backfill descriptions from local raw tables.""" 
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    stats = {"github_code": 0, "github_topic": 0, "clawhub": 0, "skipped": 0}

    # github_code_skills
    gc_rows = conn.execute("""
        SELECT name, skill_md_content FROM github_code_skills
        WHERE skill_md_content IS NOT NULL AND skill_md_content != ''
    """).fetchall()
    for row in gc_rows:
        desc = extract_fm_description(row['skill_md_content'])
        if not desc:
            desc = extract_first_para(row['skill_md_content'])
        if not desc:
            stats["skipped"] += 1
            continue
        merged = conn.execute("""
            SELECT id FROM skills_merged
            WHERE normalized_name LIKE ? AND source LIKE '%github_code%'
            AND (description = '' OR description IS NULL)
            LIMIT 1
        """, (row['name'].lower().replace(' ', '-'),)).fetchone()
        if merged:
            if execute:
                conn.execute("UPDATE skills_merged SET description = ? WHERE id = ?", (desc, merged['id']))
            stats["github_code"] += 1

    # github_topic_skills
    gt_rows = conn.execute("""
        SELECT name, description FROM github_topic_skills
        WHERE description IS NOT NULL AND description != ''
    """).fetchall()
    for row in gt_rows:
        desc = row['description'][:300]
        merged = conn.execute("""
            SELECT id FROM skills_merged
            WHERE normalized_name LIKE ? AND source LIKE '%github_topic%'
            AND (description = '' OR description IS NULL)
            LIMIT 1
        """, (row['name'].lower().replace(' ', '-'),)).fetchone()
        if merged:
            if execute:
                conn.execute("UPDATE skills_merged SET description = ? WHERE id = ?", (desc, merged['id']))
            stats["github_topic"] += 1

    # clawhub_skills
    ch_rows = conn.execute("SELECT slug, summary, description FROM clawhub_skills"").fetchall()
    for row in ch_rows:
        desc = row['description'] or row['summary'] or ""
        if not desc:
            stats["skipped"] += 1
            continue
        desc = desc[:300]
        merged = conn.execute("""
            SELECT id FROM skills_merged
            WHERE normalized_name LIKE ? AND source LIKE '%clawhub%'
            AND (description = '' OR description IS NULL)
            LIMIT 1
        """, (row['slug'],)).fetchone()
        if merged:
            if execute:
                conn.execute("UPDATE skills_merged SET description = ? WHERE id = ?", (desc, merged['id']))
            stats["clawhub"] += 1

    if execute:
        conn.commit()
    conn.close()
    return stats

def rebuild_fts(db_path):
    """Rebuild FTS5 index.""" 
    conn = sqlite3.connect(str(db_path))
    conn.execute("INSERT INTO skills_fts(skills_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

def get_stats(db_path):
    conn = sqlite3.connect(str(db_path))
    total = conn.execute('SELECT COUNT(*) FROM skills_merged').fetchone()[0]
    with_desc = conn.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != '' AND description IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    return total, with_desc

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--rebuild-fts", action="store_true")
    args = parser.parse_args()

    dry_run = args.dry_run or not args.execute
    mode = "[DRY RUN]" if dry_run else "[EXECUTE]"
    print(f"Phase 2 - Local Backfill {mode}")
    print("=" * 50)

    total_before, desc_before = get_stats(DB_PATH)
    print(f"Before: {desc_before}/{total_before} ({desc_before*100/total_before:.1f}%)")

    stats = backfill_local(DB_PATH, execute=args.execute)
    print(f"github_code: +{stats['github_code']}, github_topic: +{stats['github_topic']}, clawhub: +{stats['clawhub']}")

    total_after, desc_after = get_stats(DB_PATH)
    print(f"After: {desc_after}/{total_after} ({desc_after*100/total_after:.1f}%)")

    if args.rebuild_fts or args.execute:
        rebuild_fts(DB_PATH)
        print("FTS5 rebuilt.")
