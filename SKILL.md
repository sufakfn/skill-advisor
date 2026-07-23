---
name: "skill-advisor（技能顾问）— 语义搜索+主动推荐+职业包,智能匹配16,600+技能"
description: "当用户说'推荐技能'、'我要做XXX'、'需要什么skill'、'有什么好用的'、'我是XXX给我推荐'、'帮我选技能'、'安装技能包'时使用。"
---

# 技能顾问（skill-advisor）v6.0.0

## 功能

根据用户的**身份、职业、场景或具体需求**，从 16,600+ 技能中智能推荐，按4个模块输出。

**v5.1 新增三大能力：**
1. 🔍 **语义搜索** —— 自然语言描述 → 精准匹配技能（"做个演示" 也能命中 PPT 技能）
2. 🧠 **Context Advisor** —— 分析项目上下文，主动推荐合适的技能
3. 📦 **职业合集包** —— 16 个热门职业一键安装全套技能（教师/PM/设计师/HR/销售/会计/律师/医生/学生/投资人/电商/前端/后端/写作/求职）

> **大白话：** 你告诉我你是谁/你想做什么/你在写什么代码，我帮你挑最合适的技能，
> 分"必装、建议、以后、最佳组合"四个模块清晰展示。

---

## ⭐ 核心推荐流程（Claude 主导）

### 第一步：理解用户场景

收到用户请求后，**先判断用户属于哪种类型**：

| 用户类型 | 判断依据 | 处理方式 |
|----------|----------|----------|
| **职业身份型** | 说"我是XX老师/HR/销售/医生..." | → 查 `scenarios.md` 场景映射表 |
| **具体需求型** | 说"我想做XX/帮我出试卷/做个PPT..." | → 运行语义搜索匹配 |
| **项目开发型** | 说"我的项目要加XX功能..." | → 按项目技术栈匹配 |
| **模糊/纯好奇** | 说"有什么好用的/推荐一下" | → 问 1-2 个澄清问题 |

### 第二步：选择搜索模式

**根据用户类型选择最佳搜索策略：**

| 场景 | 搜索模式 | 脚本 | 优势 |
|------|----------|------|------|
| 用户说了模糊需求（"做个演示"） | **语义搜索** | `python scripts/semantic_search.py "做个演示"` | 同义词扩展 + FTS5，无需向量数据库 |
| 用户在项目中（有 package.json） | **Context Advisor** | `python scripts/advisor.py` | 感知项目技术栈和阶段，主动推荐 |
| 用户说了职业身份（"我是老师"） | **职业合集包** | `python scripts/profession_packs.py --search 老师` | 一键推荐整套技能 |
| 混合需求 | **组合搜索** | 先 advisor 再 semantic_search | 最精准 |

### 第三步：运行脚本获取数据

```bash
# === 模式1：语义搜索（默认推荐） ===
# 用户说模糊需求时优先使用
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/semantic_search.py "做个汇报用的幻灯片"
# 返回：按置信度排序的技能列表 + 扩展后的同义词

# === 模式2：Context Advisor ===
# 分析项目上下文，感知技术栈和开发阶段
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/advisor.py
# 带用户描述：
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/advisor.py "刚加了支付功能"
# 只返回最关键的3个推荐：
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/advisor.py --check

# === 模式3：职业合集包 ===
# 列出所有合集包：
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/profession_packs.py --list
# 搜索适合的包：
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/profession_packs.py --search 视频
# 查看教师包详情：
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/profession_packs.py --show teacher
# 生成安装计划：
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/profession_packs.py --install teacher

# === 模式4：统一入口（自动路由） ===
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/skill_advisor_v2.py . "我想做个PPT" --mode semantic
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/skill_advisor_v2.py . --mode advisor
python ~/.claude/skills/skill-advisor-skill-recommender/scripts/skill_advisor_v2.py . "我是老师" --mode pack
```

### 第四步：Claude 智能映射

拿到脚本输出的 JSON 后：

1. **如果 `mode` 是 `semantic_search`** → 取 `results` 前5个，结合 `expanded_terms` 理解为什么命中
2. **如果 `mode` 是 `context_advisor`** → 参考 `project_context`（技术栈+阶段）和 `message` 生成推荐
3. **如果 `mode` 是 `profession_pack`** → 直接使用 `matched_packs` 的职业包组合
4. **如果匹配结果很差** → Claude 忽略脚本，自行根据 `scenarios.md` 和用户描述做推荐
5. **无论哪种模式** → Claude 都需要结合 `installed` 字段标记已安装状态

