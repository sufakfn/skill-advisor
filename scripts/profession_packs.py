#!/usr/bin/env python3
"""
职业合集包管理器 v1 —— 一键安装某个职业需要的全套技能

每个职业包包含：
  - 5-8 个核心技能（带安装命令）
  - 组合使用指南
  - 安装状态检查

支持15+热门职业/身份场景

用法：
  python profession_packs.py --list                    # 列出所有合集包
  python profession_packs.py --show teacher            # 查看教师包的详情
  python profession_packs.py --install teacher         # 安装教师包
  python profession_packs.py --install-all             # 安装所有包（按需选）
  python profession_packs.py --check teacher           # 检查已安装状态
  python profession_packs.py --search 视频             # 搜索适合某技能的包
  python profession_packs.py --export teacher.md        # 导出 Markdown 指南
"""

import json
import sys
from pathlib import Path

# ============================================================
# install_cmd 说明：
#   - "npx skills add ..."  = 真实可执行的安装命令
#   - "" (空字符串)        = 虚构/待定技能，需替换为真实技能后再发布
#
# 虚构技能列表（共 17 个，需在 Phase 2/3 中替换为真实技能）：
#   product-manager-toolkit, market-research-reports, ai-drawio,
#   wechat-hotspot-publisher, baoyu-post-to-wechat, baoyu-xhs-images,
#   video-creation-suite, tts-voice-synthesis, content-research-writer,
#   stock-analysis, icon-generator, creating-financial-models,
#   sales-ai-assistant, contract-review, anything-to-notebooklm,
#   ecommerce-copywriter, product-marketing-copywriter
# ============================================================

SCRIPT_DIR = Path(__file__).parent
PACKS_DIR = SCRIPT_DIR.parent / "packs"

# ============================================================
# 职业合集包定义
# ============================================================
# 每个包：slug, name, icon, desc, target_audience, skills[{name, install_cmd, reason}], combo_guide

