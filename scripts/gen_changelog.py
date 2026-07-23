#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(__file__).parent.parent / "data" / "skill-advisor.db"
CHANGELOG = Path(__file__).parent.parent / "CHANGELOG.md"

def generate():
    """生成变更日志 — 对比更新前后的数据库状态，输出变更摘要"""
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    with_desc = conn.execute("SELECT COUNT(*) FROM skills_merged WHERE description != ''").fetchone()[0]
    conn.close()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    coverage = (with_desc / total * 100) if total else 0
    entry = "## [auto] %s - DB Sync" % date_str
    entry += chr(10) + chr(10)
    entry += "- Total skills: %d" % total
    entry += chr(10)
    entry += "- With description: %d (%.1f%%)" % (with_desc, coverage)
    entry += chr(10)
    existing = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# Changelog" + chr(10) + chr(10)
    parts = existing.split(chr(10))
    new_content = parts[0] + chr(10) + chr(10) + entry + chr(10) + chr(10)
    new_content += chr(10).join(parts[2:]) if len(parts) > 2 else ""
    CHANGELOG.write_text(new_content, encoding="utf-8")
    print("Changelog updated")

if __name__ == "__main__":
    generate()
