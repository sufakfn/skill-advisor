# skill-advisor 🧭

> 告诉 AI 你是谁，它精准推荐你需要的技能。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)](https://www.python.org/)
[![Skills](https://img.shields.io/badge/技能-16,600%2B-green.svg)](data/skill-advisor.db)

[English](README.md)

---

## 什么是 skill-advisor?

**skill-advisor** 是一个 AI 智能体技能推荐引擎。不需要你在成千上万技能里翻找，只需要告诉它你是谁/想做什么 — 它精准推荐最适合你的技能。

```
你: "我是中学数学老师"
skill-advisor 推荐:
  → unit-test (自动出卷批改)
  → pptx (做课件)
  → dataviz (成绩图表)
  → xlsx (学生档案)
  → proactive-agent (考试提醒)
  + 组合指南: "出卷 → 考试 → 分析成绩 → 记录薄弱点 → 讲评课件"
```

---

## 核心特性

- 🔍 **智能搜索** — 自然语言查询，中英文均支持 (基于 SQLite FTS5)
- 📦 **职业合集包** — 16 种身份场景精选包（教师/PM/设计师/HR/律师/医生等）
- 🌐 **16,800+ 技能** — 数据源: ClawHub / skills.sh / GitHub（持续增长）
- ⚡ **< 10ms 响应** — 本地 SQLite 缓存，离线可用
- 🔄 **在线兜底** — 本地未命中时自动搜索 skills.sh + ClawHub
- 🤝 **跨智能体** — 兼容 Claude Code、Cursor、Codex CLI、Gemini CLI 等任何支持 SKILL.md 的 agent

---

## 快速开始

### 方式一: pip 安装 (推荐)

```bash
pip install skill-advisor
```

```python
from skill_advisor import recommend

result = recommend("我是产品经理")
print(result["profession_pack"]["name"])
```

```bash
# 命令行
skill-advisor "股票分析"
skill-advisor "react前端"
skill-advisor --stats        # 数据库统计
```

### 方式二: 作为 Skill 安装 (终端用户)

```bash
cp -r skill-advisor ~/.claude/skills/          # Claude Code
cp -r skill-advisor ~/.cursor/skills/           # Cursor
cp -r skill-advisor ~/.codex/skills/            # Codex CLI
```

然后在对话中使用:
```
你: /skill-advisor "我想做个PPT"
```

### 方式三: 源码安装 (贡献者)

```bash
git clone https://github.com/skill-advisor/skill-advisor.git
cd skill-advisor
pip install -e ".[dev]"
pytest tests/ -v          # 运行测试
```

### 技术栈

- **搜索**: SQLite FTS5 (trigram 分词) + LIKE 中文兜底
- **数据**: 16,874+ 技能来自 6 个数据源
- **响应速度**: < 10ms
- **离线可用**: 本地 SQLite 缓存
- **跨智能体**: 兼容 Claude Code、Cursor、Codex CLI、Gemini CLI
- **Python**: 3.9+, 无重型依赖

---

## 架构图

```
用户输入
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│                   skill-advisor 引擎                     │
│                                                          │
│  第一层: 职业匹配                                        │
│    "数学老师" → 教师包 (8个技能 + 组合指南)               │
│                                                          │
│  第二层: 语义搜索 (SQLite FTS5)                          │
│    本地 16,800+ 技能 → < 10ms 响应                       │
│                                                          │
│  第三层: 在线兜底                                        │
│    skills.sh API + ClawHub API                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
    │
    ▼
分级推荐 (必装 / 建议 / 以后再装 / 最佳组合)
```

### 数据源

| 来源 | 数量 | 说明 |
|------|------|------|
| skills.sh | ~17,200 | 111 关键词扫描 |
| GitHub Code Search | ~3,200 | 直接搜索 SKILL.md 文件 |
| GitHub Topic | ~465 | 111 个 topic 关键词 Tree API 解析 |
| ClawHub | ~99 | 完整描述+标签+下载量 |
| Anthropic Marketplace | ~23 | 官方 Claude Code 插件/技能/智能体 |
| 本地已安装 | ~18 | 自动扫描 |
| **去重后总计** | **~16,874** | URL + 名称归一化去重后 |

---

## 项目结构

```
skill-advisor/
├── README.md / README.zh.md
├── LICENSE (MIT)
├── pyproject.toml
├── skill_advisor/          # Python 包
│   ├── __init__.py
│   ├── search.py           # SQLite 搜索引擎
│   ├── recommender.py      # 推荐引擎
│   └── data/
│       └── skill-advisor.db  # 预构建缓存 (26 MB)
├── tests/
│   └── test_search.py
└── scripts/
    └── build_cache.py      # 缓存构建器 (维护者用)
```

---

## 构建缓存

想要 rebuild 或扩展技能数据库？

```bash
# 全量构建（所有数据源）
python scripts/build_cache.py --github-token 你的GITHUB_TOKEN

# 只构建某个数据源
python scripts/build_cache.py --source clawhub
python scripts/build_cache.py --source skills_sh
python scripts/build_cache.py --source github_code --github-token xxx
python scripts/build_cache.py --source github_topic --github-token xxx

# 合并所有源
python scripts/build_cache.py --source merge

# 查看统计
python scripts/build_cache.py --stats
```

### 获取 GitHub Token

1. 打开 https://github.com/settings/tokens
2. Generate new token (classic)
3. 勾选 `public_repo` (只读)
4. 复制以 `ghp_` 开头的 token

---

## 添加职业包

编辑 `skill_advisor/recommender.py`，在 `PROFESSION_PACKS` 中添加:

```python
"data-scientist": {
    "name": "数据科学家包",
    "desc": "全流程数据科学工作流",
    "skills": [
        {"name": "pandas-pro", "reason": "数据处理核心工具", "required": True},
        {"name": "matplotlib-viz", "reason": "数据可视化"},
    ],
    "combo_guide": "pandas-pro 处理数据 → matplotlib-viz 出图",
},
```

---

## 路线图

- [ ] Forge — 从任何 API 文档自动生成技能
- [ ] Web UI — 浏览器仪表板
- [ ] 自动同步 — 每日增量更新 GitHub 新技能
- [ ] 社区贡献 — 通过 PR 提交技能
- [ ] 更多职业包 — 30+ 种身份场景

---

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing`)
5. 开启 Pull Request

---

## 许可证

[MIT](LICENSE) © 2026 skill-advisor contributors

---

## 致谢

- [ClawHub](https://clawhub.ai) — 技能注册中心
- [skills.sh](https://skills.sh) — 技能市场
- [xingkongliang/skills-manager](https://github.com/xingkongliang/skills-manager) — SQLite 存储模式
