#!/usr/bin/env python3
"""
缓存生成器 v2 — 构建 skill-advisor.db (SQLite + FTS5)

数据源:
  1. ClawHub API      (~2500条, 完整描述+标签+下载量)
  2. skills.sh API     (~10000条, 名字+安装量, 220关键词扫描)
  3. GitHub Topic      (~15000条, 需GITHUB_TOKEN) ★Tree API解析SKILL.md
  4. GitHub Code       (~10000条, 需GITHUB_TOKEN) ★下载SKILL.md解析
  5. 本地已安装技能     (自动扫描)

目标覆盖量: 30,000~50,000 条

输出: data/skill-advisor.db (SQLite, FTS5全文索引)

用法:
  python build_cache.py                           # 全量构建
  python build_cache.py --source clawhub          # 只构建某一个源
  python build_cache.py --source github_topic     # GitHub Topic爬取
  python build_cache.py --source github_code      # GitHub Code搜索
  python build_cache.py --github-token xxx        # 传入GitHub Token
  python build_cache.py --resume                  # 断点续传
  python build_cache.py --stats                   # 显示缓存统计
  python build_cache.py --max-repos 500           # 每个topic最多处理repo数

GitHub Token 获取:
  1. https://github.com/settings/tokens
  2. Generate new token (classic)
  3. 勾选 "public_repo" 权限 (只读公开仓库)
  4. 复制 token (ghp_ 开头)
"""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# === 路径 ===
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "skill-advisor.db"
STATE_PATH = DATA_DIR / "build_state.json"

# === API 配置 ===
CLAWHUB_API = "https://clawhub.ai/api/v1/skills"
SKILLS_SH_API = "https://skills.sh/api/search"
GITHUB_API = "https://api.github.com"

# 200个扫描关键词 (分类覆盖)
SKILLS_SH_KEYWORDS = [
    # 编程语言 (20)
    "react", "python", "javascript", "typescript", "rust", "go", "java", "swift", "flutter", "vue",
    "node", "next", "nuxt", "django", "fastapi", "express", "rails", "spring", "laravel", "svelte",
    # AI/ML (20)
    "ai", "ml", "llm", "gpt", "claude", "openai", "hugging", "embedding", "vector", "rag",
    "agent", "chatbot", "image", "video", "audio", "speech", "ocr", "translate", "summary", "search",
    # 开发工具 (20)
    "database", "sql", "postgres", "mongo", "redis", "docker", "kubernetes", "aws", "gcp", "azure",
    "github", "git", "ci", "cd", "deploy", "monitor", "logging", "auth", "oauth", "payment",
    # 商业/营销 (20)
    "email", "crm", "analytics", "seo", "marketing", "sales", "finance", "stock", "crypto", "ecommerce",
    "social", "blog", "news", "content", "media", "music", "game", "travel", "food", "health",
    # 日常工具 (20)
    "file", "pdf", "excel", "word", "ppt", "image", "photo", "video-edit", "download", "convert",
    "browser", "scraper", "automation", "schedule", "note", "task", "calendar", "weather", "map", "code",
    # 安全/测试 (20)
    "security", "test", "testing", "audit", "vulnerability", "scan", "fuzzing", "coverage", "qa", "lint",
    "performance", "optimization", "cache", "storage", "backup", "migration", "upgrade", "debug", "error", "trace",
    # 框架/库 (20)
    "tailwind", "prisma", "supabase", "firebase", "stripe", "twilio", "resend", "sentry", "vercel", "netlify",
    "figma", "notion", "slack", "discord", "telegram", "whatsapp", "twitter", "youtube", "spotify", "trello",
    # 数据/可视化 (20)
    "chart", "visualization", "dashboard", "report", "csv", "json", "xml", "api", "graphql", "rest",
    "webhook", "websocket", "stream", "etl", "pipeline", "workflow", "cron", "queue", "job", "batch",
    # 写作/内容 (20)
    "writing", "copywriting", "readme", "docs", "documentation", "tutorial", "course", "learn", "study", "quiz",
    "resume", "cover-letter", "interview", "presentation", "slide", "invoice", "contract", "legal", "proposal", "email-write",
    # 中文场景 (20)
    "wechat", "xiaohongshu", "douyin", "bilibili", "taobao", "jd", "meituan", "alipay", "weibo", "zhihu",
    "baidu", "tencent", "bytedance", "alibaba", "huawei", "xiaomi", "netease", "pinduoduo", "kuaishou", "rednote",
    # 其他 (20)
    "ios", "android", "desktop", "cli", "terminal", "shell", "config", "setup", "boilerplate", "template",
    "theme", "icon", "font", "color", "animation", "3d", "vr", "ar", "blockchain", "web3",
]

