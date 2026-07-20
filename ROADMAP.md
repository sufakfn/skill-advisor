# 🗺️ skill-advisor 开源路线图

> 版本: 1.0 · 更新日期: 2026-07-15 · 当前完成度: ~75%

---

## 总览

```
Phase 1 ─── Phase 2 ─────── Phase 3 ─────────── Phase 4
开源基本功    搜索质量+数据      生态建设            差异化护城河
(第1-2周)    (第3-6周)        (第7-12周)          (第13周+)
   ↓              ↓                ↓                   ↓
 修/补/通       数据+搜索         Web/社区           主动推荐/安全
```

| Phase | 周期 | 目标 | 关键指标 |
|-------|------|------|----------|
| Phase 1 | 第 1-2 周 | 开源基本功 — 可信、可跑、可贡献 | CI 绿灯、README 自洽、pip 可装 |
| Phase 2 | 第 3-6 周 | 搜索质量 — 描述覆盖 + 新数据源 | 描述覆盖率 1.8% → 60%+ |
| Phase 3 | 第 7-12 周 | 生态建设 — Web/自动同步/PyPI | PyPI 发布、GitHub Actions 自动同步 |
| Phase 4 | 第 13 周+ | 差异化 — 主动推荐 + 安全 + 多语言 | 与 SkillFinder 形成互补 |

---

## Phase 1: 开源基本功 (第 1-2 周)

> **目标**: 让人一上来就信任这个项目 — 文档自洽、测试能跑、pip 能装。

### Week 1 — 文档与配置修复

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 1.1 | 修复 `pyproject.toml` 占位符 | 🔴 P0 | 30min | 把 `your-username` 改成真实 GitHub 用户名/组织 | `pip install -e .` 后 metadata URLs 正确 |
| 1.2 | 统一 README 中不一致的数字 | 🔴 P0 | 1h | README.md / README.zh.md / SKILL.md 三处技能数、职业包数必须一致 | 三份文档数字完全一致 |
| 1.3 | 创建 `CONTRIBUTING.md` | 🔴 P0 | 2h | 包含: 行为准则、如何提 issue、PR 流程、开发环境 setup、代码风格 | 文件存在且内容完整 |
| 1.4 | 创建 `CHANGELOG.md` | 🟡 P1 | 1h | 按 Keep a Changelog 格式，从 v6.0.0 开始 | 文件存在 |
| 1.5 | 添加 `.github/PULL_REQUEST_TEMPLATE.md` | 🟡 P1 | 30min | PR 模板: 改动描述、测试、截图 | 文件存在 |
| 1.6 | 添加 `.github/ISSUE_TEMPLATE/bug_report.md` | 🟡 P1 | 30min | Bug 报告模板 | 文件存在 |
| 1.7 | 添加 `.github/ISSUE_TEMPLATE/feature_request.md` | 🟡 P1 | 30min | Feature 请求模板 | 文件存在 |

### Week 1 — 测试与 CI

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 1.8 | 安装 pytest 并跑通现有测试 | 🔴 P0 | 1h | `pip install pytest` → `pytest tests/ -v` 全绿 | 7/7 测试通过 |
| 1.9 | 补充搜索边界测试 | 🟡 P1 | 2h | 空字符串、特殊字符、超长查询、SQL 注入尝试、中英文混合 | 新增 10+ 测试用例 |
| 1.10 | 补充推荐引擎测试 | 🟡 P1 | 2h | 职业匹配边界、无匹配输入、全部已安装、空数据库降级 | 新增 8+ 测试用例 |
| 1.11 | 创建 `.github/workflows/ci.yml` | 🔴 P0 | 2h | 触发: push + PR; 步骤: checkout → setup-python → install → pytest → flake8 | CI 在 sample push 后绿灯 |
| 1.12 | 添加 `Makefile` / `tox.ini` | 🟠 P2 | 1h | `make test` / `make lint` / `make build` 一键操作 | 命令可用 |

