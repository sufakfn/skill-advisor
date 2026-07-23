# skill-advisor 开源路线图

> 版本: 6.1.0 · 更新日期: 2026-07-23 · 当前完成度: 90%

---

## 总览

```
已完成 ───────────────────────────────────────── 待完成
安装/搜索/向量/CI/Sync                          PyPI/WebUI/安全扫描
```

| 阶段 | 状态 | 关键指标 |
|------|------|----------|
| 核心功能 | ✅ 完成 | 17,744 技能，95.7% 描述覆盖，向量搜索 |
| CI/CD | ✅ 完成 | GitHub Actions 自动同步，每周一 02:00 UTC |
| 搜索质量 | ✅ 完成 | 混合搜索（向量+FTS5+LIKE），中文支持 |
| 职业推荐 | ✅ 完成 | 16 个职业包，关键词触发 |
| 更新机制 | ✅ 完成 | git pull，关键词触发，命令触发 |

---

## 已完成功能

### 核心搜索
- FTS5 全文搜索 + LIKE 模糊匹配
- 向量语义搜索（BAAI/bge-small-zh-v1.5，512 维）
- 混合搜索（向量+FTS5+LIKE 三路召回）
- 中文分词支持

### 数据源
- ClawHub API（99 条，有描述）
- skills.sh（21,703 条，220 关键词扫描）
- 本地已安装技能扫描
- 描述回补（GitHub raw URL 下载 SKILL.md）

### 推荐功能
- 16 个职业包（教师/PM/设计师/医生/学生等）
- Context Advisor（项目上下文感知）
- 模糊需求语义匹配

### 更新机制
- 增量更新（只处理新增，不动已有）
- Git LFS 分发（38MB 数据库）
- GitHub Actions 每周自动同步
- 关键词触发更新（"更新技能"/"同步数据"等）
- 命令触发更新（`skill-advisor sync`）

### CLI 工具
- `skill-advisor search "query"` — 搜索技能
- `skill-advisor sync` — 手动同步数据
- `skill-advisor stats` — 查看统计
- `skill-advisor rebuild-vectors` — 重建向量索引
- `skill-advisor warm-up` — 预加载模型

---

## 待完成（可选）

### PyPI 发布
- 注册 PyPI 账号
- 配置 `pyproject.toml` 元数据
- 构建 sdist + wheel
- 发布到 PyPI

### Web UI
- FastAPI + 搜索 API
- 搜索页面
- 职业包页面
- 技能详情页

### 安全扫描
- SKILL.md 静态分析
- 可疑 URL 检测
- 安装前确认提示

### 多语言
- 日语支持
- 韩语支持
- 运行时语言切换

---

## 如何参与

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

- 提 Bug → [Issue](https://github.com/sufakfn/skill-advisor/issues)
- 提 Feature → [Issue](https://github.com/sufakfn/skill-advisor/issues)
- 提 PR → [Pull Request](https://github.com/sufakfn/skill-advisor/pulls)
