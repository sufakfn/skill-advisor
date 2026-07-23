# 贡献指南

> 感谢你对 skill-advisor 的兴趣！本文档帮助你快速上手贡献。

---

## 📋 目录

- [行为准则](#行为准则)
- [如何提 Issue](#如何提-issue)
- [如何提 PR](#如何提-pr)
- [开发环境 Setup](#开发环境-setup)
- [代码风格](#代码风格)
- [项目结构](#项目结构)
- [测试](#测试)

---

## 行为准则

1. **友善** — 尊重每一位贡献者
2. **建设性** — 批评对事不对人
3. **开放** — 欢迎新人，耐心回答问题

---

## 如何提 Issue

### Bug 报告

使用 [Bug 模板](https://github.com/sufakfn/skill-advisor/issues/new?template=bug_report.md)，包含：

- 清晰的问题描述
- 复现步骤
- 期望行为 vs 实际行为
- 环境信息 (Python 版本、操作系统)

### Feature 请求

使用 [Feature 模板](https://github.com/sufakfn/skill-advisor/issues/new?template=feature_request.md)，包含：

- 功能描述
- 使用场景
- 可能的实现方案（可选）

---

## 如何提 PR

### 流程

1. **Fork** 本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m "Add your feature"`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 开启 **Pull Request** 到 `main` 分支

### PR 要求

- [ ] 描述清楚改动内容
- [ ] 关联相关 Issue (如有)
- [ ] 所有测试通过 (`pytest tests/ -v`)
- [ ] 代码符合风格规范
- [ ] 更新相关文档 (如有必要)

### Commit 信息规范

`<type>: <简短描述>`

type:
- `feat`     新功能
- `fix`      修复 Bug
- `docs`     文档更新
- `test`     测试相关
- `refactor` 重构
- `chore`    构建/工具变更

示例: `feat: 添加日语支持`

---

## 开发环境 Setup

### 前置要求

- Python >= 3.9
- Git

### 安装步骤

```bash
# 1. Fork 后 clone 自己的仓库
git clone https://github.com/YOUR_USERNAME/skill-advisor.git
cd skill-advisor

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scriptsctivate

# 3. 安装开发依赖
pip install -e ".[dev]"

# 4. 验证安装
python -c "from skill_advisor import recommend; print("OK")"

# 5. 跑测试
pytest tests/ -v
```

---

## 代码风格

- 遵循 **PEP 8**
- 行宽 100 字符
- 使用 4 空格缩进
- 函数和变量用 `snake_case`
- 类用 `PascalCase`
- 公共函数必须有 docstring

### Lint

```bash
pip install flake8
flake8 skill_advisor/ tests/ --max-line-length=100
```

---

## 项目结构

```
skill-advisor/
├── README.md / README.zh.md     # 文档
├── CONTRIBUTING.md              # 本文件
├── CHANGELOG.md                 # 变更日志
├── pyproject.toml               # 包配置
├── skill_advisor/               # Python 包
│   ├── __init__.py
│   ├── search.py                # SQLite 搜索引擎
│   └── recommender.py           # 推荐引擎
├── tests/                       # 测试
│   └── test_search.py
├── scripts/                     # 维护脚本
│   └── build_cache.py
└── data/
    └── skills.db                # 技能数据库
```

---

## 测试

```bash
# 跑全部测试
pytest tests/ -v

# 跑单个测试文件
pytest tests/test_search.py -v

# 跑单个测试
pytest tests/test_search.py::TestSearch::test_search_english -v

# 查看覆盖率
pip install pytest-cov
pytest tests/ --cov=skill_advisor --cov-report=term-missing
```

---

## 常见问题

**Q: 如何添加新的职业包？**
A: 编辑 `skill_advisor/recommender.py` 中的 `PROFESSION_PACKS` 字典。

**Q: 如何添加新的数据源？**
A: 编辑 `scripts/build_cache.py`，新增 `--source` 参数支持。

**Q: 数据库如何更新？**
A: 运行 `python scripts/build_cache.py --github-token YOUR_TOKEN`

---

## 联系

- 💬 讨论 → [GitHub Discussion](https://github.com/sufakfn/skill-advisor/discussions)
- 🐛 Bug → [Issue](https://github.com/sufakfn/skill-advisor/issues)

感谢你的贡献！🎉