### Week 2 — 安装体验与发布准备

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 1.13 | 验证 `pip install -e .` 本地安装 | 🔴 P0 | 1h | 干净 venv → pip install → `from skill_advisor import recommend` 可用 | import 成功 |
| 1.14 | 验证 CLI 入口 `skill-advisor` | 🔴 P0 | 1h | `skill-advisor "测试"` 能输出推荐 | 命令行返回 JSON |
| 1.15 | 补全 profession_packs.py 的 install_cmd | 🟡 P1 | 3h | 15 个职业包 × 5-8 技能，每个 install_cmd 必须是真实可执行的 `npx skills add` 命令 | 无空字符串 |
| 1.16 | 验证 `cp -r` 到 `~/.claude/skills/` 后可用 | 🟡 P1 | 1h | 作为 Skill 安装后，`/skill-advisor` 命令能触发 | 在 Claude Code 中能调用 |
| 1.17 | 添加 README badges | 🟡 P1 | 30min | License / Python / CI Status / PyPI (预留) / Skills 数量 | badges 显示正确 |
| 1.18 | 写第一份 GitHub Release 说明 | 🟡 P1 | 1h | v6.0.0 发布说明，包含功能列表、安装方式、Roadmap | Release 页面完整 |

### Phase 1 验收清单

- [ ] `pytest tests/` 全绿 (CI badge 显示 passing)
- [ ] `pip install -e .` 成功
- [ ] `skill-advisor "测试"` 输出正常
- [ ] README 数字三处一致
- [ ] CONTRIBUTING.md 存在
- [ ] GitHub Issue/PR 模板存在
- [ ] Release v6.0.0 已发布

---

## Phase 2: 搜索质量 + 数据 (第 3-6 周)

> **目标**: 把描述覆盖率从 1.8% 提到 60%+，让搜索结果真正可用。

### Week 3-4 — 数据补全

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 2.1 | 分析当前 DB 描述缺失分布 | 🔴 P0 | 2h | 按 source 分组统计: clawhub / skills_sh / github_code / github_topic 各有多少有描述 | 输出统计报告 |
| 2.2 | 编写描述补全脚本 `scripts/backfill_descriptions.py` | 🔴 P0 | 6h | 对有 urls 的技能，抓取 SKILL.md 第一段作为描述; 调用 GitHub API 获取 | 脚本可运行 |
| 2.3 | 运行描述补全 (ClawHub 源) | 🔴 P0 | 2h | ClawHub 数据有 description 字段，检查为何没入库 | ClawHub 源描述覆盖率 >80% |
| 2.4 | 运行描述补全 (GitHub Code 源) | 🔴 P0 | 4h | 通过 GitHub API 拉取 SKILL.md → 提取 frontmatter description | GitHub Code 源描述覆盖率 >50% |
| 2.5 | 运行描述补全 (skills.sh 源) | 🟡 P1 | 3h | skills.sh 数据原本无描述，通过 urls 反查 | skills.sh 源描述覆盖率 >30% |
| 2.6 | 重新构建 FTS5 索引 | 🔴 P0 | 1h | 描述补全后 rebuild FTS5 索引 | 搜索命中质量提升 |
| 2.7 | 验证搜索质量提升 | 🔴 P0 | 2h | 用 20 个测试查询对比补全前后搜索结果相关性 | 人工评估相关性提升 |

### Week 4-5 — 新增数据源

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 2.8 | 接入 Anthropic 官方 marketplace | 🔴 P0 | 6h | 爬取 `anthropics/awesome-claude-code-skills` 或官方 API | +28,000 技能 |
| 2.9 | 接入 SkillHub 源 | 🟡 P1 | 4h | SkillFinder 使用的 SkillHub (12,448 条) | +12,000 技能 |
| 2.10 | 接入 GitHub Topics 源增强 | 🟡 P1 | 3h | 扩展 topic 关键词列表 | +5,000 技能 |
| 2.11 | 多源去重策略优化 | 🔴 P0 | 3h | 按 repo URL 归一化去重; 同名不同源合并保留最高质量 | 去重后总量统计 |
| 2.12 | 更新 build_cache.py 支持新源 | 🔴 P0 | 2h | 新增 `--source anthropic_marketplace` 等参数 | 参数可用 |