### 第五步：格式化输出

按下方格式模块输出最终推荐。

---

## 输出格式（固定顺序）

按以下4个模块从上到下输出，每个模块独立展示：

### 1️⃣ 🔴 必装

**直接服务核心职能的技能。** 没有这些，工作无法开展。

**格式：表格**

| 已装 | 技能 | 能干什么 |
|:---:|------|----------|
| ✅/⬜ | `英文名（中文名）` | 一句话核心能力 |

**说明：**
- ✅ = 已安装（技能目录存在于 `~/.claude/skills/`）
- ⬜ = 未安装
- 最多推荐 5-8 个技能
- 技能名格式：`英文名` + `（中文名）` + ` — 简要说明`

---

### 2️⃣ 🟡 建议安装

**提升工作效率的技能。** 有了这些如虎添翼，但不是必需品。

| 已装 | 技能 | 能干什么 |
|:---:|------|----------| 
| ✅/⬜ | `英文名（中文名）` | 一句话核心能力 |

---

### 3️⃣ 🟢 以后再装

**现阶段用不上的技能。** 等场景成熟时再进行安装。

| 已装 | 技能 | 什么时候用 |
|:---:|------|-----------|
| ✅/⬜ | `英文名（中文名）` | 场景说明 |

---

### 4️⃣ ⭐ 最佳组合

**3-5个核心技能的组合推荐。** 相互配合，覆盖主要工作职能。

**⚠️ 最佳组合的重点：**
- 表格上方必须有一段详细理由（2-3句话），解释为什么选这几个
- 说明这些技能如何配合使用、覆盖哪些职能、为什么这样组合
- 不能只列技能不解释

**输出模板：**
```
⭐ 最佳组合 — 覆盖职能：XXX、XXX、XXX

（这里是一段详细理由，2-3句话。解释为什么选这几个技能，
它们如何配合使用，覆盖了哪些核心职能，为什么这样组合最
优。）

| 已装 | 技能 | 入选理由 |
|:---:|------|----------|
| ✅ | `英文名（中文名）` | 具体在组合中的角色 |
| ⬜ | `英文名（中文名）` | 具体在组合中的角色 |
```

---

## 完整输出示例

### 🎯 示例1：语义搜索（模糊需求）

> 用户："我想做个演示用的东西"

**语义搜索命中：** pptx（幻灯片/演示/汇报）、canvas-design（视觉设计）

#### 🔴 必装

| 已装 | 技能 | 能干什么 |
|:---:|------|----------|
| ✅ | **pptx（PPT制作）** | 创建/编辑演示文稿、幻灯片、课件 |
| ⬜ | **canvas-design（视觉设计）** | 设计视觉作品、海报、封面 |

#### 🟡 建议安装

| 已装 | 技能 | 能干什么 |
|:---:|------|----------|
| ⬜ | **theme-factory（主题样式）** | 给演示套用专业主题 |
| ✅ | **dataviz（数据可视化）** | 往PPT里加图表 |

#### 🟢 以后再装

| 已装 | 技能 | 什么时候用 |
|:---:|------|-----------|
| ⬜ | **remark（Markdown演示）** | 喜欢用 Markdown 做演示时 |

#### ⭐ 最佳组合 — 覆盖职能：演示制作、视觉设计、数据呈现

推荐这3个技能组合使用，覆盖从"内容准备→视觉设计→演示输出"的完整工作流：pptx 负责核心幻灯片制作，dataviz 把数据变成图表放进幻灯片，theme-factory 一键套用专业外观。三个技能配合，制作高颜值演示文稿。

| 已装 | 技能 | 入选理由 |
|:---:|------|----------|
| ✅ | pptx（PPT制作） | 核心：创建和编辑演示文稿 |
| ⬜ | dataviz（数据可视化） | 为演示添加图表 |
| ⬜ | theme-factory（主题样式） | 一键美化外观 |

---

### 🎯 示例2：职业合集包

> 用户："我是中学数学老师，推荐一下"

#### 📦 🏫 教师全能包

**适合人群：** 中小学教师、大学老师、培训机构讲师
**简介：** 把 AI 变成你的教学助手 —— 出卷、批改、课件、家校沟通全包

