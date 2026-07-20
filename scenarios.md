# 场景→技能映射知识库

> 当用户描述自己的职业、身份、场景时，根据此映射表找到对应技能。
> 这是 Claude 做推荐时的参考依据。

---

## 🏫 教育

### 教师（各科通用）
**核心需求：** 备课出题、批改分析、成绩统计、家校沟通
**推荐技能：**
- unit-test（单元测试专家）— 自动出卷、批改、生成成绩报告
- dataviz（数据可视化）— 成绩图表、分数分布、知识点掌握度
- pptx / ppt-generator — 做课件
- xlsx — 成绩表、学生档案管理
- proactive-agent（主动预判AI）— 定时提醒、自动通知家长
- agent-memory（AI记忆系统）— 记住每个学生薄弱点
- baoyu-post-to-wechat（微信公众号发文）— 家长通知、班级周报

### 数学老师（特定）
**核心需求：** 出题（含公式）、几何图形、成绩分析、错题追踪
**推荐技能：**
- unit-test — 出卷（支持 LaTeX 公式）
- dataviz — 成绩趋势图、各题正确率分析
- agent-memory — 记录每个学生易错题型
- proactive-agent — 定期出卷/家长会提醒
- xlsx — 成绩汇总表

### 语文老师
**推荐技能：**
- unit-test — 阅读理解出题、作文评分参考
- baoyu-post-to-wechat — 发布范文、班级动态
- agent-memory — 记录学生阅读偏好、写作薄弱点
- tts-voice-synthesis — 课文朗读音频

### 英语老师
**推荐技能：**
- unit-test — 听力/阅读/语法出题
- tts-voice-synthesis — 标准发音音频
- agent-memory — 记录学生单词量、语法薄弱点

### 学生
**推荐技能：**
- deep-research — 论文资料查找
- pptx — 课堂展示
- xlsx — 实验数据整理
- agent-memory — 知识点记忆管理
- anything-to-notebooklm — 学习资料整理

---

## 💼 办公室白领

### 行政/文秘
**推荐技能：**
- docx — 公文写作、会议纪要
- xlsx — 数据统计、报表
- pptx — 汇报演示
- pdf — 文档处理
- proactive-agent — 日程提醒、定期报告

### 人力资源/HR
**推荐技能：**
- xlsx — 薪酬统计、考勤管理
- docx — 劳动合同、通知文件
- tailored-resume-generator — 简历筛选参考
- deep-research — 行业薪酬调研
- proactive-agent — 面试提醒、合同到期提醒

### 财务会计
**推荐技能：**
- xlsx — 核心工具，财务报表、数据分析
- pdf — 发票、凭证处理
- creating-financial-models — 财务建模
- stock-analysis — 投资分析参考
- dataviz — 财务数据可视化

### 销售
**推荐技能：**
- sales-ai-assistant — 客户跟进、转化分析
- xlsx — 销售数据、业绩统计
- pptx — 产品演示、路演
- proactive-agent — 客户跟进提醒
- crm 相关技能

### 市场营销
**推荐技能：**
- product-marketing-copywriter — 营销文案
- content-creation-publisher — 内容发布
- baoyu-post-to-wechat — 公众号运营
- market-research-reports — 市场调研
- dataviz — 数据报告可视化

---

## 🎨 创意/内容

### 自媒体/博主
**推荐技能：**
- baoyu-post-to-wechat — 公众号发文
- baoyu-xhs-images — 小红书图文
- wechat-hotspot-publisher — 热点文生成
- video-creation-suite — 视频制作
- content-creation-publisher — 内容发布一条龙
- tts-voice-synthesis — 配音

### 视频创作者
**推荐技能：**
- video-creation-suite — 视频制作
- tts-voice-synthesis — 配音
- sora / imagegen — AI 视频/图片生成
- infinitetalk — 数字人

### 设计师
**推荐技能：**
- canvas-design — 视觉设计
- frontend-design — UI 设计
- icon-generator — 图标生成
- web-design-analyzer — 竞品分析

### 作家/写作者
**推荐技能：**
- docx — 写作排版
- baoyu-post-to-wechat — 发布
- content-research-writer — 研究写作
- poetry-music-visual — 文艺创作

---

## 🏢 管理/专业

### 产品经理
**推荐技能：**
- product-manager-toolkit — PRD、竞品分析
- deep-research — 行业调研
- web-design-analyzer — 竞品 UI 分析
- market-research-reports — 市场报告
- proactive-agent — 定时任务

### 律师
**推荐技能：**
- contract-review — 合同审查
- legal-assistant-skills-main — 法律助手
- docx — 法律文书
- deep-research — 判例查找

### 投资人/金融
**推荐技能：**
- stock-analysis — 股票分析
- creating-financial-models — 财务建模
- market-research-reports — 行业研究
- deep-research — 深度调研
- xlsx — 数据分析

### 医生/医疗
**推荐技能：**
- deep-research — 医学文献查找
- agent-memory — 患者档案记忆
- xlsx — 数据统计分析
- tts-voice-synthesis — 患者教育音频

---

## 🛠️ 技术/开发（已有良好支持，保持不变）

### 前端开发
**推荐技能：** frontend-design, react-best-practices, webapp-testing, sentry

### 后端开发
**推荐技能：** postgres-best-practices, testing, security, deploy

### 全栈开发
**推荐技能：** frontend + backend + deploy + testing

### 桌面应用开发
**推荐技能：** frontend-design, pdf, xlsx, security

---

## 🏠 日常生活

### 个人/家庭
**推荐技能：**
- stock-analysis — 理财分析
- creating-financial-models — 家庭财务规划
- bedtime-story — 睡前故事（有小孩）
- moltbook — 绘本制作

### 电商卖家
**推荐技能：**
- ecommerce-copywriter — 产品文案
- product-marketing-copywriter — 营销文案
- pet-commerce-creator — 宠物带货
- xlsx — 订单管理

---

## 📋 匹配规则

1. **先匹配职业身份** → 找到对应场景 → 推荐该场景的技能
2. **再匹配具体需求** → 如果用户说了具体需求（如"我想做视频"），优先按需求匹配
3. **已安装的技能优先推荐**（标记 ✅）
4. **如果用户身份不在上表中** → 根据用户描述的具体需求关键词匹配
5. **如果完全无法判断** → 问用户 1-2 个澄清问题
