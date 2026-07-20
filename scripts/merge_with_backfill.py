#!/usr/bin/env python3
"""Phase 2.11 - Smart Merge Pipeline

Runs merge_all_sources then backfills descriptions.
This preserves the dedup logic while ensuring maximum description coverage.

Usage:
  python scripts/merge_with_backfill.py          # full pipeline
  python scripts/merge_with_backfill.py --stats  # show coverage stats
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    if args.stats:
        show_stats(conn)
        return
    
    print("=" * 60)
    print("Smart Merge Pipeline: merge + backfill")
    print("=" * 60)
    
    # Step 1: Run original merge
    sys.path.insert(0, str(Path(__file__).parent))
    from build_cache import init_database, merge_all_sources, rebuild_fts
    
    print("
[Step 1] Running original merge...")
    # Re-initialize DB (merge clears skills_merged)
    conn.close()
    conn = init_database(DB_PATH)
    count = merge_all_sources(conn)
    print(f"  Merged: {count} unique skills")
    
    # Step 2: Backfill descriptions
    print("
[Step 2] Backfilling descriptions...")
    from backfill_descriptions import backfill as local_backfill, rebuild_fts as rebuild_fts_idx
    stats = local_backfill(DB_PATH, execute=True)
    print(f"  Local backfill: {stats}")
    
    # Step 3: Rebuild FTS5
    print("
[Step 3] Rebuilding FTS5...")
    rebuild_fts_idx(DB_PATH)
    print("  Done.")
    
    # Final stats
    show_stats(conn)

def show_stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    with_desc = conn.execute("SELECT COUNT(*) FROM skills_merged WHERE description != '' AND description IS NOT NULL").fetchone()[0]
    print(f"
Coverage: {with_desc}/{total} ({with_desc*100/total:.1f}%)")
    sources = conn.execute("SELECT source, COUNT(*) FROM skills_merged GROUP BY source ORDER BY COUNT(*) DESC LIMIT 5").fetchall()
    for s, c in sources:
        print(f"  {s:30s}: {c}")

if __name__ == "__main__":
    main()