### Week 5-6 — 搜索质量评估体系

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 2.13 | 建立搜索质量评估集 | 🟡 P1 | 4h | 50 个中英文查询 + 期望命中技能 (ground truth) | `tests/eval_queries.json` |
| 2.14 | 实现评估脚本 `scripts/eval_search.py` | 🟡 P1 | 3h | 计算 Precision@5 / Recall@10 / MRR | 输出评估报告 |
| 2.15 | 搜索相关性调优 | 🟡 P1 | 4h | 调整 FTS5 分词器 / LIKE 权重 / quality_score 算法 | Precision@5 > 0.6 |
| 2.16 | 中文分词增强 | 🟠 P2 | 4h | 集成 jieba 分词替代双词 LIKE | 中文搜索 MRR 提升 |
| 2.17 | 更新 README 数据源表 | 🟡 P1 | 1h | 反映新数据源和去重后总量 | 数据准确 |

### Phase 2 验收清单

- [ ] 描述覆盖率 ≥ 60%
- [ ] 总技能量 ≥ 30,000
- [ ] 搜索评估 Precision@5 ≥ 0.6
- [ ] 20 个测试查询全部返回合理结果
- [ ] build_cache.py 支持全部 5+ 数据源
- [ ] 评估脚本可复现

---

## Phase 3: 生态建设 (第 7-12 周)

> **目标**: 从"能用"到"好用" — Web UI、自动同步、PyPI 发布、社区贡献。

### Week 7-8 — PyPI 发布

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 3.1 | 注册 PyPI 账号 + 配置 API token | 🔴 P0 | 1h | pypi.org 注册 | 账号就绪 |
| 3.2 | 完善 `pyproject.toml` 元数据 | 🔴 P0 | 1h | classifiers / keywords / project URLs 完整 | `pip install skill-advisor` 后 info 正确 |
| 3.3 | 构建 sdist + wheel | 🔴 P0 | 1h | `python -m build` | dist/ 产物存在 |
| 3.4 | 上传到 TestPyPI 验证 | 🔴 P0 | 2h | `twine upload --repository testpypi` → 从 TestPyPI 安装测试 | TestPyPI 安装成功 |
| 3.5 | 正式发布到 PyPI | 🔴 P0 | 1h | `twine upload` | `pip install skill-advisor` 可用 |
| 3.6 | 更新 README 安装说明 | 🟡 P1 | 30min | 添加 `pip install skill-advisor` 方式 | 说明清晰 |

### Week 8-9 — 自动同步 CI

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 3.7 | 创建 `.github/workflows/sync_skills.yml` | 🔴 P0 | 4h | 每周一 02:00 UTC 自动跑 build_cache.py → 提交 DB 更新 | workflow 文件存在 |
| 3.8 | 配置 GitHub Token 到 Secrets | 🔴 P0 | 30min | `GH_TOKEN` 和 `CLAWHUB_TOKEN` (如需) | Secret 配置完成 |
| 3.9 | 测试 CI 手动触发 | 🔴 P0 | 1h | `workflow_dispatch` 触发 → 检查 DB 是否更新 | CI 成功运行 |
| 3.10 | 添加 DB 更新 changelog 自动生成 | 🟡 P1 | 2h | CI 自动统计新增/删除技能数 → 写入 CHANGELOG | 自动 changelog |
| 3.11 | 添加 CI 通知 (可选: Slack/飞书) | 🟠 P2 | 2h | 同步完成后通知 | 通知可达 |