# GitHub Topic 搜索关键词 (多源爬取)
GITHUB_TOPICS = [
    "claude-skill", "claude-code-skill", "claude-skills", "claude-code-skills",
    "openclaw-skill", "codex-skill", "codex-skills", "agent-skill", "agent-skills",
    "cursor-skills", "kiro-skill", "ai-skill", "ai-skills",
    "claude-agent", "ai-agent", "llm-agent",
    "skill-creator", "skill-marketplace", "skill-registry",
    "SKILL.md", "agent-skill",
]


# ============================================================
# SQLite 数据库初始化
# ============================================================

def init_database(db_path):
    """初始化 SQLite 数据库 + FTS5 全文索引"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")  # 并发性能
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript("""
        -- ClawHub 原始数据
        CREATE TABLE IF NOT EXISTS clawhub_skills (
            slug TEXT PRIMARY KEY,
            display_name TEXT,
            summary TEXT,
            description TEXT,
                topics TEXT,  -- JSON array
            tags TEXT,    -- JSON array
            downloads INTEGER DEFAULT 0,
            installs INTEGER DEFAULT 0,
            stars INTEGER DEFAULT 0,
            raw_json TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- skills.sh 原始数据
        CREATE TABLE IF NOT EXISTS skills_sh_skills (
            skill_id TEXT PRIMARY KEY,
            name TEXT,
            installs INTEGER DEFAULT 0,
            source TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- GitHub Topic 数据
        CREATE TABLE IF NOT EXISTS github_topic_skills (
            repo_fullname TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            stars INTEGER DEFAULT 0,
            topics TEXT,  -- JSON array
            skill_md_path TEXT,
            skill_md_content TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- GitHub Code Search 数据
        CREATE TABLE IF NOT EXISTS github_code_skills (
            repo_path TEXT PRIMARY KEY,  -- "owner/repo/path/SKILL.md"
            repo_fullname TEXT,
            name TEXT,
            description TEXT,
            stars INTEGER DEFAULT 0,
            skill_md_content TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 本地已安装技能
        CREATE TABLE IF NOT EXISTS local_skills (
            name TEXT PRIMARY KEY,
            path TEXT,
            description TEXT,
            raw_content TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 去重合并后的统一视图
        CREATE TABLE IF NOT EXISTS skills_merged (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            description TEXT,
            name_aliases TEXT,   -- JSON array 中文别名/昵称 (用于中文搜索)
            source TEXT,        -- clawhub|skills_sh|github_topic|github_code|local
            source_detail TEXT, -- 来源详情 JSON
            installs INTEGER DEFAULT 0,
            stars INTEGER DEFAULT 0,
            topics TEXT,         -- JSON array
            urls TEXT,           -- JSON array 安装URL列表
            quality_score REAL DEFAULT 0,  -- 综合质量评分
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(normalized_name, source)
        );

        -- FTS5 全文索引 (在 name + description + name_aliases 上)
        -- 使用 trigram tokenizer 支持中文 (3字滑动窗口匹配)
        CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
            name, description, topics, name_aliases,
            content=skills_merged,
            content_rowid=id,
            tokenize='trigram'
        );

        -- 同步 FTS 索引的触发器
        CREATE TRIGGER IF NOT EXISTS skills_fts_insert
        AFTER INSERT ON skills_merged BEGIN
            INSERT INTO skills_fts(rowid, name, description, topics, name_aliases)
            VALUES (new.id, new.name, COALESCE(new.description,''), COALESCE(new.topics,''), COALESCE(new.name_aliases,''));
        END;

        -- 构建状态追踪
        CREATE TABLE IF NOT EXISTS build_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 向量嵌入存储（用于语义搜索）
        CREATE TABLE IF NOT EXISTS skills_vectors (
            skill_id INTEGER PRIMARY KEY,
            embedding BLOB NOT NULL,        -- float32 序列化
            model TEXT NOT NULL,            -- 模型名，如 'all-MiniLM-L6-v2'
            dimensions INTEGER NOT NULL,    -- 向量维度，如 384
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (skill_id) REFERENCES skills_merged(id)
        );
    """)

    conn.commit()
    return conn


# ============================================================
# 数据源 1: ClawHub 全量拉取
# ============================================================

def fetch_clawhub_all(conn, limit=100):
    """翻页游标拉取 ClawHub 全量技能"""
    print("\n[1/5] 拉取 ClawHub 全量数据...")

    cursor = None
    page = 0
    total = 0

    while True:
        params = f"sort=downloads&dir=desc&limit={limit}"
        if cursor:
            params += f"&cursor={json.dumps(cursor)}"

        url = f"{CLAWHUB_API}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "skill-advisor-cache/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  ClawHub 第{page}页错误: {e}")
            conn.commit()  # 先提交已有数据
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            slug = item.get("slug", "")
            stats = item.get("stats", {})
            conn.execute("""
                INSERT OR REPLACE INTO clawhub_skills
                (slug, display_name, summary, description, topics, tags,
                 downloads, installs, stars, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                slug,
                item.get("displayName", ""),
                item.get("summary", ""),
                item.get("description", ""),
                json.dumps(item.get("topics", []), ensure_ascii=False),
                json.dumps(item.get("tags", []), ensure_ascii=False),
                stats.get("downloads", 0),
                stats.get("installs", 0),
                stats.get("stars", 0),
                json.dumps(item, ensure_ascii=False),
            ))
            total += 1

        conn.commit()
        page += 1
        next_cursor = data.get("nextCursor")

        if not next_cursor or not items:
            break

        cursor = next_cursor

        if page % 10 == 0:
            print(f"  ...已拉取 {total} 条 ({page} 页)")

        time.sleep(0.5)  # 礼貌延迟

    print(f"  ✅ ClawHub: 共 {total} 条")
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES (?, ?)",
        ("clawhub_count", str(total))
    )
    conn.commit()
    return total


# ============================================================
# 数据源 2: skills.sh 关键词扫描
# ============================================================

def fetch_skills_sh_all(conn, keywords=None, limit_per_keyword=200):
    """多关键词扫描 skills.sh"""
    print("\n[2/5] 扫描 skills.sh 市场...")

    if keywords is None:
        keywords = SKILLS_SH_KEYWORDS

    seen_ids = set()
    total_new = 0
    errors = 0

    # 加载已采集的 (支持断点续传)
    existing = conn.execute("SELECT skill_id FROM skills_sh_skills").fetchall()
    for (sid,) in existing:
        seen_ids.add(sid)
    print(f"  已有缓存: {len(seen_ids)} 条")

    for i, kw in enumerate(keywords):
        url = f"{SKILLS_SH_API}?q={kw}&limit={limit_per_keyword}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "skill-advisor-cache/1.0",
            "Accept": "application/json"
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            for s in data.get("skills", []):
                sid = s.get("id", "")
                if sid and sid not in seen_ids:
                    seen_ids.add(sid)
                    conn.execute("""
                        INSERT OR REPLACE INTO skills_sh_skills
                        (skill_id, name, installs, source)
                        VALUES (?, ?, ?, ?)
                    """, (
                        sid,
                        s.get("name", ""),
                        s.get("installs", 0),
                        s.get("source", ""),
                    ))
                    total_new += 1

            # 每20个关键词提交一次
            if (i + 1) % 20 == 0:
                conn.commit()
                print(f"  ...进度: {i+1}/{len(keywords)} 关键词, 新增 {total_new} 条, {errors} 错误")

            time.sleep(0.1)  # 礼貌延迟

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  关键词 '{kw}' 错误: {e}")
            time.sleep(1)  # 犯错后多等一会

    conn.commit()
    total = len(seen_ids)
    print(f"  ✅ skills.sh: 新增 {total_new} 条, 总计 {total} 条, {errors} 错误")
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES (?, ?)",
        ("skills_sh_count", str(total))
    )
    conn.commit()
    return total


# ============================================================
# 数据源 3: GitHub Topic 搜索
# ============================================================

def github_api_get(url, headers, timeout=20):
    """
    GitHub API 请求封装 — 自动处理速率限制和重试

    返回 (data_dict, remaining_quota) 或 (None, remaining_quota)
    """
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            remaining = int(resp.headers.get("X-RateLimit-Remaining", 5000))
            reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
            data = json.loads(resp.read().decode())

            # 预警: 剩余配额极低 (<3) 才等待
            # 注意: 30次/分钟的速率由调用方控制 (2.1秒间隔)
            # 这里只处理配额即将耗尽的情况
            if remaining < 3:
                wait = max(reset_time - int(time.time()), 0) + 5
                if wait > 300:  # 等超过5分钟就放弃
                    print(f"    ⚠️ 配额剩余 {remaining}, 等待太长 ({wait}秒), 跳过")
                    return None, remaining
                print(f"    ⏳ 配额剩余 {remaining}, 等待 {wait}秒恢复...")
                time.sleep(wait)
                return github_api_get(url, headers, timeout)

            return data, remaining
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            # 速率限制 → 等待并重试
            try:
                reset_time = int(e.headers.get("X-RateLimit-Reset", 0))
            except:
                reset_time = 0
            wait = max(reset_time - int(time.time()), 0) + 10
            if wait > 600:  # 等超过10分钟就放弃
                print(f"    ⚠️ GitHub 限流等待太长 ({wait}秒), 跳过")
                return None, 0
            print(f"    ⏳ GitHub 限流, 等待 {wait}秒后重试...")
            time.sleep(wait)
            return github_api_get(url, headers, timeout)
        return None, 5000
    except Exception as e:
        return None, 5000


def find_skill_md_in_tree(full_name, headers):
    """
    在仓库的 Git Tree 中查找所有 SKILL.md 文件

    返回: [(path, skill_name), ...]
    """
    results = []
    tree_url = f"{GITHUB_API}/repos/{full_name}/git/trees/HEAD?recursive=1"
    data, _ = github_api_get(tree_url, headers, timeout=15)
    if not data:
        return results

    for node in data.get("tree", []):
        path = node.get("path", "")
        if path.endswith("SKILL.md") and node.get("type") == "blob":
            # 从 path 提取技能名 (SKILL.md 的上一级目录名)
            parts = path.split("/")
            skill_name = parts[-2] if len(parts) >= 2 else parts[0]
            results.append((path, skill_name))

    return results


def download_raw_file(raw_url, timeout=10):
    """下载 raw.githubusercontent.com 文件"""
    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "skill-advisor-cache/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")[:3000]
    except:
        return ""


