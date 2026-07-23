#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Description Backfiller — 从 GitHub raw URL 补全 skills.sh 条目的 SKILL.md 描述。

skills.sh 数据的 source 字段包含 owner/repo，可用于构造 raw URL：
  https://raw.githubusercontent.com/{owner}/{repo}/HEAD/skills/{skill-name}/SKILL.md

流程:
  1. 从 skills_sh_skills 表读取有 source 的条目
  2. 尝试下载 SKILL.md（多种路径格式）
  3. 解析 frontmatter 提取 description
  4. 写回 skills_merged 表的 description 字段

用法:
  python scripts/backfill_descriptions.py                  # 全量补全
  python scripts/backfill_descriptions.py --limit 100      # 只处理前 100 条
  python scripts/backfill_descriptions.py --stats          # 查看统计
  python scripts/backfill_descriptions.py --workers 8      # 并发下载数
  python scripts/backfill_descriptions.py --dry-run        # 不写数据库
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# SKILL.md 可能存在的位置（按优先级）
SKILL_MD_PATHS = [
    # 标准路径
    "skills/{skill_name}/SKILL.md",
    "{skill_name}/SKILL.md",
    "SKILL.md",
    # 常见变体
    "skills/{skill_name}/skill.md",
    "{skill_name}/skill.md",
    "skill.md",
    # 带前缀
    "skills/{skill_name}/README.md",
    "{skill_name}/README.md",
    "README.md",
    # 文档目录
    "docs/{skill_name}/SKILL.md",
    "docs/SKILL.md",
    # 源码目录
    "src/{skill_name}/SKILL.md",
    "src/skills/{skill_name}/SKILL.md",
    # 其他可能
    "{skill_name}/docs/SKILL.md",
    "skills/{skill_name}/index.md",
    "{skill_name}/index.md",
]


def parse_frontmatter(content: str) -> tuple:
    """从 SKILL.md 内容解析 frontmatter (name, description)"""
    name = ""
    desc = ""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            for line in content[3:end].split("\n"):
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if len(desc) > 500:
                        desc = desc[:500]
    return name, desc


# SSRF 防护 - 允许的域名白名单
ALLOWED_DOWNLOAD_DOMAINS = {
    "raw.githubusercontent.com",
    "github.com",
}