PROFESSION_PACKS = [
    {
        "slug": "teacher",
        "name": "教师全能包",
        "icon": "🏫",
        "desc": "把 AI 变成你的教学助手 —— 出卷、批改、课件、家校沟通全包",
        "target_audience": "中小学教师、大学老师、培训机构讲师",
        "skills": [
            {"name": "unit-test", "install_cmd": "npx skills add anthropics/skills/unit-test --skill unit-test", "reason": "核心：自动出卷、批改、生成成绩报告", "required": True},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "做课件/说课PPT", "required": True},
            {"name": "dataviz", "install_cmd": "npx skills add vercel-labs/agent-skills --skill dataviz", "reason": "成绩图表、各题正确率分析", "required": False},
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "成绩汇总表、学生档案管理", "required": False},
            {"name": "proactive-agent", "install_cmd": "npx skills add anthropics/skills/proactive-agent", "reason": "定时提醒考试/家长会/每日作业", "required": False},
            {"name": "agent-memory", "install_cmd": "npx skills add anthropics/skills/agent-memory", "reason": "记录每个学生薄弱知识点，因材施教", "required": False},
            {"name": "baoyu-post-to-wechat", "install_cmd": "npx skills add anthropic-agent-skills/baoyu-post-to-wechat --skill baoyu-post-to-wechat", "reason": "家长通知、班级周报（需要时手动装）", "required": False},
            {"name": "tts-voice-synthesis", "install_cmd": "npx skills add anthropic-agent-skills/tts-voice-synthesis --skill tts-voice-synthesis", "reason": "英语听力音频、课文朗读", "required": False},
        ],
        "combo_guide": "先用 unit-test 出卷 → 考完用 xlsx 和 dataviz 做成绩分析 → 用 agent-memory 记录薄弱点 → 用 pptx 做讲评课件 → 用 proactive-agent 定时提醒下次考试。一个完整的「考试→分析→补课」闭环。",
    },
    {
        "slug": "product-manager",
        "name": "产品经理包",
        "icon": "📋",
        "desc": "PRD → 竞品 → 调研 → 路线图的完整产品工作流",
        "target_audience": "产品经理、产品总监、创业者",
        "skills": [
            {"name": "product-manager-toolkit", "install_cmd": "npx skills add anthropic-agent-skills/product-manager-toolkit --skill product-manager-toolkit", "reason": "核心：PRD模板、竞品分析、用户故事地图", "required": True},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "深度行业调研报告", "required": True},
            {"name": "web-design-analyzer", "install_cmd": "npx skills add anthropic-agent-skills/web-design-analyzer --skill web-design-analyzer", "reason": "竞品UI分析、设计对标", "required": False},
            {"name": "market-research-reports", "install_cmd": "npx skills add anthropic-agent-skills/market-research-reports --skill market-research-reports", "reason": "市场调研报告自动生成", "required": False},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "产品汇报、路演PPT", "required": False},
            {"name": "proactive-agent", "install_cmd": "npx skills add anthropics/skills/proactive-agent", "reason": "定时提醒需求评审、版本发布", "required": False},
            {"name": "ai-drawio", "install_cmd": "npx skills add anthropic-agent-skills/ai-drawio --skill ai-drawio", "reason": "产品流程图、架构图", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 做行业调研 → 用 market-research-reports 生成市场报告 → 用 web-design-analyzer 分析竞品 → 用 product-manager-toolkit 写PRD → 用 pptx 做汇报 → 用 proactive-agent 推进版本节奏。",
    },
    {
        "slug": "content-creator",
        "name": "自媒体创作者包",
        "icon": "🎬",
        "desc": "从选题到发布的全流程 —— 公众号、小红书、短视频全覆盖",
        "target_audience": "自媒体博主、内容运营、短视频创作者",
        "skills": [
            {"name": "wechat-hotspot-publisher", "install_cmd": "npx skills add anthropic-agent-skills/wechat-hotspot-publisher --skill wechat-hotspot-publisher", "reason": "核心：热点文自动生成+发布", "required": True},
            {"name": "baoyu-post-to-wechat", "install_cmd": "npx skills add anthropic-agent-skills/baoyu-post-to-wechat --skill baoyu-post-to-wechat", "reason": "公众号排版发文", "required": True},
            {"name": "baoyu-xhs-images", "install_cmd": "npx skills add anthropic-agent-skills/baoyu-xhs-images --skill baoyu-xhs-images", "reason": "小红书图文卡片制作", "required": False},
            {"name": "video-creation-suite", "install_cmd": "npx skills add anthropic-agent-skills/video-creation-suite --skill video-creation-suite", "reason": "短视频制作全流程", "required": False},
            {"name": "tts-voice-synthesis", "install_cmd": "npx skills add anthropic-agent-skills/tts-voice-synthesis --skill tts-voice-synthesis", "reason": "视频配音、旁白", "required": False},
            {"name": "content-research-writer", "install_cmd": "npx skills add anthropic-agent-skills/content-research-writer --skill content-research-writer", "reason": "深度内容研究写作", "required": False},
            {"name": "stock-analysis", "install_cmd": "npx skills add anthropic-agent-skills/stock-analysis --skill stock-analysis", "reason": "财经类内容的数据支撑", "required": False},
        ],
        "combo_guide": "用 wechat-hotspot-publisher 追热点 → 用 content-research-writer 深度调研 → 用 baoyu-post-to-wechat 发公众号 → 用 baoyu-xhs-images 同步小红书 → 用 video-creation-suite + tts-voice-synthesis 做视频版。一次创作，多平台分发。",
    },
    {
        "slug": "designer",
        "name": "设计师包",
        "icon": "🎨",
        "desc": "从竞品分析到视觉设计、UI 走查的完整设计工作流",
        "target_audience": "UI/UX 设计师、视觉设计师、设计总监",
        "skills": [
            {"name": "web-design-analyzer", "install_cmd": "npx skills add anthropic-agent-skills/web-design-analyzer --skill web-design-analyzer", "reason": "核心：竞品UI分析、设计对标", "required": True},
            {"name": "canvas-design", "install_cmd": "npx skills add anthropics/skills/canvas-design", "reason": "海报、封面、视觉作品设计", "required": True},
            {"name": "frontend-design", "install_cmd": "npx skills add anthropics/skills/frontend-design", "reason": "前端UI设计规范", "required": False},
            {"name": "icon-generator", "install_cmd": "npx skills add anthropic-agent-skills/icon-generator --skill icon-generator", "reason": "图标、Logo 生成", "required": False},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "设计提案PPT", "required": False},
        ],
        "combo_guide": "用 web-design-analyzer 分析竞品设计 → 用 canvas-design 做视觉稿 → 用 frontend-design 输出前端规范 → 用 icon-generator 生成图标 → 用 pptx 做设计提案。",
    },
    {
        "slug": "hr",
        "name": "人力资源包",
        "icon": "👥",
        "desc": "招聘、薪酬、考勤、劳动合同全覆盖",
        "target_audience": "HR、人事专员、招聘经理",
        "skills": [
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "核心：薪酬统计、考勤管理、人员花名册", "required": True},
            {"name": "docx", "install_cmd": "npx skills add anthropics/skills/docx", "reason": "劳动合同、通知文件、offer 信", "required": True},
            {"name": "tailored-resume-generator", "install_cmd": "npx skills add anthropics/skills/tailored-resume-generator", "reason": "简历筛选参考、JD 生成", "required": False},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "行业薪酬调研、竞品公司分析", "required": False},
            {"name": "proactive-agent", "install_cmd": "npx skills add anthropics/skills/proactive-agent", "reason": "面试提醒、合同到期提醒、转正提醒", "required": False},
            {"name": "pdf", "install_cmd": "npx skills add anthropics/skills/pdf", "reason": "PDF 合同处理、表单填写", "required": False},
        ],
        "combo_guide": "用 xlsx 管理薪酬考勤 → 用 docx 写合同和通知 → 用 tailored-resume-generator 写 JD → 用 deep-research-pro 做薪酬调研 → 用 proactive-agent 自动提醒关键节点。",
    },
    {
        "slug": "finance",
        "name": "财务会计包",
        "icon": "💰",
        "desc": "财务报表、财务建模、投资分析一站式",
        "target_audience": "会计、财务分析师、CFO、审计",
        "skills": [
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "核心：财务报表、数据分析", "required": True},
            {"name": "creating-financial-models", "install_cmd": "npx skills add anthropic-agent-skills/creating-financial-models --skill creating-financial-models", "reason": "财务建模、DCF 估值", "required": True},
            {"name": "pdf", "install_cmd": "npx skills add anthropics/skills/pdf", "reason": "发票、凭证、PDF 处理", "required": False},
            {"name": "stock-analysis", "install_cmd": "npx skills add anthropic-agent-skills/stock-analysis --skill stock-analysis", "reason": "投资分析、竞品公司财报", "required": False},
            {"name": "dataviz", "install_cmd": "npx skills add vercel-labs/agent-skills --skill dataviz", "reason": "财务数据可视化", "required": False},
            {"name": "proactive-agent", "install_cmd": "npx skills add anthropics/skills/proactive-agent", "reason": "报税提醒、月度结账提醒", "required": False},
        ],
        "combo_guide": "用 xlsx 做日常报表 → 用 creating-financial-models 做估值模型 → 用 pdf 处理发票凭证 → 用 stock-analysis 做投资参考 → 用 dataviz 做可视化汇报 → 用 proactive-agent 提醒关键时间节点。",
    },
    {
        "slug": "sales",
        "name": "销售精英包",
        "icon": "📈",
        "desc": "客户跟进、销售数据、产品演示全覆盖",
        "target_audience": "销售代表、销售总监、BD",
        "skills": [
            {"name": "sales-ai-assistant", "install_cmd": "npx skills add anthropic-agent-skills/sales-ai-assistant --skill sales-ai-assistant", "reason": "核心：客户跟进、转化分析", "required": True},
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "销售数据、业绩统计、漏斗分析", "required": True},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "产品演示、路演PPT", "required": False},
            {"name": "proactive-agent", "install_cmd": "npx skills add anthropics/skills/proactive-agent", "reason": "客户跟进提醒、合同到期提醒", "required": False},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "客户背景调研、竞品分析", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 调研客户 → 用 sales-ai-assistant 跟进转化 → 用 xlsx 统计业绩 → 用 pptx 做产品演示 → 用 proactive-agent 自动提醒跟进。",
    },
    {
        "slug": "lawyer",
        "name": "法律法务包",
        "icon": "⚖️",
        "desc": "合同审查、法律文书、判例查找一站式",
        "target_audience": "律师、法务、合规官",
        "skills": [
            {"name": "contract-review", "install_cmd": "npx skills add anthropic-agent-skills/contract-review --skill contract-review", "reason": "核心：合同审查、条款分析", "required": True},
            {"name": "docx", "install_cmd": "npx skills add anthropics/skills/docx", "reason": "法律文书、起诉状、代理词", "required": True},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "判例查找、法规检索", "required": False},
            {"name": "pdf", "install_cmd": "npx skills add anthropics/skills/pdf", "reason": "PDF 合同处理、证据整理", "required": False},
            {"name": "agent-memory", "install_cmd": "npx skills add anthropics/skills/agent-memory", "reason": "案件档案管理、客户信息记忆", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 查判例 → 用 contract-review 审合同 → 用 docx 写法律文书 → 用 pdf 整理证据 → 用 agent-memory 管理案件档案。",
    },
    {
        "slug": "doctor",
        "name": "医疗健康包",
        "icon": "🏥",
        "desc": "医学文献、患者档案、数据分析全覆盖",
        "target_audience": "医生、医学生、医疗研究员",
        "skills": [
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "核心：医学文献查找、PubMed 检索", "required": True},
            {"name": "agent-memory", "install_cmd": "npx skills add anthropics/skills/agent-memory", "reason": "患者档案记忆、病历管理", "required": True},
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "临床数据统计分析", "required": False},
            {"name": "tts-voice-synthesis", "install_cmd": "npx skills add anthropic-agent-skills/tts-voice-synthesis --skill tts-voice-synthesis", "reason": "患者教育音频、健康科普", "required": False},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "学术汇报、病例讨论PPT", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 查最新文献 → 用 agent-memory 管理患者档案 → 用 xlsx 做临床数据分析 → 用 pptx 做学术汇报 → 用 tts-voice-synthesis 做患者教育。",
    },
    {
        "slug": "student",
        "name": "学生学习包",
        "icon": "📚",
        "desc": "论文、笔记、考试复习、知识管理全覆盖",
        "target_audience": "大学生、研究生、备考学生",
        "skills": [
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "核心：论文资料查找、文献综述", "required": True},
            {"name": "anything-to-notebooklm", "install_cmd": "npx skills add anthropic-agent-skills/anything-to-notebooklm --skill anything-to-notebooklm", "reason": "学习资料整理、知识库构建", "required": True},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "课堂展示、答辩PPT", "required": False},
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "实验数据整理、成绩统计", "required": False},
            {"name": "agent-memory", "install_cmd": "npx skills add anthropics/skills/agent-memory", "reason": "知识点记忆、错题本", "required": False},
            {"name": "obsidian-skills-integrated", "install_cmd": "npx skills add anthropics/skills/obsidian-skills-integrated", "reason": "Obsidian 笔记管理", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 查论文 → 用 anything-to-notebooklm 整理学习资料 → 用 agent-memory 记知识点 → 用 obsidian-skills-integrated 管理笔记 → 用 pptx 做展示。",
    },
    {
        "slug": "investor",
        "name": "投资分析包",
        "icon": "📊",
        "desc": "股票分析、财务建模、行业研究一站式",
        "target_audience": "投资人、分析师、基金经理",
        "skills": [
            {"name": "stock-analysis", "install_cmd": "npx skills add anthropic-agent-skills/stock-analysis --skill stock-analysis", "reason": "核心：股票分析、行情数据", "required": True},
            {"name": "creating-financial-models", "install_cmd": "npx skills add anthropic-agent-skills/creating-financial-models --skill creating-financial-models", "reason": "财务建模、DCF 估值", "required": True},
            {"name": "market-research-reports", "install_cmd": "npx skills add anthropic-agent-skills/market-research-reports --skill market-research-reports", "reason": "行业研究报告", "required": False},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "深度调研、新闻追踪", "required": False},
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "投资组合数据分析", "required": False},
            {"name": "dataviz", "install_cmd": "npx skills add vercel-labs/agent-skills --skill dataviz", "reason": "投资数据可视化", "required": False},
        ],
        "combo_guide": "用 market-research-reports 看行业 → 用 stock-analysis 看个股 → 用 creating-financial-models 做估值 → 用 deep-research-pro 做深度调研 → 用 xlsx + dataviz 管理投资组合。",
    },
    {
        "slug": "ecommerce",
        "name": "电商卖家包",
        "icon": "🛒",
        "desc": "产品文案、营销、订单管理全覆盖",
        "target_audience": "电商卖家、运营、跨境电商",
        "skills": [
            {"name": "ecommerce-copywriter", "install_cmd": "npx skills add anthropic-agent-skills/ecommerce-copywriter --skill ecommerce-copywriter", "reason": "核心：产品文案、详情页", "required": True},
            {"name": "product-marketing-copywriter", "install_cmd": "npx skills add anthropic-agent-skills/product-marketing-copywriter --skill product-marketing-copywriter", "reason": "营销文案、推广文案", "required": True},
            {"name": "xlsx", "install_cmd": "npx skills add anthropics/skills/xlsx", "reason": "订单管理、库存统计", "required": False},
            {"name": "canvas-design", "install_cmd": "npx skills add anthropics/skills/canvas-design", "reason": "产品图、主图设计", "required": False},
            {"name": "stock-analysis", "install_cmd": "npx skills add anthropic-agent-skills/stock-analysis --skill stock-analysis", "reason": "上市公司竞品分析", "required": False},
        ],
        "combo_guide": "用 ecommerce-copywriter 写产品文案 → 用 product-marketing-copywriter 写推广 → 用 canvas-design 做产品图 → 用 xlsx 管订单库存 → 用 stock-analysis 看竞品公司财报。",
    },
    {
        "slug": "frontend-dev",
        "name": "前端开发者包",
        "icon": "🖥️",
        "desc": "React/Vue/Next.js 最佳实践 + 测试 + 性能 + 监控",
        "target_audience": "前端工程师、全栈开发者",
        "skills": [
            {"name": "react-best-practices", "install_cmd": "npx skills add vercel-labs/agent-skills --skill react-best-practices", "reason": "React 编码最佳实践", "required": True},
            {"name": "frontend-design", "install_cmd": "npx skills add anthropics/skills/frontend-design", "reason": "前端UI设计规范", "required": True},
            {"name": "webapp-testing", "install_cmd": "npx skills add anthropics/skills/webapp-testing", "reason": "Playwright 端到端测试", "required": False},
            {"name": "web-perf", "install_cmd": "npx skills add cloudflare/agent-skills --skill web-perf", "reason": "Core Web Vitals 性能审计", "required": False},
            {"name": "sentry-react-sdk", "install_cmd": "npx skills add anthropics/skills/sentry-react-sdk", "reason": "React 错误监控", "required": False},
            {"name": "vercel-deploy", "install_cmd": "npx skills add vercel-labs/agent-skills --skill vercel-deploy", "reason": "一键部署到 Vercel", "required": False},
        ],
        "combo_guide": "用 react-best-practices 写高质量代码 → 用 frontend-design 做UI规范 → 用 webapp-testing 做E2E测试 → 用 web-perf 做性能审计 → 用 sentry-react-sdk 做线上监控 → 用 vercel-deploy 一键上线。",
    },
    {
        "slug": "backend-dev",
        "name": "后端开发者包",
        "icon": "⚙️",
        "desc": "数据库优化 + 安全 + 测试 + 部署运维",
        "target_audience": "后端工程师、DevOps、架构师",
        "skills": [
            {"name": "postgres-best-practices", "install_cmd": "npx skills add supabase/agent-skills --skill postgres-best-practices", "reason": "PostgreSQL 最佳实践", "required": True},
            {"name": "security-best-practices", "install_cmd": "npx skills add anthropics/skills/security-best-practices", "reason": "代码安全审查", "required": True},
            {"name": "insecure-defaults", "install_cmd": "npx skills add anthropics/skills/insecure-defaults", "reason": "硬编码密码/默认凭据检测", "required": False},
            {"name": "webapp-testing", "install_cmd": "npx skills add anthropics/skills/webapp-testing", "reason": "API 端到端测试", "required": False},
            {"name": "sentry-sdk-setup", "install_cmd": "npx skills add anthropics/skills/sentry-sdk-setup", "reason": "后端错误监控", "required": False},
            {"name": "vercel-deploy", "install_cmd": "npx skills add vercel-labs/agent-skills --skill vercel-deploy", "reason": "一键部署", "required": False},
        ],
        "combo_guide": "用 postgres-best-practices 优化数据库 → 用 security-best-practices 做安全审查 → 用 insecure-defaults 查硬编码密码 → 用 webapp-testing 做API测试 → 用 sentry-sdk-setup 做线上监控。",
    },
    {
        "slug": "writer",
        "name": "写作创作者包",
        "icon": "✍️",
        "desc": "从研究到写作到发布的完整创作工作流",
        "target_audience": "作家、自媒体写作者、技术写作者",
        "skills": [
            {"name": "content-research-writer", "install_cmd": "npx skills add anthropic-agent-skills/content-research-writer --skill content-research-writer", "reason": "核心：深度研究写作", "required": True},
            {"name": "docx", "install_cmd": "npx skills add anthropics/skills/docx", "reason": "文档排版、Word 输出", "required": True},
            {"name": "baoyu-post-to-wechat", "install_cmd": "npx skills add anthropic-agent-skills/baoyu-post-to-wechat --skill baoyu-post-to-wechat", "reason": "公众号发布", "required": False},
            {"name": "humanizer", "install_cmd": "npx skills add anthropics/skills/humanizer", "reason": "去AI痕迹、文风优化", "required": False},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "深度调研、素材收集", "required": False},
            {"name": "pdf", "install_cmd": "npx skills add anthropics/skills/pdf", "reason": "PDF 输出、电子书制作", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 做调研 → 用 content-research-writer 写初稿 → 用 humanizer 优化文风 → 用 docx 排版 → 用 baoyu-post-to-wechat 发布 → 用 pdf 做电子书。",
    },
    {
        "slug": "job-seeker",
        "name": "求职找工作包",
        "icon": "🎯",
        "desc": "简历、面试、职业规划一站式",
        "target_audience": "求职者、应届生、跳槽者",
        "skills": [
            {"name": "tailored-resume-generator", "install_cmd": "npx skills add anthropics/skills/tailored-resume-generator", "reason": "核心：定制化简历生成", "required": True},
            {"name": "deep-research-pro", "install_cmd": "npx skills add anthropic-agent-skills/deep-research --skill deep-research", "reason": "目标公司调研", "required": True},
            {"name": "pptx", "install_cmd": "npx skills add anthropics/skills/pptx", "reason": "作品集展示PPT", "required": False},
            {"name": "humanizer", "install_cmd": "npx skills add anthropics/skills/humanizer", "reason": "简历文风优化", "required": False},
            {"name": "proactive-agent", "install_cmd": "npx skills add anthropics/skills/proactive-agent", "reason": "面试提醒、跟进提醒", "required": False},
        ],
        "combo_guide": "用 deep-research-pro 调研目标公司 → 用 tailored-resume-generator 定制简历 → 用 humanizer 优化文风 → 用 pptx 做作品集 → 用 proactive-agent 提醒面试和跟进。",
    },
]


