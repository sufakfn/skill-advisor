# v6.0.0 — Initial Release

> Release Date: 2026-07-15
> License: MIT

## 🎉 首个开源正式版

skill-advisor 是一个 AI 智能体技能推荐引擎。告诉它你是谁或你想做什么，它从 16,600+ 技能中精准推荐最适合你的。

---

## ✨ 核心功能

### 🔍 智能搜索
- 自然语言查询，中英文均支持
- 基于 SQLite FTS5 全文检索，< 10ms 响应
- 中文分词增强（双词 LIKE 补偿）

### 📦 职业合集包
- 16 个热门职业一键安装（教师/PM/设计师/HR/律师/医生/学生/销售/电商/前端/后端/写作/求职/投资人/自媒体/会计）
- 每个包含 5-8 个核心技能 + 组合使用指南
- 安装命令已验证真实可执行

### 🧠 多模式推荐
- **语义搜索**: "做个演示" 也能命中 PPT 技能
- **Context Advisor**: 分析项目技术栈主动推荐
- **职业合集**: 一键匹配整套工作流
- **在线兜底**: 本地未命中时搜索 skills.sh + ClawHub

---

## 📊 数据规模

| 来源 | 数量 |
|------|------|
| skills.sh | ~13,700 |
| GitHub Code Search | ~2,300 |
| GitHub Topic | ~150 |
| ClawHub | ~45 |
| 本地已安装 | ~12 |
| **去重后总计** | **~16,630** |

---

## 🚀 快速开始

### 作为 Skill 安装（推荐终端用户）

```bash
cp -r skill-advisor ~/.claude/skills/
```

然后在 Claude Code 中使用:
```
/skill-advisor "我是中学数学老师"
```

### 作为 Python 包安装（开发者）

```bash
pip install skill-advisor
```

```python
from skill_advisor import recommend
result = recommend("我是产品经理")
print(result["profession_pack"]["name"])
```

### 命令行

```bash
skill-advisor "股票分析"
skill-advisor --stats
```

---

## 🧪 测试

```bash
pytest tests/ -v
```

- 8 个基础测试 ✅
- 22 个边界测试 ✅
- **总计: 30/30 通过**

---

## 📋 项目结构

```
skill-advisor/
├── README.md / README.zh.md
├── CONTRIBUTING.md              # 新增：贡献指南
├── CHANGELOG.md                 # 新增：变更日志
├── LICENSE (MIT)
├── pyproject.toml               # 修复：占位符替换
├── Makefile                     # 新增：一键操作
├── .github/
│   ├── workflows/ci.yml         # 新增：CI
│   ├── PULL_REQUEST_TEMPLATE.md # 新增
│   └── ISSUE_TEMPLATE/          # 新增：Bug + Feature 模板
├── skill_advisor/
│   ├── __init__.py
│   ├── search.py                # 搜索引擎
│   └── recommender.py           # 推荐引擎 + CLI main()
├── scripts/
│   ├── profession_packs.py      # 职业包管理
│   └── build_cache.py           # 缓存构建
├── tests/
│   ├── test_search.py           # 基础测试
│   └── test_search_enhanced.py  # 新增：边界测试
└── data/
    └── skills.db                # 26 MB 预处理缓存
```

---

## 🐛 Bug 修复

- 修复 `recommender.py` 中 `description` 为 `NULL` 时崩溃的问题
- 修复 `pyproject.toml` 中 `your-username` 占位符
- 添加 CLI `main()` 入口函数（解决 `skill-advisor` 命令不可用的问题）

---

## 📝 文档

- README / README.zh.md / SKILL.md 关键数字已统一（16,600+ 技能 / 16 个职业包 / v6.0.0）
- 英文 README 面向国际用户，中文 README 面向中国大陆用户

---

## 🗺️ Roadmap

- [ ] Phase 1 ✅ — 开源基本功 (本期)
- [ ] Phase 2 — 搜索质量 + 描述补全 (第 3-6 周)
- [ ] Phase 3 — PyPI + Web UI + 自动同步 (第 7-12 周)
- [ ] Phase 4 — 主动推荐 + 安全扫描 (第 13 周+)

详见 [ROADMAP.md](ROADMAP.md)

---

## 🤝 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 License

[MIT](LICENSE) © 2026 skill-advisor contributors