### Week 9-10 — Web UI (浏览器仪表板)

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 3.12 | 技术选型: FastAPI + htmx / React | 🔴 P0 | 2h | 决定栈，考虑维护成本 | 决策文档 |
| 3.13 | 创建 `web/` 目录 + 基础 FastAPI 应用 | 🔴 P0 | 4h | `web/app.py` — 搜索 API + 静态文件服务 | `uvicorn web.app:app` 启动 |
| 3.14 | 实现搜索页面 | 🔴 P0 | 6h | 输入框 → 实时搜索 → 结果卡片列表 | 页面可用 |
| 3.15 | 实现职业包页面 | 🟡 P1 | 4h | 15 个职业包卡片 → 点击展开详情 | 页面可用 |
| 3.16 | 实现技能详情页 | 🟡 P1 | 3h | 技能名 + 描述 + 安装命令 + 来源链接 | 页面可用 |
| 3.17 | 添加暗色主题 | 🟠 P2 | 2h | CSS 变量切换 | 暗色/亮色可用 |
| 3.18 | Web UI 部署到 Vercel/Cloudflare Pages | 🟡 P1 | 3h | 自动部署 | 公网可访问 |

### Week 11-12 — 社区贡献体系

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 3.19 | 创建 `docs/` 目录 + 文档站 | 🟡 P1 | 4h | 用 MkDocs 或 VitePress 搭建文档站 | 文档站可浏览 |
| 3.20 | 编写"如何添加新职业包"教程 | 🟡 P1 | 2h | 图文教程 | 教程完整 |
| 3.21 | 编写"如何添加新数据源"教程 | 🟡 P1 | 2h | 图文教程 | 教程完整 |
| 3.22 | 创建 `SKILLS.md` 社区技能提交规范 | 🟡 P1 | 2h | 定义提交格式: 名称/描述/安装命令/来源 | 规范文档 |
| 3.23 | 添加 GitHub Discussion | 🟠 P2 | 30min | 启用仓库 Discussion | Discussion 可用 |
| 3.24 | 写一篇项目技术博客 | 🟠 P2 | 4h | 发在项目 Wiki 或外部平台 | 博客发布 |
| 3.25 | 联系 SkillFinder/skills-manager 互链 | 🟠 P2 | 1h | 发 issue/PR 请求互相推荐 | 至少 1 个回复 |

### Phase 3 验收清单

- [ ] `pip install skill-advisor` 从 PyPI 安装成功
- [ ] GitHub Actions 每周自动同步运行正常
- [ ] Web UI 公网可访问
- [ ] 文档站可浏览
- [ ] 至少 1 个外部社区贡献 (issue/PR)

---

## Phase 4: 差异化护城河 (第 13 周+)

> **目标**: 建立 SkillFinder 做不了的能力 — 中文深度、主动推荐、安全。

### Week 13-14 — 主动推荐增强 (Context Advisor 2.0)

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 4.1 | 分析 SkillForge Context Advisor 设计 | 🟡 P1 | 2h | 研究其 4 级强度 (off/quiet/balanced/active) | 分析笔记 |
| 4.2 | 实现推荐强度配置 | 🟡 P1 | 3h | `~/.skill-advisor/config.toml` 中配置 `advisor_level` | 配置生效 |
| 4.3 | 实现"不打扰"智能判断 | 🟡 P1 | 4h | 基于: 上次推荐时间、用户是否已安装、项目阶段是否变化 | 1h 内不重复推荐 |
| 4.4 | 集成到 Claude Code hooks | 🟡 P1 | 3h | `PostToolUse` hook → 检测阶段变化 → 主动推荐 | hook 可用 |
| 4.5 | 添加推荐反馈机制 | 🟠 P2 | 2h | 用户可 dismiss / "已安装" / "不需要" → 学习偏好 | 反馈记录到本地 |

