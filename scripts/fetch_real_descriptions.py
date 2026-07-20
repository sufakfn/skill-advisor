#!/usr/bin/env python3
"""从 GitHub SKILL.md 抓取真实描述"""

import json
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
DESC_RE = re.compile(r"^description:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)


def extract_fm_desc(content):
    if not content:
        return ""
    fm = FM_RE.match(content)
    if not fm:
        return ""
    desc = DESC_RE.search(fm.group(1))
    if desc:
        return desc.group(1).strip().strip('"').strip("'")[:300]
    return ""


def clean_github_url(url):
    """清理 GitHub URL，返回 (owner, repo, subpath) 或 None"""
    if ' ' in url:
        return None
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)(?:/blob/[^/]+)?/(.+)', url)
    if not match:
        return None
    owner, repo, subpath = match.group(1), match.group(2), match.group(3)
    repo = repo.replace('.git', '')
    basename = subpath.rsplit('/', 1)[-1] if '/' in subpath else subpath
    if not basename.lower().endswith('skill.md'):
        subpath = subpath.rsplit('/', 1)[0] + '/SKILL.md'
    return (owner, repo, subpath)


def fetch_via_raw(owner, repo, subpath):
    """通过 raw.githubusercontent.com 获取"""
    for branch in ["main", "master"]:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{subpath}"
        req = urllib.request.Request(raw_url, headers={"User-Agent": "skill-advisor/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception:
            continue
    return None


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, name, urls FROM skills_merged
        WHERE (description = '' OR description IS NULL)
        AND urls LIKE '%github.com%'
        ORDER BY installs DESC
    """).fetchall()

    print(f"Found {len(rows)} skills with GitHub URL but no description", flush=True)

    success = 0
    for i, row in enumerate(rows):
        try:
            urls = json.loads(row["urls"])
        except Exception:
            continue

        for url in urls:
            if "github.com" not in url:
                continue

            cleaned = clean_github_url(url)
            if not cleaned:
                continue

            owner, repo, subpath = cleaned
            try:
                content = fetch_via_raw(owner, repo, subpath)
                if content:
                    desc = extract_fm_desc(content)
                    if desc:
                        conn.execute(
                            "UPDATE skills_merged SET description = ? WHERE id = ?",
                            (desc, row["id"])
                        )
                        success += 1
                        if success <= 5:
                            print(f"  #{success}: {row['name']} -> {desc[:50]}", flush=True)
                        break
            except Exception as e:
                print(f"  Error processing {row['name']}: {e}", flush=True)

        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"  Progress: {i+1}/{len(rows)}, success: {success}", flush=True)

        time.sleep(0.3)

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    with_desc = conn.execute("SELECT COUNT(*) FROM skills_merged WHERE description != ''").fetchone()[0]
    conn.close()

    print(f"\nDone. Success: {success}/{len(rows)}")
    print(f"Coverage: {with_desc}/{total} ({with_desc*100/total:.1f}%)")


if __name__ == "__main__":
    main()