def parse_skill_md_frontmatter(content):
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
                    if len(desc) > 300:
                        desc = desc[:300]
    return name, desc


def fetch_github_topics(conn, token, topics=None):
    """
    GitHub Topic 搜索 — 多源爬取 的 topic_crawler

    流程:
      1. 按 topic 搜索仓库 (每个topic最多1000个)
      2. 对每个仓库用 Tree API 找 SKILL.md
      3. 下载 SKILL.md 并解析 frontmatter
    """
    print("\n[3/5] GitHub Topic 搜索 (Tree API 解析 SKILL.md)...")

    if not token:
        print("  ⚠️ 无 GITHUB_TOKEN, 跳过 GitHub Topic 搜索")
        return 0

    if topics is None:
        topics = GITHUB_TOPICS

    headers = {
        "User-Agent": "skill-advisor-cache/1.0",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }

    total_repos = 0
    total_skills = 0
    seen_repos = set()

    # 已有缓存 (支持断点续传)
    existing = conn.execute("SELECT repo_fullname FROM github_topic_skills").fetchall()
    for (r,) in existing:
        seen_repos.add(r)
    print(f"  已有缓存: {len(seen_repos)} 个repo")

    for topic_idx, topic in enumerate(topics):
        # 搜多页 (每topic最多300 repo)
        repos_processed = 0
        for page in range(1, 4):  # 3 页 × 100 = 300 repo/topic
            url = (f"{GITHUB_API}/search/repositories?q=topic:{topic}"
                   f"&per_page=100&page={page}&sort=stars&order=desc")
            data, remaining = github_api_get(url, headers)

            if not data:
                break

            items = data.get("items", [])
            if not items:
                break

            for repo in items:
                full_name = repo.get("full_name", "")
                if full_name in seen_repos:
                    continue
                seen_repos.add(full_name)
                repos_processed += 1

                # Tree API 找 SKILL.md (消耗 Core 配额, 5000/小时)
                skill_files = find_skill_md_in_tree(full_name, headers)

                if not skill_files:
                    conn.execute("""
                        INSERT OR REPLACE INTO github_topic_skills
                        (repo_fullname, name, description, stars, topics)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        full_name,
                        full_name.split("/")[-1],
                        repo.get("description", "") or "",
                        repo.get("stargazers_count", 0),
                        json.dumps(repo.get("topics", []), ensure_ascii=False),
                    ))
                else:
                    for path, skill_name in skill_files:
                        raw_url = f"https://raw.githubusercontent.com/{full_name}/HEAD/{path}"
                        md_content = download_raw_file(raw_url)
                        parsed_name, parsed_desc = parse_skill_md_frontmatter(md_content)

                        final_name = parsed_name or skill_name
                        final_desc = parsed_desc or (repo.get("description", "") or "")

                        conn.execute("""
                            INSERT OR REPLACE INTO github_topic_skills
                            (repo_fullname, name, description, stars, topics,
                             skill_md_path, skill_md_content)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            full_name,
                            final_name,
                            final_desc,
                            repo.get("stargazers_count", 0),
                            json.dumps(repo.get("topics", []), ensure_ascii=False),
                            path,
                            md_content[:2000],
                        ))
                        total_skills += 1

                total_repos += 1

            # 礼貌延迟: 每个 topic 之间等 2 秒
            time.sleep(2)

        conn.commit()
        print(f"  [{topic_idx+1}/{len(topics)}] {topic}: "
              f"{repos_processed} repo, {total_skills} 技能 (搜索配额: {remaining})")

        # 每5个topic等2分钟 (让 Core API 配额恢复)
        if (topic_idx + 1) % 5 == 0:
            print(f"    ⏳ 等待 120秒 让 API 配额恢复...")
            time.sleep(120)

    print(f"  ✅ GitHub Topic: {total_repos} repo → {total_skills} 技能")
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES (?, ?)",
        ("github_topic_count", str(total_skills))
    )
    conn.commit()
    return total_skills