| 状态 | 技能 | 角色 | 说明 |
|:---:|------|------|------|
| ✅ | unit-test（单元测试专家） | 🔴必装 | 核心：自动出卷、批改、生成成绩报告 |
| ⬜ | pptx（PPT制作） | 🔴必装 | 做课件/说课PPT |
| ⬜ | dataviz（数据可视化） | 🟡建议 | 成绩图表、各题正确率分析 |
| ✅ | proactive-agent（主动预判AI） | 🟡建议 | 定时提醒考试/家长会 |
| ⬜ | agent-memory（AI记忆系统） | 🟡建议 | 记录学生薄弱知识点 |
| ⬜ | xlsx（Excel表格） | 🟡建议 | 成绩汇总表、学生档案管理 |

**组合使用指南：**
先用 unit-test 出卷 → 考完用 xlsx 和 dataviz 做成绩分析 → 用 agent-memory 记录薄弱点 → 用 pptx 做讲评课件 → 用 proactive-agent 定时提醒下次考试。一个完整的「考试→分析→补课」闭环。

---

### 🎯 示例3：Context Advisor

> 用户："我在做一个Next.js项目"（package.json 里有 next + stripe）

**Context Advisor 感知：** 阶段=核心功能开发 | 技术栈=[Next.js, payment, auth]

#### 🔴 必装（基于技术栈）

| 已装 | 技能 | 能干什么 |
|:---:|------|----------|
| ⬜ | **next-best-practices（Next.js最佳实践）** | Next.js 官方编码规范 |
| ⬜ | **stripe-best-practices（支付集成）** | Stripe 支付安全集成 |

#### 🟡 建议（基于项目阶段）

| 已装 | 技能 | 能干什么 |
|:---:|------|----------|
| ⬜ | **sentry-sdk-setup（错误监控）** | 线上错误追踪 |
| ⬜ | **web-perf（性能审计）** | Core Web Vitals 优化 |

---

## 场景映射知识库

详见同目录下的 `scenarios.md` 文件。

> 当用户描述职业/身份时，先查 scenarios.md 中的对应场景，
> 找到该场景推荐的技能列表，再结合脚本输出的已安装状态，
> 生成最终推荐。

---

## 职业合集包清单（16 个）

| 包 | 图标 | 核心技能 | 适合人群 |
|----|------|----------|----------|
| teacher | 🏫 | unit-test + pptx + dataviz + proactive-agent | 教师 |
| product-manager | 📋 | product-manager-toolkit + deep-research + web-design-analyzer | 产品经理 |
| content-creator | 🎬 | wechat-hotspot + baoyu系列 + video-creation | 自媒体 |
| designer | 🎨 | canvas-design + frontend-design + web-design-analyzer | 设计师 |
| hr | 👥 | xlsx + docx + tailored-resume-generator | HR/人事 |
| finance | 💰 | xlsx + creating-financial-models + stock-analysis | 会计/财务 |
| sales | 📈 | sales-ai-assistant + xlsx + pptx | 销售 |
| lawyer | ⚖️ | contract-review + docx + deep-research | 律师/法务 |
| doctor | 🏥 | deep-research + agent-memory + xlsx | 医生 |
| student | 📚 | deep-research + anything-to-notebooklm + pptx | 学生 |
| investor | 📊 | stock-analysis + creating-financial-models + market-research | 投资人 |
| ecommerce | 🛒 | ecommerce-copywriter + product-marketing-copywriter + canvas-design | 电商卖家 |
| frontend-dev | 🖥️ | react-best-practices + frontend-design + webapp-testing | 前端开发者 |
| backend-dev | ⚙️ | postgres-best-practices + security-best-practices + webapp-testing | 后端开发者 |
| writer | ✍️ | content-research-writer + docx + humanizer | 写作创作者 |
| job-seeker | 🎯 | tailored-resume-generator + deep-research + pptx | 求职者 |

---

## 注意事项

1. **优先用语义搜索** —— 当用户说模糊需求时（"做个演示"），用 `semantic_search.py` 而非关键词匹配
2. **项目场景用 Advisor** —— 当用户有项目目录时，用 `advisor.py` 感知技术栈
3. **身份匹配用合集包** —— 当用户说"我是XX"时，用 `profession_packs.py` 匹配职业包
4. **脚本输出不对路时，不要硬用** —— Claude 应自行判断并覆盖
5. **始终检查已安装状态** —— 优先推荐已安装的技能
6. **中文名称优先** —— 面向非技术用户时，技能名后加中文解释
7. **大白话描述** —— 不要用技术术语，要用人话

---

## 数据源