def _is_safe_url(url: str) -> bool:
    """检查 URL 是否在允许的域名白名单内（SSRF 防护）"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.hostname in ALLOWED_DOWNLOAD_DOMAINS
    except Exception:
        return False


def download_skill_md(owner_repo: str, skill_name: str, timeout: int = 10) -> str:
    """
    尝试从 GitHub raw URL 下载 SKILL.md。
    尝试多种路径格式，返回内容或空字符串。
    """
    for path_template in SKILL_MD_PATHS:
        path = path_template.format(skill_name=skill_name)
        url = f"https://raw.githubusercontent.com/{owner_repo}/HEAD/{path}"

        # SSRF 防护：检查 URL 域名
        if not _is_safe_url(url):
            continue

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "skill-advisor-backfill/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            if content and len(content) > 50:
                return content
        except Exception:
            continue
    return ""


def process_one_skill(row, dry_run=False):
    """处理单条技能 SKILL.md。

    返回: (merged_id, description, skill_md_content) 或 None
    """
    skill_id, name, source = row

    if not source or "/" not in source:
        return None

    parts = skill_id.split("/")
    if len(parts) >= 3:
        skill_name = parts[2]
        # 处理 react:components 这类带冒号的名称
        skill_name = skill_name.replace(":", "-")
    elif len(parts) == 2:
        skill_name = parts[1].replace(":", "-")
    else:
        skill_name = name.lower().replace(" ", "-")

    owner_repo = source
    content = download_skill_md(owner_repo, skill_name)

    if not content:
        return None

    parsed_name, parsed_desc = parse_frontmatter(content)
    desc = parsed_desc or content[:300].replace("\n", " ").strip()

    return (skill_id, desc, content[:2000])


def backfill(db_path=None, limit=None, workers=4, dry_run=False):
    """补全技能描述。"""
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 获取需要描述的 skills.sh 条目（已有描述的不需要重取）
    # 先从 skills_merged 表中找到 description 为空的
    query = """
        SELECT s.skill_id, s.name, s.source
        FROM skills_sh_skills s
        INNER JOIN skills_merged m ON m.source LIKE '%skills_sh%' AND m.normalized_name = (
            SELECT normalized_name FROM skills_merged
            WHERE source LIKE '%skills_sh%'
            ORDER BY id LIMIT 1
        )
        WHERE s.source IS NOT NULL AND s.source LIKE '%/%'
    """

    # 简化：读取所有有 source 的 skills.sh 条目
    rows = conn.execute("""
        SELECT skill_id, name, source
        FROM skills_sh_skills
        WHERE source IS NOT NULL AND source LIKE '%/%'
        ORDER BY installs DESC
    """).fetchall()

    total = len(rows)
    if limit:
        rows = rows[:limit]

    print(f"[回补] 待处理: {len(rows)} / {total} 条（有 source 的 skills.sh 技能）")
    print(f"[回补] 并发数: {workers}, dry_run: {dry_run}")
    print()

    found = 0
    missing = 0
    descs_written = 0

    # 预加载已有的 merged 映射
    merged_map = {}
    for row in conn.execute("SELECT id, name, source FROM skills_merged WHERE source LIKE '%skills_sh%'"):
        merged_map[row[1]] = row[0]

    def worker_fn(row):
        """单个工作线程 — 尝试多种路径下载 SKILL.md 并提取描述"""
        return process_one_skill(row, dry_run)

    batch = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(worker_fn, row): row for row in rows}

        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            skill_id, name, source = futures[future]

            if result:
                _, desc, content = result
                found += 1
                batch.append((skill_id, name, desc, content))
            else:
                missing += 1

            # 每 50 条打印进度
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                print(f"  ... {i+1}/{len(rows)} ({rate:.0f}/秒) 命中={found} 缺失={missing}")

            # 批量写入（每 100 条）
            if not dry_run and len(batch) >= 100:
                _write_batch(conn, batch)
                descs_written += len(batch)
                batch = []

    # 最后一批
    if not dry_run and batch:
        _write_batch(conn, batch)
        descs_written += len(batch)

    conn.commit()
    conn.close()

    elapsed = time.time() - start
    print()
    print(f"=" * 50)
    print(f"✅ 回补完成")
    print(f"  总计处理: {len(rows)}")
    print(f"  SKILL.md 命中: {found} ({found/len(rows)*100:.1f}%)")
    print(f"  未找到: {missing}")
    print(f"  写入描述: {descs_written}")
    print(f"  耗时: {elapsed:.1f}s")
    print(f"=" * 50)


def _write_batch(conn, batch):
    """批量写回数据库。

    更新 skills_merged 表的 description 字段。
    匹配条件: skills.sh 的 skill_id ↔ skills_merged 的 name/source 关联。
    """
    for skill_id, name, desc, content in batch:
        # 通过 skill_id（owner/repo/name 格式）匹配 skills_merged 的 name
        parts = skill_id.split("/")
        skill_name = parts[-1] if parts else skill_id

        # 尝试多种匹配策略
        conn.execute("""
            UPDATE skills_merged
            SET description = ?
            WHERE source LIKE '%skills_sh%'
              AND description = ''
              AND (name = ? OR name = ? OR normalized_name = ?)
        """, (desc, name, skill_name, skill_name.replace("-", "").replace("_", "")))

        # 如果没有精确匹配，尝试模糊匹配
        conn.execute("""
            UPDATE skills_merged
            SET description = ?
            WHERE source LIKE '%skills_sh%'
              AND description = ''
              AND name LIKE ?
            AND rowid IN (
                SELECT rowid FROM skills_merged
                WHERE source LIKE '%skills_sh%'
                  AND description = ''
                  AND name LIKE ?
                LIMIT 1
            )
        """, (desc, f"%{skill_name}%", f"%{skill_name}%"))

    conn.commit()


def show_stats(db_path=None):
    """显示描述覆盖率统计。"""
    if db_path is None:
        db_path = DB_PATH

    if not Path(db_path).exists():
        print("❌ 数据库不存在")
        return

    conn = sqlite3.connect(str(db_path))

    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    with_desc = conn.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != ''"
    ).fetchone()[0]

    # 按来源统计
    rows = conn.execute("""
        SELECT
            CASE
                WHEN source LIKE '%skills_sh%' THEN 'skills.sh'
                WHEN source LIKE '%clawhub%' THEN 'ClawHub'
                WHEN source LIKE '%github%' THEN 'GitHub'
                WHEN source LIKE '%local%' THEN '本地'
                ELSE '其他'
            END AS src,
            COUNT(*) AS total,
            SUM(CASE WHEN description != '' THEN 1 ELSE 0 END) AS with_desc
        FROM skills_merged
        GROUP BY src
    """).fetchall()

    print()
    print("=" * 55)
    print("📊 描述覆盖率统计")
    print("=" * 55)
    print(f"  总技能数:     {total:,}")
    print(f"  有描述的:     {with_desc:,} ({with_desc/total*100:.1f}%)")
    print()
    print(f"  {'来源':<15s} {'总数':>8s} {'有描述':>8s} {'覆盖率':>8s}")
    print(f"  {'-'*47}")
    for src, cnt, desc in rows:
        pct = f"{desc/cnt*100:.1f}%" if cnt > 0 else "0%"
        print(f"  {src:<15s} {cnt:>8,} {desc:>8,} {pct:>8s}")
    print("=" * 55)
    conn.close()


def main():
    """描述回补主入口 — 从 GitHub raw URL 下载 SKILL.md 补全技能描述"""
    parser = argparse.ArgumentParser(description="回补 skills.sh 技能描述")
    parser.add_argument("--db", default=str(DB_PATH), help="数据库路径")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条")
    parser.add_argument("--workers", type=int, default=4, help="并发下载数")
    parser.add_argument("--dry-run", action="store_true", help="不写数据库")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    args = parser.parse_args()

    if args.stats:
        show_stats(args.db)
        return

    backfill(db_path=args.db, limit=args.limit, workers=args.workers, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
