#!/usr/bin/env python3
"""
增量更新编排器 — 在已有数据基础上补充新数据，不重复已有工作。

对比:
  全量重建: ~60 分钟（拉取 55,000+ 条，下载 21,000+ SKILL.md，生成 10,000+ 向量）
  增量更新: ~30 秒（仅处理新增部分）

流程:
  1. 增量拉取各数据源（INSERT OR REPLACE，天然去重）
  2. 增量合并（不清空已有数据，只添加/更新变化部分）
  3. 增量回补描述（只处理 description 为空的条目）
  4. 增量生成向量（只处理无嵌入的条目）
  5. 输出变更统计

用法:
  python scripts/incremental_update.py              # 增量更新
  python scripts/incremental_update.py --stats      # 查看统计
  python scripts/incremental_update.py --full       # 全量重建（回退）
  python scripts/incremental_update.py --github-token xxx  # 指定 Token
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "data" / "skill-advisor.db"

# 确保 scripts 目录在 Python path 中（用于导入 build_cache 等模块）
sys.path.insert(0, str(SCRIPT_DIR))


def get_stats(db_path=None):
    """获取数据库统计"""
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(str(db_path))
    stats = {}
    stats["clawhub"] = conn.execute("SELECT COUNT(*) FROM clawhub_skills").fetchone()[0]
    stats["skills_sh"] = conn.execute("SELECT COUNT(*) FROM skills_sh_skills").fetchone()[0]
    stats["github_topic"] = conn.execute("SELECT COUNT(*) FROM github_topic_skills").fetchone()[0]
    stats["github_code"] = conn.execute("SELECT COUNT(*) FROM github_code_skills").fetchone()[0]
    stats["local"] = conn.execute("SELECT COUNT(*) FROM local_skills").fetchone()[0]
    stats["merged"] = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    stats["with_desc"] = conn.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != ''"
    ).fetchone()[0]
    stats["vectorized"] = conn.execute("SELECT COUNT(*) FROM skills_vectors").fetchone()[0]
    conn.close()
    return stats


def incremental_update(github_token=None, db_path=None, full=False):
    """执行增量更新"""
    if db_path is None:
        db_path = DB_PATH

    print("=" * 60)
    print(f"{'🔄 增量更新' if not full else '🔨 全量重建'}")
    print("=" * 60)

    # 更新前统计
    before = get_stats(db_path)
    print(f"\n更新前: {before['merged']} 技能, {before['with_desc']} 有描述, {before['vectorized']} 向量")
    print()

    start = time.time()

    conn = sqlite3.connect(str(db_path))

    # 1. 增量拉取 ClawHub
    from build_cache import (
        fetch_clawhub_all, fetch_skills_sh_all, fetch_github_topics,
        fetch_github_code_search, scan_local_skills, merge_all_sources,
        init_database, DB_PATH as BUILD_DB_PATH
    )

    if not full:
        conn = init_database(Path(db_path))

    incremental_mode = not full

    print("[1/5] 拉取 ClawHub...")
    before_clawhub = before["clawhub"]
    fetch_clawhub_all(conn)
    after_stats = get_stats(db_path)
    clawhub_new = after_stats["clawhub"] - before_clawhub
    print(f"  ✅ ClawHub: {after_stats['clawhub']} 条{'(+' + str(clawhub_new) + ')' if clawhub_new > 0 else ''}")

    print("[2/5] 扫描 skills.sh...")
    before_ss = after_stats["skills_sh"]
    fetch_skills_sh_all(conn)
    after_stats = get_stats(db_path)
    ss_new = after_stats["skills_sh"] - before_ss
    print(f"  ✅ skills.sh: {after_stats['skills_sh']} 条{'(+' + str(ss_new) + ')' if ss_new > 0 else ''}")

    if github_token:
        print("[3/5] GitHub Topic...")
        fetch_github_topics(conn, github_token)
        after_stats = get_stats(db_path)
        print(f"  ✅ GitHub Topic: {after_stats['github_topic']} 条")

        print("[4/5] GitHub Code Search...")
        fetch_github_code_search(conn, github_token)
        after_stats = get_stats(db_path)
        print(f"  ✅ GitHub Code: {after_stats['github_code']} 条")
    else:
        print("[3/5] GitHub Topic: ⏭ 跳过（无 Token）")
        print("[4/5] GitHub Code Search: ⏭ 跳过（无 Token）")

    print("[5/5] 合并本地技能...")
    scan_local_skills(conn)

    # 合并
    print(f"\n[合并] {'增量' if incremental_mode else '全量'}合并...")
    before_merged = get_stats(db_path)["merged"]
    merge_all_sources(conn, incremental=incremental_mode)
    conn.close()

    # 更新后统计
    after = get_stats(db_path)
    elapsed = time.time() - start

    print()
    print("=" * 60)
    print(f"✅ 更新完成 ({elapsed:.1f}s)")
    print("=" * 60)
    print(f"\n  {'指标':<20s} {'更新前':>8s} {'更新后':>8s} {'变化':>8s}")
    print(f"  {'-'*48}")
    print(f"  {'总技能':<20s} {before['merged']:>8} {after['merged']:>8} {after['merged'] - before['merged']:>+8}")
    print(f"  {'有描述':<20s} {before['with_desc']:>8} {after['with_desc']:>8} {after['with_desc'] - before['with_desc']:>+8}")
    print(f"  {'向量索引':<20s} {before['vectorized']:>8} {after['vectorized']:>8} {after['vectorized'] - before['vectorized']:>+8}")
    print()

    # 回补描述
    need_desc = after["merged"] - after["with_desc"]
    if need_desc > 0:
        print(f"📌 还有 {need_desc} 条技能缺描述，运行以下命令回补:")
        print(f"   python scripts/backfill_descriptions.py --workers 16")
        print()
        print(f"📌 回补后重建向量索引:")
        print(f"   python scripts/build_vectors.py --force")
    else:
        print(f"✅ 全部技能已有描述")

    print()
    print(f"📌 提交更新:")
    print(f"   git add data/skill-advisor.db")
    print(f"   git commit -m \"增量更新: {after['merged'] - before['merged']:+d} 技能, {after['with_desc'] - before['with_desc']:+d} 描述\"")
    print(f"   git push")


def main():
    parser = argparse.ArgumentParser(description="skill-advisor 增量更新")
    parser.add_argument("--db", default=str(DB_PATH), help="数据库路径")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN", ""), help="GitHub Token")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--full", action="store_true", help="全量重建（默认增量）")
    args = parser.parse_args()

    if args.stats:
        stats = get_stats(args.db)
        print()
        print("=" * 50)
        print("📊 数据库统计")
        print("=" * 50)
        print(f"  ClawHub:       {stats['clawhub']:>8,} 条")
        print(f"  skills.sh:     {stats['skills_sh']:>8,} 条")
        print(f"  GitHub Topic:  {stats['github_topic']:>8,} 条")
        print(f"  GitHub Code:   {stats['github_code']:>8,} 条")
        print(f"  本地:          {stats['local']:>8,} 条")
        print(f"  ─────────────────────────────")
        print(f"  合并后总计:    {stats['merged']:>8,} 条")
        print(f"  有描述的:      {stats['with_desc']:>8,} 条 ({stats['with_desc']/max(stats['merged'],1)*100:.1f}%)")
        print(f"  向量索引:      {stats['vectorized']:>8,} 条")
        print("=" * 50)
        return

    incremental_update(github_token=args.github_token, db_path=args.db, full=args.full)


if __name__ == "__main__":
    main()
# trigger