| 来源 | 数量 | 获取方式 | 说明 |
|------|------|----------|------|
| **skills.sh** | ~17,200 | 111 关键词扫描 | 最大数据源，GitHub 技能市场 |
| **GitHub Code Search** | ~3,200 | 直接搜索 SKILL.md 文件 | 高质量技能（含 frontmatter） |
| **GitHub Topic** | ~465 | 111 个 topic 关键词 Tree API 解析 | 按主题分类的技能 |
| **ClawHub** | ~99 | ClawHub API 按下载量排序 | 热门精选技能 |
| **Anthropic Marketplace** | ~23 | GitHub API 获取官方插件 | 官方 Claude Code 技能 |
| **本地已安装** | ~18 | 自动扫描 ~/.claude/skills/ | 用户已安装的技能 |
| **去重后总计** | **~16,874** | URL + 名称归一化去重 | 持续增长 |
| **Anthropic Marketplace** | ~23 | GitHub API 获取官方插件 | 官方 Claude Code 技能 |
| **职业合集包** | 16 个 | profession_packs.py PROFESSION_PACKS | 一键安装全套 |
| **Context 规则** | 6 阶段 × N 技术栈 | advisor.py STAGE/TECHSTACK | 项目感知推荐 |

---

## 脚本清单

| 脚本 | 功能 | 何时用 |
|------|------|--------|
| `skill_advisor.py` | 原有推荐引擎（v4） | 兼容保留 |
| `skill_advisor_v2.py` | 统一入口（自动路由） | 需要自动判断模式时 |
| `semantic_search.py` | TF-IDF 语义搜索 + 同义词扩展 | **模糊需求首选** |
| `advisor.py` | Context Advisor（项目上下文感知） | **有项目目录时** |
| `profession_packs.py` | 职业合集包管理 | **用户说身份时** |
| `build_knowledge_base.py` | 知识库构建器 | 刷新数据源时 |
| `setup.sh` | 首次使用配置 | **首次使用时自动运行** |
| `incremental_update.py` | 增量更新 | CI 自动同步时 |
| `backfill_descriptions.py` | 描述回补 | CI 自动同步时 |
| `build_vectors.py` | 向量重建 | CI 自动同步时 |

## 数据更新

| 方式 | 触发 | 说明 |
|------|------|------|
| **自动** | 每周一 02:00 UTC | GitHub Actions 自动增量更新 + git push |
| **手动** | 用户想更新时 | `skill-advisor sync` 或 `git pull` |
| **提醒** | 数据库超过 7 天未更新 | 使用时提示用户更新 |

### 手动更新

#### 方式 1：关键词触发（Claude Code 用户）

用户说以下任一关键词时，Claude 自动执行更新：

| 类别 | 触发关键词 | 执行动作 |
|------|-----------|---------|
| **直接更新** | "更新技能" / "更新skill" / "skill更新" / "将这个技能更新一下" / "帮我更新" / "更新一下" | `cd skill_dir && git pull` |
| **同步数据** | "同步数据" / "同步技能" / "更新数据" / "数据同步" / "同步一下" | `cd skill_dir && git pull` |
| **刷新** | "刷新技能" / "刷新数据" / "刷新一下" / "重新加载" | `cd skill_dir && git pull` |
| **获取最新** | "获取最新" / "拉取最新" / "pull最新" / "有新版吗" | `cd skill_dir && git pull` |
| **检查更新** | "检查更新" / "有更新吗" | 检查数据库年龄，提示是否需要更新 |

#### 方式 2：命令触发（所有智能体通用）

适用于 Codex、Cursor、WorkBuddy 等任何智能体：

```bash
# 统一命令（推荐）
skill-advisor sync

# 或 git pull
cd ~/.claude/skills/skill-advisor && git pull
```

### 首次使用检查

首次使用时，建议运行配置脚本检查数据库状态：

```bash
bash ~/.claude/skills/skill-advisor/scripts/setup.sh
```

如果数据库超过 7 天未更新，会提示用户运行 `git pull`。

## 用户命令（CLI）

安装后，用户可直接使用 `skill-advisor` 命令：

```bash
# 搜索技能（每次启动自动检查更新）
skill-advisor search "react 最佳实践"
skill-advisor search "做个演示" --limit 5

# 手动同步最新数据
skill-advisor sync

# 查看统计
skill-advisor stats

# 重建向量索引（安装向量依赖后）
skill-advisor rebuild-vectors
```
