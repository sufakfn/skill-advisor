#!/usr/bin/env python3
"""从 GitHub URL 反查技能描述 + 名字关键词提取"""

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

STOPWORDS = {'a', 'an', 'the', 'for', 'to', 'of', 'in', 'on', 'with', 'and', 'or',
             'skill', 'claude', 'agent', 'ai', 'code', 'dev', 'tool', 'helper'}


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


def generate_pseudo_description(name):
    """从技能名生成伪描述"""
    clean = re.sub(r'[-_:]+', ' ', name)
    clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)
    words = clean.lower().split()
    keywords = [w for w in words if w not in STOPWORDS and len(w) > 1]
    if keywords:
        return f"AI coding skill for {' '.join(keywords[:5])}"
    return ""


def fetch_via_api(url):
    """通过 GitHub API 获取 SKILL.md"""
    match = re.match(r'https?://github\.com/(.+?)(?:/blob/[^/]+)?/(.+/SKILL\.md)', url)
    if not match:
        return None
    path = match.group(2)
    api_url = f"https://api.github.com/repos/{path}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "skill-advisor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if 'content' in data:
                import base64
                return base64.b64decode(data['content']).decode('utf-8', errors="replace")
    except Exception:
        pass
    return None


def backfill(execute=False, max_items=5000):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, urls FROM skills_merged "
        "WHERE (description = '' OR description IS NULL) "
        "ORDER BY installs DESC LIMIT ?",
        (max_items,)
    ).fetchall()
    print(f"Found {len(rows)} skills to backfill")
    
    success = 0
    api_count = 0
    pseudo_count = 0
    
    for row in rows:
        desc = ""
        urls = []
        try:
            urls = json.loads(row["urls"])
        except Exception:
            pass
        
        # 策略1: GitHub API（准确）
        for url in urls:
            if "github.com" in url and "SKILL.md" in url:
                content = fetch_via_api(url)
                if content:
                    desc = extract_fm_desc(content)
                    if desc:
                        api_count += 1
                        break
                time.sleep(0.1)  # 限速
        
        # 策略2: 名字关键词提取（兜底）
        if not desc:
            desc = generate_pseudo_description(row["name"])
            if desc:
                pseudo_count += 1
        
        if desc and execute:
            conn.execute(
                "UPDATE skills_merged SET description = ? WHERE id = ?",
                (desc, row["id"])
            )
            success += 1
    
    if execute:
        conn.commit()
    conn.close()
    print(f"Backfilled: {success}/{len(rows)} (API: {api_count}, pseudo: {pseudo_count})")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    max_items = 5000
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_items = int(sys.argv[idx + 1])
    backfill(execute=not dry_run, max_items=max_items)
