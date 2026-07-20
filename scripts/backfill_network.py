#!/usr/bin/env python3
"""Phase 2.6 - Network Description Backfill (Accurate)

Fetches real SKILL.md from GitHub to extract descriptions.
Usage:
  python scripts/backfill_network.py           # dry run
  python scripts/backfill_network.py --execute   # apply
  python scripts/backfill_network.py --execute --max 100
"""

import re, json, sqlite3, time, urllib.request
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "skills.db"
STATE = Path(__file__).parent.parent / "data" / "backfill_state.json"
DELAY = 1.0

# Pre-compiled regexes (repr-injected at generation time)
FM_RE = re.compile('^---\\s*\\n(.*?)\\n---', re.DOTALL)
DESC_RE = re.compile('^description:\\s*["\']?(.+?)["\']?\\s*$', re.MULTILINE)
GH_RE = re.compile('https?://github\\.com/([^/]+)/([^/]+)/(.+)')
COPY_RE = re.compile('Copy #\\d+ of ')

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"processed": [], "success": 0}

def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def parse_github_url(url):
    m = GH_RE.match(url)
    if not m: return None, None
    return m.group(1) + "/" + m.group(2), m.group(3)

def fetch_raw(owner_repo, path):
    clean = COPY_RE.sub("", path)
    encoded = clean.replace(" ", "%20").replace("#", "%23")
    for branch in ["main", "master"]:
        url = "https://raw.githubusercontent.com/" + owner_repo + "/" + branch + "/" + encoded
        req = urllib.request.Request(url, headers={"User-Agent": "skill-advisor/6.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception:
            continue
    return None

def extract_desc(content):
    fm = FM_RE.match(content)
    if not fm: return ""
    d = DESC_RE.search(fm.group(1))
    if d:
        return d.group(1).strip().strip('"').strip("'")[:300]
    return ""

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--max", type=int, default=5)
    args = p.parse_args()
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    state = load_state()
    targets = conn.execute(
        "SELECT id, name, urls FROM skills_merged "
        "WHERE (description = ? OR description IS NULL) "
        "AND urls LIKE ? ORDER BY installs DESC",
        ("", "%github.com%")
    ).fetchall()
    mode = "EXECUTE" if args.execute else "DRY RUN"
    print("Phase 2.6 - Network Backfill: " + mode)
    print("Targets: " + str(len(targets)))
    print("=" * 50)
    success = 0
    requests = 0
    for row in targets:
        rid = row["id"]
        if rid in state["processed"]: continue
        if requests >= args.max: break
        try:
            urls = json.loads(row["urls"])
        except Exception:
            state["processed"].append(rid); continue
        gh_urls = [u for u in urls if "github.com" in u]
        if not gh_urls:
            state["processed"].append(rid); continue
        desc = ""
        for gh_url in gh_urls:
            owner_repo, path = parse_github_url(gh_url)
            if not owner_repo: continue
            requests += 1
            content = fetch_raw(owner_repo, path)
            if content:
                desc = extract_desc(content)
                if desc: break
            time.sleep(DELAY)
        if desc:
            success += 1
        if desc and args.execute:
            conn.execute("UPDATE skills_merged SET description = ? WHERE id = ?", (desc, rid))
            success += 1
        state["processed"].append(rid)
        if requests % 10 == 0:
            save_state(state)
            print("  " + str(requests) + " fetched, " + str(success) + " found")
    if args.execute: conn.commit()
    save_state(state)
    conn.close()
    conn2 = sqlite3.connect(str(DB))
    total = conn2.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    with_d = conn2.execute(
        "SELECT COUNT(*) FROM skills_merged WHERE description != ? AND description IS NOT NULL",
        ("",)
    ).fetchone()[0]
    conn2.close()
    print("Coverage: " + str(with_d) + "/" + str(total) + " (" + str(round(with_d*100/total, 1)) + "%)")

if __name__ == "__main__":
    main()
