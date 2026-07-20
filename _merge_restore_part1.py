def merge_all_sources(conn):
    """5 个数据源 → 去重合并到 skills_merged"""
    print("
[合并] 去重合并所有数据源...")

    # 清空旧数据
    conn.execute("DELETE FROM skills_merged")
    conn.execute("DELETE FROM skills_fts")

    merged = {}  # normalized_name → skill dict

    # 辅助函数
    def add_skill(name, desc, source, installs=0, stars=0, topics=None, url="", cn_aliases=None):
        norm = normalize_name(name)
        if not norm or len(norm) < 2:
            return
        if norm in merged:
            existing = merged[norm]
            if len(desc) > len(existing.get("description", "")):
                existing["description"] = desc
            existing.setdefault("sources_set", set()).add(source)
            existing["installs"] = max(existing["installs"], installs)
            existing["stars"] = max(existing["stars"], stars)
            if url:
                existing.setdefault("urls", []).append(url)
            if topics:
                existing_topics = set(existing.get("topics", []))
                existing_topics.update(topics)
                existing["topics"] = list(existing_topics)
        else:
            merged[norm] = {
                "name": name,
                "normalized_name": norm,
                "description": desc,
                "sources_set": {source},  # 用 set 去重
                "installs": installs,
                "stars": stars,
                "topics": topics or [],
                "urls": [url] if url else [],
            }

    # 1. ClawHub (最高质量)
    rows = conn.execute(
        "SELECT slug, display_name, summary, description, topics, tags, downloads, installs, stars FROM clawhub_skills"
    ).fetchall()
    for row in rows:
        slug, dn, summary, desc, topics_json, tags_json, dl, ins, st = row
        topics = []
        try:
            topics = json.loads(topics_json or "[]")
        except:
            pass
        try:
            tags = json.loads(tags_json or "[]")
            topics.extend(tags)
        except:
            pass
        final_desc = desc or summary or ""
        url = f"https://clawhub.ai/skills/{slug}"
        cn_aliases = [t for t in tags if any('一' <= c <= '鿿' for c in t)]
        add_skill(dn or slug, final_desc, "clawhub", installs=ins or dl, stars=st,
                  topics=list(set(topics)), url=url, cn_aliases=cn_aliases)
    print(f"  ClawHub: {len(rows)} 条")

    # 2. skills.sh (量最大)
    rows = conn.execute(
        "SELECT skill_id, name, installs FROM skills_sh_skills"
    ).fetchall()
    for row in rows:
        sid, name, installs = row
        if not name:
            name = sid.split("/")[-1] if "/" in sid else sid
        url = f"https://skills.sh/skill/{sid}"
        add_skill(name, "", "skills_sh", installs=installs or 0, url=url)
    print(f"  skills.sh: {len(rows)} 条")