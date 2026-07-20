#!/usr/bin/env python3
"""合并 SkillFinder 数据到 skill-advisor"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"
SKILLFINDER_FILE = Path(__file__).parent.parent / "data" / "skillfinder_metadata.jsonl"


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 读取现有技能（用于去重）
    existing = conn.execute("SELECT id, name, normalized_name, source, urls FROM skills_merged").fetchall()
    existing_names = {row['name'].lower() for row in existing}
    existing_normalized = {row['normalized_name'] for row in existing}
    existing_urls = set()
    for row in existing:
        try:
            urls = json.loads(row['urls'])
            for u in urls:
                existing_urls.add(u.lower())
        except:
            pass

    print(f"Existing skills: {len(existing_names)}")
    print(f"Existing URLs: {len(existing_urls)}")

    # 读取 SkillFinder 数据
    new_skills = []
    duplicates = 0
    with open(SKILLFINDER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            name = data.get('name', '').strip()
            desc = data.get('description', '')
            if isinstance(desc, list):
                desc = ' '.join(str(d) for d in desc) if desc else ''
            desc = str(desc).strip() if desc else ''

            # 跳过无描述
            if not desc:
                continue

            # 去重：检查 name 和 skill_md_url
            skill_url = data.get('skill_md_url', '').lower()
            normalized = name.lower().replace(' ', '-')

            if name.lower() in existing_names or normalized in existing_normalized or skill_url in existing_urls:
                duplicates += 1
                continue

            # 构建安装命令
            install_cmd = data.get('install_cmd', {})
            if isinstance(install_cmd, dict):
                install_cmd_str = install_cmd.get('claude_code', '')
            else:
                install_cmd_str = str(install_cmd) if install_cmd else ''

            # 构建 URLs
            urls = []
            if data.get('skill_md_url'):
                urls.append(data['skill_md_url'])
            if data.get('repo_url'):
                urls.append(data['repo_url'])

            # 构建 source
            source = data.get('source', [])
            if isinstance(source, list):
                source_str = ','.join(source) if source else 'skillfinder'
            else:
                source_str = str(source) if source else 'skillfinder'

            # 质量分
            quality = data.get('quality', {})
            stars = quality.get('stars', 0)

            new_skills.append({
                'name': name,
                'normalized_name': normalized,
                'description': desc[:300],
                'source': source_str,
                'installs': 0,
                'stars': stars,
                'topics': json.dumps(data.get('topics', []), ensure_ascii=False),
                'urls': json.dumps(urls, ensure_ascii=False),
                'quality_score': min(100, stars // 10),
                'verified': 1,
            })

    print(f"New skills to add: {len(new_skills)}")
    print(f"Duplicates skipped: {duplicates}")

    # 插入新技能（忽略约束冲突）
    inserted = 0
    for skill in new_skills:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO skills_merged 
                (name, normalized_name, description, source, installs, stars, topics, urls, quality_score, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill['name'], skill['normalized_name'], skill['description'],
                skill['source'], skill['installs'], skill['stars'],
                skill['topics'], skill['urls'], skill['quality_score'], skill['verified']
            ))
            inserted += 1
        except Exception as e:
            pass

    conn.commit()

    # 最终统计
    total = conn.execute("SELECT COUNT(*) FROM skills_merged").fetchone()[0]
    verified = conn.execute("SELECT COUNT(*) FROM skills_merged WHERE verified = 1").fetchone()[0]
    conn.close()

    print(f"\nInserted: {inserted}")
    print(f"Final: {total} skills ({verified} verified)")


if __name__ == "__main__":
    main()
