# 变更日志 (Changelog)

## [auto] 2026-07-16 - DB Sync

- Total skills: 16874
- With description: 3065 (18.2%)


本项目的所有重要变更都会记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 新增
- 修复 `pyproject.toml` 占位符 (`your-username` → `skill-advisor`)
- 统一 README / SKILL.md 中的技能数量 (16,600+) 和职业包数量 (16)
- 添加 `CONTRIBUTING.md` 贡献指南
- 添加 `CHANGELOG.md` 变更日志
- 添加 GitHub Issue/PR 模板
- 添加搜索边界测试和推荐引擎测试
- 添加 GitHub Actions CI workflow
- 添加 `Makefile` 一键操作

---

## [6.0.0] - 2026-07-15

### 新增
- 🔍 **语义搜索** — 自然语言描述 → 精准匹配技能（基于 SQLite FTS5）
- 🧠 **Context Advisor** — 分析项目上下文，主动推荐合适的技能
- 📦 **职业合集包** — 16 个热门职业一键安装全套技能
- 🌐 **16,600+ 技能** — 数据源: ClawHub / skills.sh / GitHub
- ⚡ **< 10ms 响应** — 本地 SQLite 缓存，离线可用
- 🔄 **在线兜底** — 本地未命中时自动搜索 skills.sh + ClawHub
- 🤝 **跨智能体** — 兼容 Claude Code、Cursor、Codex CLI、Gemini CLI

### 数据源
| 来源 | 数量 |
|------|------|
| skills.sh | ~13,700 |
| GitHub Code Search | ~2,300 |
| GitHub Topic | ~150 |
| ClawHub | ~45 |
| 本地已安装 | ~12 |
| **去重后总计** | **~16,630** |

### 职业合集包 (16 个)
teacher / product-manager / content-creator / designer / hr / finance / sales / lawyer / doctor / student / investor / ecommerce / frontend-dev / backend-dev / writer / job-seeker

---

[Unreleased]: https://github.com/skill-advisor/skill-advisor/compare/v6.0.0...HEAD
[6.0.0]: https://github.com/skill-advisor/skill-advisor/releases/tag/v6.0.0