# ============================================================
# 合集包操作
# ============================================================

def get_installed_skills():
    """获取已安装的技能列表"""
    skill_dir = Path.home() / ".claude" / "skills"
    if not skill_dir.exists():
        return set()
    installed = set()
    for d in skill_dir.iterdir():
        if d.is_dir():
            base = d.name.split("（")[0] if "（" in d.name else d.name
            installed.add(base.strip().lower())
    return installed


def check_pack_status(pack):
    """检查一个包的安装状态"""
    installed = get_installed_skills()
    result = []
    for skill in pack["skills"]:
        name = skill["name"]
        base = name.split("（")[0].strip().lower()
        is_installed = base in installed or any(base in d for d in installed)
        result.append({
            "name": name,
            "required": skill.get("required", False),
            "installed": is_installed,
            "reason": skill["reason"],
        })
    installed_count = sum(1 for r in result if r["installed"])
    total = len(result)
    return {
        "pack_slug": pack["slug"],
        "pack_name": pack["name"],
        "skills": result,
        "installed_count": installed_count,
        "total": total,
        "complete": installed_count == total,
        "completion": round(installed_count / total * 100) if total > 0 else 0,
    }


def search_packs(query):
    """搜索适合某关键词的合集包"""
    query_lower = query.lower()
    results = []
    for pack in PROFESSION_PACKS:
        score = 0
        # 包名匹配
        if query_lower in pack["name"].lower():
            score += 10
        # 描述匹配
        if query_lower in pack["desc"].lower():
            score += 5
        # 技能名匹配
        for skill in pack["skills"]:
            if query_lower in skill["name"].lower():
                score += 3
            if query_lower in skill["reason"].lower():
                score += 2
        # 目标受众匹配
        if query_lower in pack["target_audience"].lower():
            score += 4
        if score > 0:
            results.append((pack, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in results]


def export_pack_markdown(pack, output_path):
    """导出合集包为 Markdown 指南"""
    status = check_pack_status(pack)
    lines = [
        f"# {pack['icon']} {pack['name']}",
        "",
        f"**适合人群：** {pack['target_audience']}",
        f"**简介：** {pack['desc']}",
        "",
        f"## 包含技能（{status['installed_count']}/{status['total']} 已安装）",
        "",
        "| 状态 | 技能 | 角色 | 说明 |",
        "|:---:|------|------|------|",
    ]
    for s in status["skills"]:
        icon = "✅" if s["installed"] else "🔴" if s["required"] else "⬜"
        req = "必装" if s["required"] else "建议"
        lines.append(f"| {icon} | `{s['name']}` | {req} | {s['reason']} |")

    lines.extend([
        "",
        "## 组合使用指南",
        "",
        pack["combo_guide"],
        "",
        "## 安装命令",
        "",
        "```bash",
    ])
    for skill in pack["skills"]:
        if skill.get("install_cmd"):
            lines.append(f"# {skill['reason']}")
            lines.append(skill["install_cmd"])
    lines.append("```")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return content


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="职业合集包管理器 —— 一键安装全套技能")
    parser.add_argument("--list", action="store_true", help="列出所有合集包")
    parser.add_argument("--show", metavar="SLUG", help="查看某个包详情")
    parser.add_argument("--check", metavar="SLUG", help="检查安装状态")
    parser.add_argument("--install", metavar="SLUG", help="生成安装命令")
    parser.add_argument("--search", metavar="QUERY", help="搜索适合的包")
    parser.add_argument("--export", metavar="SLUG", help="导出 Markdown 指南")
    parser.add_argument("--profile", action="store_true", help="显示已安装技能统计")
    args = parser.parse_args()

    if args.profile:
        installed = get_installed_skills()
        print(json.dumps({
            "installed_count": len(installed),
            "installed_skills": sorted(installed),
            "available_packs": len(PROFESSION_PACKS),
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.list:
        installed = get_installed_skills()
        results = []
        for pack in PROFESSION_PACKS:
            status = check_pack_status(pack)
            results.append({
                "slug": pack["slug"],
                "name": f"{pack['icon']} {pack['name']}",
                "desc": pack["desc"],
                "target": pack["target_audience"],
                "total_skills": status["total"],
                "installed": status["installed_count"],
                "completion": f"{status['completion']}%",
            })
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.show:
        pack = next((p for p in PROFESSION_PACKS if p["slug"] == args.show), None)
        if not pack:
            print(json.dumps({"error": f"Pack '{args.show}' not found", "available": [p["slug"] for p in PROFESSION_PACKS]}, ensure_ascii=False))
            sys.exit(1)
        status = check_pack_status(pack)
        print(json.dumps({**pack, "status": status}, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.check:
        pack = next((p for p in PROFESSION_PACKS if p["slug"] == args.check), None)
        if not pack:
            print(json.dumps({"error": f"Pack '{args.check}' not found"}, ensure_ascii=False))
            sys.exit(1)
        status = check_pack_status(pack)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.install:
        pack = next((p for p in PROFESSION_PACKS if p["slug"] == args.install), None)
        if not pack:
            print(json.dumps({"error": f"Pack '{args.install}' not found"}, ensure_ascii=False))
            sys.exit(1)
        status = check_pack_status(pack)
        to_install = [s for s in status["skills"] if not s["installed"]]
        print(json.dumps({
            "pack": pack["name"],
            "already_installed": status["installed_count"],
            "to_install": len(to_install),
            "install_plan": [
                {"name": s["name"], "reason": s["reason"], "required": s["required"]}
                for s in to_install
            ],
            "combo_guide": pack["combo_guide"],
            "next_step": f"Claude 将逐个安装以上 {len(to_install)} 个技能",
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.search:
        results = search_packs(args.search)
        print(json.dumps({
            "query": args.search,
            "matched_packs": [
                {
                    "slug": p["slug"],
                    "name": f"{p['icon']} {p['name']}",
                    "desc": p["desc"],
                    "skills": [s["name"] for s in p["skills"]],
                }
                for p in results
            ]
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.export:
        pack = next((p for p in PROFESSION_PACKS if p["slug"] == args.export), None)
        if not pack:
            print(json.dumps({"error": f"Pack '{args.export}' not found"}, ensure_ascii=False))
            sys.exit(1)
        out_path = f"{pack['slug']}_guide.md"
        export_pack_markdown(pack, out_path)
        print(json.dumps({"exported_to": out_path, "pack": pack["name"]}, ensure_ascii=False))
        sys.exit(0)

    # 默认：列出所有包
    print(json.dumps({
        "packs_count": len(PROFESSION_PACKS),
        "packs": [{"slug": p["slug"], "name": f"{p['icon']} {p['name']}", "desc": p["desc"]} for p in PROFESSION_PACKS],
        "usage": "python profession_packs.py --list | --show SLUG | --install SLUG | --search QUERY",
    }, ensure_ascii=False, indent=2))