# ============================================================
# 数据源 4: GitHub Code Search
# ============================================================

def fetch_github_code_search(conn, token, queries=None):
    """
    GitHub Code Search — 直接搜索所有 SKILL.md 文件

    ⚠️ GitHub Search API 限制: 30次/分钟!
    策略: 少量查询 + 最大化每次查询的返回量 + 冷静期等待

    多查询策略 (最大化覆盖):
      - "filename:SKILL.md"           → 直接匹配 (主要)
      - "filename:SKILL.md+claude"     → Claude 相关
      - "filename:SKILL.md+agent"      → Agent 相关
      - "filename:SKILL.md+cursor"     → Cursor 相关

    每个查询最多 1000 条 (GitHub 限制), 每个查询间隔 2秒 以遵守速率限制
    """
    print("\n[4/5] GitHub Code Search (限速: 30次/分钟)...")

    if not token:
        print("  ⚠️ 无 GITHUB_TOKEN, 跳过 GitHub Code Search")
        return 0

    if queries is None:
        # 保守策略: 4个查询 × 1000条 = 4000条
        queries = [
            "filename:SKILL.md",
            "filename:SKILL.md+claude",
            "filename:SKILL.md+agent",
            "filename:SKILL.md+cursor",
        ]

    headers = {
        "User-Agent": "skill-advisor-cache/1.0",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }

    total = 0
    seen_paths = set()

    # 已有缓存 (支持断点续传)
    existing = conn.execute("SELECT repo_path FROM github_code_skills").fetchall()
    for (p,) in existing:
        seen_paths.add(p)
    print(f"  已有缓存: {len(seen_paths)} 条")

    SEARCH_LIMIT_PER_MIN = 25  # 保守: 25次/分钟 (官方限制30)

    for q_idx, query in enumerate(queries):
        page = 1
        query_total = 0
        searches_this_minute = 0

        while page <= 10:  # 每查询最多 10 页 × 100 = 1000 条
            # 速率控制: 每分钟前 25 次搜索, 然后等待
            if searches_this_minute >= SEARCH_LIMIT_PER_MIN:
                print(f"    ⏳ 达到 {SEARCH_LIMIT_PER_MIN}次/分钟, 等待 60 秒...")
                time.sleep(60)
                searches_this_minute = 0

            url = f"{GITHUB_API}/search/code?q={query}&per_page=100&page={page}"
            data, remaining = github_api_get(url, headers)
            searches_this_minute += 1

            if not data:
                break

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                repo_path = f"{item['repository']['full_name']}/{item['path']}"
                if repo_path in seen_paths:
                    continue
                seen_paths.add(repo_path)

                path = item.get("path", "")
                name = item.get("name", "SKILL.md")
                parts = path.split("/")
                if len(parts) >= 2:
                    name = parts[-2]

                # 下载 SKILL.md 内容 (用 raw 链接, 不消耗 API 配额)
                raw_url = f"https://raw.githubusercontent.com/{item['repository']['full_name']}/HEAD/{path}"
                md_content = download_raw_file(raw_url)
                parsed_name, parsed_desc = parse_skill_md_frontmatter(md_content)
                final_name = parsed_name or name

                conn.execute("""
                    INSERT OR REPLACE INTO github_code_skills
                    (repo_path, repo_fullname, name, description, stars, skill_md_content)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    repo_path,
                    item.get("repository", {}).get("full_name", ""),
                    final_name,
                    parsed_desc,
                    item.get("repository", {}).get("stargazers_count", 0),
                    md_content[:2000],
                ))
                total += 1
                query_total += 1

            conn.commit()
            print(f"  [{q_idx+1}/{len(queries)}] '{query}' p{page}: "
                  f"+{query_total} (总 {total}, 搜索配额: {remaining})")

            page += 1
            time.sleep(2.1)  # 每次搜索间隔 >2秒 (30次/分钟 = 2秒/次)

    print(f"  ✅ GitHub Code Search: 共 {total} 条")
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES (?, ?)",
        ("github_code_count", str(total))
    )
    conn.commit()
    return total


# ============================================================
# 数据源 5: 本地技能扫描
# ============================================================

def scan_local_skills(conn):
    """扫描本地已安装的技能"""
    print("\n[5/5] 扫描本地已安装技能...")

    skill_dirs = [
        Path.home() / ".claude" / "skills",
        Path.home() / ".cursor" / "skills",
        Path.home() / ".codex" / "skills",
        Path.home() / ".agents" / "skills",
        Path.home() / ".claude" / "plugins",
    ]

    total = 0
    for base_dir in skill_dirs:
        if not base_dir.exists():
            continue
        for d in sorted(base_dir.iterdir()):
            if not d.is_dir():
                continue
            skill_md = d / "SKILL.md"
            if not skill_md.exists():
                continue

            content = ""
            desc = ""
            try:
                content = skill_md.read_text(encoding="utf-8")[:2000]
                # 从 frontmatter 提取 description
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        for line in content[3:end].split("\n"):
                            if line.strip().startswith("description:"):
                                desc = line.split(":", 1)[1].strip().strip('"').strip("'")[:500]
                                break
            except:
                pass

            conn.execute("""
                INSERT OR REPLACE INTO local_skills (name, path, description, raw_content)
                VALUES (?, ?, ?, ?)
            """, (d.name, str(d), desc, content))
            total += 1

    conn.commit()
    print(f"  ✅ 本地技能: 共 {total} 条")
    return total


# ============================================================
# 去重合并引擎
# ============================================================

def normalize_name(name):
    """名字规范化 — 用于去重"""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r"[\s_\.]+", "-", n)  # 空格/下划线/点 → 连字符
    n = re.sub(r"-+", "-", n)         # 多连字符 → 单连字符
    n = n.strip("-")
    return n


def merge_all_sources(conn, incremental=False):
    """5 个数据源 → 去重合并到 skills_merged

    incremental=False（默认）: 清空重建（全量模式）
    incremental=True: 增量模式 — 不删除已有数据，只添加/更新
    """
    print(f"\n[合并] 去重合并所有数据源... (模式: {'增量' if incremental else '全量'})")

    if not incremental:
        # 全量模式：清空重建
        conn.execute("DELETE FROM skills_merged")
        conn.execute("DELETE FROM skills_fts")

    merged = {}  # normalized_name → skill dict

    # 辅助函数
    def add_skill(name, desc, source, installs=0, stars=0, topics=None, url="", cn_aliases=None):
        norm = normalize_name(name)
        if not norm or len(norm) < 2:
            return
        if norm in merged:
            # 已存在 → 保留描述更长的 + 记录多来源
            existing = merged[norm]
            if len(desc) > len(existing.get("description", "")):
                existing["description"] = desc
            # 用 set 追踪来源，避免重复
            existing.setdefault("sources_set", set()).add(source)
            existing["installs"] = max(existing["installs"], installs)
            existing["stars"] = max(existing["stars"], stars)
            if url:
                existing.setdefault("urls", []).append(url)
            # 合并 topics
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
        # ClawHub 的 tags 也作为中文别名
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

    # 3. GitHub Topic
    rows = conn.execute(
        "SELECT repo_fullname, name, description, stars, topics FROM github_topic_skills"
    ).fetchall()
    for row in rows:
        rfn, name, desc, st, topics_json = row
        topics = []
        try:
            topics = json.loads(topics_json or "[]")
        except:
            pass
        url = f"https://github.com/{rfn}"
        add_skill(name, desc or "", "github_topic", stars=st or 0,
                  topics=topics, url=url)
    print(f"  GitHub Topic: {len(rows)} 条")

    # 4. GitHub Code
    rows = conn.execute(
        "SELECT repo_path, name, stars FROM github_code_skills"
    ).fetchall()
    for row in rows:
        rp, name, st = row
        url = f"https://github.com/{rp}"
        add_skill(name, "", "github_code", stars=st or 0, url=url)
    print(f"  GitHub Code: {len(rows)} 条")

    # 5. 本地
    rows = conn.execute(
        "SELECT name, description FROM local_skills"
    ).fetchall()
    for row in rows:
        name, desc = row
        add_skill(name, desc or "", "local")
    print(f"  本地: {len(rows)} 条")

    # 补充 name_aliases: 从 FALLBACK_SKILLS intent 标签获取中文别名
    try:
        advisor_path = SCRIPT_DIR / "skill_advisor.py"
        if advisor_path.exists():
            content = advisor_path.read_text(encoding="utf-8")
            start = content.find("FALLBACK_SKILLS = [")
            if start > 0:
                end = content.find("]\n\n", start)
                if end > 0:
                    exec_globals = {}
                    exec(content[start:end + 1], exec_globals)
                    for s in exec_globals.get("FALLBACK_SKILLS", []):
                        name = s.get("name", "")
                        intents = s.get("intent", [])
                        cn = [t for t in intents if any('一' <= c <= '鿿' for c in t)]
                        if cn:
                            norm = normalize_name(name)
                            if norm in merged:
                                merged[norm].setdefault("cn_aliases", set()).update(cn)
    except Exception:
        pass

    # 写入合并表 + 计算质量分
    print(f"  去重后: {len(merged)} 个唯一技能")

    # 增量模式：先加载已有数据用于合并
    existing = {}
    if incremental:
        for row in conn.execute("SELECT id, name, normalized_name, description, source, installs, stars, topics, urls, quality_score, name_aliases FROM skills_merged"):
            existing[row[2]] = {
                "id": row[0], "name": row[1], "normalized_name": row[2],
                "description": row[3] or "", "source": row[4] or "",
                "installs": row[5] or 0, "stars": row[6] or 0,
                "online": True  # 标记为已有
            }

    for norm, skill in merged.items():
        # 质量分: 有描述 +30, 有安装量 +0~30, 有stars +0~20, 有topics +0~20
        quality = 0
        if skill["description"]:
            quality += min(30, len(skill["description"]) // 10)
        if skill["installs"] > 0:
            quality += min(30, int(skill["installs"] ** 0.5))
        if skill["stars"] > 0:
            quality += min(20, int(skill["stars"] ** 0.3))
        if skill["topics"]:
            quality += min(20, len(skill["topics"]) * 4)
        quality = min(100, quality)

        urls = list(set(skill.get("urls", [])))[:5]  # 最多5个URL
        sources_str = ",".join(sorted(skill.get("sources_set", {skill.get("source", "")})))
        cn_aliases_json = json.dumps(
            sorted(skill.get("cn_aliases", set())), ensure_ascii=False
        )

        if incremental and norm in existing:
            # 增量模式：已有记录 → 更新（保留更好的描述、更高的安装量）
            ex = existing[norm]
            # 保留更长的描述
            desc = skill["description"][:1000]
            if len(ex.get("description", "")) > len(desc):
                desc = ex["description"]
            # 合并来源
            old_sources = set(ex.get("source", "").split(",")) if ex.get("source") else set()
            new_sources = set(sources_str.split(","))
            merged_sources = ",".join(sorted(old_sources | new_sources))
            # 取更高的 installs/stars
            installs = max(ex.get("installs", 0), skill["installs"])
            stars = max(ex.get("stars", 0), skill["stars"])
            conn.execute("""
                UPDATE skills_merged
                SET name=?, description=?, source=?, installs=?, stars=?,
                    topics=?, urls=?, quality_score=?, name_aliases=?,
                    fetched_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                skill["name"], desc, merged_sources, installs, stars,
                json.dumps(skill["topics"][:20], ensure_ascii=False),
                json.dumps(urls, ensure_ascii=False), quality,
                cn_aliases_json, ex["id"]
            ))
        else:
            # 新记录 → 插入
            conn.execute("""
                INSERT INTO skills_merged
                (name, normalized_name, description, source, installs, stars,
                 topics, urls, quality_score, name_aliases)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill["name"], norm, skill["description"][:1000],
                sources_str, skill["installs"], skill["stars"],
                json.dumps(skill["topics"][:20], ensure_ascii=False),
                json.dumps(urls, ensure_ascii=False), quality,
                cn_aliases_json,
            ))

    conn.commit()

    # 优化 FTS（仅全量模式需要重建，增量模式触发器自动维护）
    if not incremental:
        conn.execute("INSERT INTO skills_fts(skills_fts) VALUES('optimize')")
    conn.commit()

    return len(merged)


# ============================================================
# 统计
# ============================================================

def show_stats(conn):
    """显示缓存统计"""
    print("\n" + "=" * 60)
    print("📊 skill-advisor.db 缓存统计")
    print("=" * 60)

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

    print(f"\n  原始数据:")
    print(f"    ClawHub:       {stats['clawhub']:>6} 条 (有完整描述)")
    print(f"    skills.sh:     {stats['skills_sh']:>6} 条 (有名字+安装量)")
    print(f"    GitHub Topic:  {stats['github_topic']:>6} 条 (需Token)")
    print(f"    GitHub Code:   {stats['github_code']:>6} 条 (需Token)")
    print(f"    本地已安装:     {stats['local']:>6} 条")
    print(f"\n  去重合并后:")
    print(f"    唯一技能总数:   {stats['merged']:>6} 条")
    print(f"    有描述的:      {stats['with_desc']:>6} 条")

    # 文件大小
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / 1024 / 1024
        print(f"\n  数据库文件大小: {size_mb:.1f} MB")

    # Top 来源
    rows = conn.execute("""
        SELECT source, COUNT(*) FROM skills_merged GROUP BY source ORDER BY COUNT(*) DESC
    """).fetchall()
    print(f"\n  来源分布:")
    for src, cnt in rows:
        print(f"    {src:15s}: {cnt:>6} 条")

    # Top 质量
    rows = conn.execute("""
        SELECT name, quality_score FROM skills_merged
        WHERE description != '' ORDER BY quality_score DESC LIMIT 10
    """).fetchall()
    if rows:
        print(f"\n  Top 10 高质量技能:")
        for name, score in rows:
            print(f"    {score:>5.1f}  {name}")

    print("=" * 60)


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="skill-advisor 缓存生成器")
    parser.add_argument("--source", choices=["clawhub", "skills_sh", "github_topic", "github_code", "local", "merge", "all"], default="all")
    parser.add_argument("--github-token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--stats", action="store_true", help="显示统计后退出")
    parser.add_argument("--limit", type=int, default=100, help="ClawHub每页条数")
    parser.add_argument("--max-repos", type=int, default=500, help="每个GitHub Topic最多处理repo数")
    parser.add_argument("--resume", action="store_true", help="断点续传 (跳过多余已采集数据)")
    parser.add_argument("--vectors", action="store_true", help="合并后构建向量嵌入索引（需 sentence-transformers）")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="嵌入模型名 (默认: all-MiniLM-L6-v2)")
    parser.add_argument("--force", action="store_true", help="强制重建所有嵌入")
    parser.add_argument("--incremental", action="store_true", help="增量模式：不清空已有数据，只添加/更新")
    args = parser.parse_args()

    if args.stats:
        conn = sqlite3.connect(args.db)
        show_stats(conn)
        conn.close()
        return

    print("=" * 60)
    print("🚀 skill-advisor 缓存生成器 v1")
    print("=" * 60)
    print(f"数据库: {args.db}")
    print(f"GitHub Token: {'✅ 已配置' if args.github_token else '❌ 未配置(GitHub搜索将跳过)'}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 初始化数据库
    conn = init_database(Path(args.db))

    start_time = time.time()

    try:
        if args.source in ("clawhub", "all"):
            fetch_clawhub_all(conn, limit=args.limit)

        if args.source in ("skills_sh", "all"):
            fetch_skills_sh_all(conn)

        if args.source in ("github_topic", "all"):
            fetch_github_topics(conn, args.github_token)

        if args.source in ("github_code", "all"):
            fetch_github_code_search(conn, args.github_token)

        if args.source in ("local", "all"):
            scan_local_skills(conn)

        # 合并
        if args.source in ("merge", "all"):
            merge_all_sources(conn, incremental=args.incremental)

            # 可选：构建向量嵌入索引
            if args.vectors:
                print("\n[向量] 构建嵌入索引...")
                try:
                    sys.path.insert(0, str(SCRIPT_DIR))
                    from build_vectors import build_all
                    build_all(conn, model_name=args.model, force=args.force)
                except ImportError as e:
                    print(f"  ⚠️ 向量依赖未安装: {e}")
                    print("  提示: pip install -e '.[vector]'")

    except KeyboardInterrupt:
        print("\n\n⏸️ 用户中断, 数据已保存, 下次运行 --resume 继续")
        conn.commit()

    elapsed = time.time() - start_time
    print(f"\n⏱️ 耗时: {elapsed:.1f} 秒")

    # 显示统计
    show_stats(conn)

    # VACUUM (压缩)
    if args.source == "all":
        print("\n📦 压缩数据库...")
        conn.execute("VACUUM")
        if DB_PATH.exists():
            size_mb = DB_PATH.stat().st_size / 1024 / 1024
            print(f"  最终大小: {size_mb:.1f} MB")

    conn.close()
    print("\n✅ 缓存构建完成!")


if __name__ == "__main__":
    main()
