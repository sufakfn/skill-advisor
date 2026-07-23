# skill-advisor 🧭

> Tell AI who you are, it knows exactly what skills you need.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)
[![Skills](https://img.shields.io/badge/skills-16,600%2B-green.svg)](data/skill-advisor.db)
[![CI](https://github.com/skill-advisor/skill-advisor/workflows/CI/badge.svg)](https://github.com/skill-advisor/skill-advisor/actions)
[![PyPI](https://img.shields.io/pypi/v/skill-advisor.svg)](https://pypi.org/project/skill-advisor/)
[![Contributors](https://img.shields.io/github/contributors/skill-advisor/skill-advisor.svg)](https://github.com/skill-advisor/skill-advisor/graphs/contributors)

[中文文档](README.zh.md)

---

## What is skill-advisor?

**skill-advisor** is a smart skill recommendation engine for AI coding agents. Instead of browsing through thousands of skills, just tell it who you are or what you want to do — it recommends exactly the right skills for you.

```
You: "I'm a middle school math teacher"
skill-advisor: → unit-test (auto-generate exams)
               → pptx (create courseware)
               → dataviz (grade charts)
               → xlsx (student records)
               → proactive-agent (exam reminders)
               + combo guide: "Generate exam → Analyze grades → Track weak points → Create review slides"
```

---

## Features

- 🔍 **Smart Search** — Natural language query in English or Chinese (powered by SQLite FTS5)
- 📦 **Profession Packs** — 16 curated packs for teachers, PMs, designers, HR, lawyers, doctors, etc.
- 🌐 **16,800+ Skills** — From ClawHub, skills.sh, GitHub (continuously growing)
- ⚡ **< 10ms Response** — Local SQLite cache, works offline
- 🔄 **Online Fallback** — Auto-searches skills.sh + ClawHub when local cache misses
- 🤖 **Cross-Agent** — Works with Claude Code, Cursor, Codex CLI, Gemini CLI, and any SKILL.md-compatible agent

---

## Quick Start

### Option 1: Install via pip (recommended)

```bash
pip install skill-advisor
```

```python
from skill_advisor import recommend

result = recommend("I'm a product manager")
print(result["profession_pack"]["name"])
```

```bash
# CLI usage
skill-advisor "stock analysis"
skill-advisor "react frontend"
skill-advisor --stats        # database statistics
```

### Option 2: Install as a Skill (for end users)

```bash
# Clone to your agent's skills directory
cp -r skill-advisor ~/.claude/skills/          # Claude Code
cp -r skill-advisor ~/.cursor/skills/           # Cursor
cp -r skill-advisor ~/.codex/skills/            # Codex CLI
```

Then use it in any conversation:
```
You: /skill-advisor "I want to make a presentation"
```

### Option 3: Install from source (for contributors)

```bash
git clone https://github.com/skill-advisor/skill-advisor.git
cd skill-advisor
pip install -e ".[dev]"
pytest tests/ -v          # run tests
```

### Tech Stack

- **Search**: SQLite FTS5 (trigram tokenizer) + LIKE fallback for Chinese
- **Data**: 16,874+ skills from 6 sources (ClawHub, skills.sh, GitHub, Anthropic, local)
- **Response time**: < 10ms per query
- **Offline capable**: local SQLite cache, no internet required for search
- **Cross-agent**: works with Claude Code, Cursor, Codex CLI, Gemini CLI, and any SKILL.md-compatible agent
- **Python**: 3.9+, no heavy dependencies (only `jieba` for enhanced Chinese search)

---

## Architecture

```
User Input
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│                   skill-advisor Engine                    │
│                                                          │
│  Layer 1: Profession Matching                            │
│    "Math teacher" → teacher pack (8 skills + guide)      │
│                                                          │
│  Layer 2: Semantic Search (SQLite FTS5)                  │
│    Local 16,800+ skills → < 10ms response                │
│                                                          │
│  Layer 3: Online Fallback                                │
│    skills.sh API + ClawHub API                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
    │
    ▼
Ranked Recommendations (required / suggested / later / best combo)
```

### Data Sources

| Source | Count | Description |
|--------|-------|-------------|
| skills.sh | ~17,200 | Multi-keyword scan (111 keywords) |
| GitHub Code Search | ~3,200 | Direct `SKILL.md` file search |
| GitHub Topic | ~465 | Tree API parsing (111 topic keywords) |
| ClawHub | ~99 | Full descriptions + tags + downloads |
| Anthropic Marketplace | ~23 | Official Claude Code plugins/skills/agents |
| Local installed | ~18 | Auto-scanned |
| **Total (deduplicated)** | **~16,874** | After URL + name normalization |

---

## Project Structure

```
skill-advisor/
├── README.md / README.zh.md
├── LICENSE (MIT)
├── pyproject.toml
├── skill_advisor/          # Python package
│   ├── __init__.py
│   ├── search.py           # SQLite search engine
│   ├── recommender.py      # Recommendation engine
│   └── data/
│       └── skill-advisor.db  # Pre-built cache (26 MB)
├── tests/
│   └── test_search.py
└── scripts/
    └── build_cache.py      # Cache builder (for maintainers)
```

---

## Building the Cache

Want to rebuild or extend the skill database?

```bash
# Full build (all sources)
python scripts/build_cache.py --github-token YOUR_GITHUB_TOKEN

# Build specific sources
python scripts/build_cache.py --source clawhub
python scripts/build_cache.py --source skills_sh
python scripts/build_cache.py --source github_code --github-token xxx
python scripts/build_cache.py --source github_topic --github-token xxx

# Merge all sources
python scripts/build_cache.py --source merge

# View stats
python scripts/build_cache.py --stats
```

---

## Adding a New Profession Pack

Edit `skill_advisor/recommender.py` and add to `PROFESSION_PACKS`:

```python
"data-scientist": {
    "name": "Data Scientist Pack",
    "desc": "Full data science workflow",
    "skills": [
        {"name": "pandas-pro", "reason": "Data manipulation", "required": True},
        {"name": "matplotlib-viz", "reason": "Visualization"},
    ],
    "combo_guide": "Use pandas-pro for data → matplotlib-viz for charts",
},
```

---

## Roadmap

- [ ] Forge — Auto-generate skills from any API documentation
- [x] Web UI — Browser-based dashboard (basic available at /web)
- [ ] Auto-sync — Daily incremental updates from GitHub
- [ ] Community contributions — Submit skills via PR
- [ ] More profession packs — 30+ identities

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## License

[MIT](LICENSE) © 2026 skill-advisor contributors

---

## Special Thanks

- [ClawHub](https://clawhub.ai) — Skill registry
- [skills.sh](https://skills.sh) — Skill marketplace
- [xingkongliang/skills-manager](https://github.com/xingkongliang/skills-manager) — SQLite storage pattern