### Week 14-15 — 安全防护层

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 4.6 | 研究 SkillFinder VirusTotal 集成方式 | 🟡 P1 | 2h | 看其 `--safety_only` 实现 | 技术方案 |
| 4.7 | 实现技能安全扫描脚本 | 🟡 P1 | 6h | 对 SKILL.md 做静态分析: 检测可疑 URL / 危险命令 / 权限申请 | 脚本可用 |
| 4.8 | 在搜索结果中标记安全状态 | 🟡 P1 | 2h | 安全扫描通过 ✅ / 未扫描 ⚠️ / 可疑 ❌ | UI 显示标记 |
| 4.9 | 添加安装前确认提示 | 🟡 P1 | 2h | 安装非官方源技能时二次确认 | 提示出现 |

### Week 15-16 — 多语言 + 扩展

| # | 任务 | 优先级 | 预估 | 详细 | 验收标准 |
|---|------|--------|------|------|----------|
| 4.10 | 提取所有硬编码中文 → i18n | 🟠 P2 | 4h | 用 `gettext` 或 `babel` 重构 | 中文提取完成 |
| 4.11 | 添加日语支持 | 🟠 P2 | 3h | ja 翻译 | 日语可用 |
| 4.12 | 添加韩语支持 | 🟠 P2 | 3h | ko 翻译 | 韩语可用 |
| 4.13 | 运行时语言切换 | 🟠 P2 | 2h | `Accept-Language` header / 命令行 `--lang` | 切换生效 |

### Week 16+ — 长期探索

| # | 任务 | 优先级 | 预估 | 详细 |
|---|------|--------|------|------|
| 4.14 | 向量语义搜索 (可选) | 🟠 P2 | 8h | 对高热度技能做嵌入，渐进引入 FAISS |
| 4.15 | 用户画像学习 | 🟠 P2 | 6h | 基于安装历史个性化推荐 |
| 4.16 | 技能组合自动发现 | 🔵 P3 | 8h | 分析用户已装技能组合 → 推荐常见搭配 |
| 4.17 | 与 IDE 深度集成 (VSCode 扩展) | 🔵 P3 | 12h | VSCode 内直接搜索安装 |

### Phase 4 验收清单

- [ ] Context Advisor 主动推荐可用
- [ ] 安全扫描覆盖 Top 1000 技能
- [ ] 至少 3 种语言支持
- [ ] 与 SkillFinder 形成明确差异化

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| GitHub API 限速 (5000次/小时) | 高 | Phase 2 数据爬取慢 | 用 Token + 分布式爬取 + 断点续传 |
| skills.sh / ClawHub API 变更 | 中 | 在线兜底失效 | 抽象数据源层，快速适配 |
| 描述补全质量差 (LLM 生成) | 中 | 搜索结果噪声 | 人工抽检 + 置信度过滤 |
| PyPI 包名被抢注 | 低 | 发布受阻 | 尽早注册 + 备选名 `skill-advisor-cli` |
| 维护者精力有限 | 高 | Phase 3/4 延期 | 优先保 Phase 1-2，后续靠社区 |

---

## 里程碑总览

```
2026-07-15  ████░░░░░░░░░░░░  当前 (v6.0.0, 16,630 技能)
             ↓ Phase 1 (2周)
2026-07-29  █████░░░░░░░░░░░  v6.1.0 — CI 绿灯, PyPI 就绪, 文档自洽
             ↓ Phase 2 (4周)
2026-08-26  ████████░░░░░░░░  v7.0.0 — 30,000+ 技能, 描述覆盖 60%+
             ↓ Phase 3 (6周)
2026-10-07  ██████████░░░░░░  v8.0.0 — PyPI 发布, Web UI, 自动同步
             ↓ Phase 4 (4周)
2026-11-04  ████████████░░░░  v9.0.0 — 主动推荐, 安全扫描, 多语言
             ↓ 持续
2027+       ████████████████  社区驱动增长
```

---

## 如何参与

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

- 🐛 提 Bug → [Issue](https://github.com/your-username/skill-advisor/issues)
- 💡 提 Feature → [Issue](https://github.com/your-username/skill-advisor/issues)
- 🔧 提 PR → [Pull Request](https://github.com/your-username/skill-advisor/pulls)
- 💬 讨论 → [Discussion](https://github.com/your-username/skill-advisor/discussions)
