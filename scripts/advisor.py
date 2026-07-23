#!/usr/bin/env python3
"""
Context Advisor v1 —— 上下文感知技能推荐（无需用户主动问）

核心能力：
  1. 扫描项目上下文（package.json、.git、README、最近修改的文件）
  2. 根据上下文自动推断需要什么技能
  3. 检测项目阶段变化（刚搭建框架？开始写业务逻辑？）→ 推荐对应技能
  4. 输出 JSON 给 Claude，Claude 决定是否打断推荐

四种触发模式：
  - manual  : 用户显式调用 advisor.py（默认）
  - hook    : 被 Claude Code hook 触发（文件保存后）
  - session : 新会话启动时触发
  - check   : 快速检查当前上下文，返回 1-3 个最推荐技能

用法：
  python advisor.py                          # 手动：分析当前项目
  python advisor.py --cwd /path/to/project   # 指定项目
  python advisor.py --mode hook              # hook 模式（更简洁输出）
  python advisor.py --mode session           # 会话模式（更丰富输出）
  python advisor.py --check                  # 快速检查，只返回 top-3
  python advisor.py "刚加了支付功能"          # 结合用户描述
  python advisor.py --profile                # 显示上下文信息
"""

import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CACHE_DIR = SKILL_DIR / ".cache"

# ============================================================
# 项目上下文分析
# ============================================================

def analyze_project_context(project_dir="."):
    """
    深入分析项目上下文，返回结构化信息
    """
    p = Path(project_dir).resolve()
    ctx = {
        "path": str(p),
        "project_name": p.name,
        "type": "unknown",
        "frontend": None,
        "backend": None,
        "database": None,
        "testing": None,
        "deployment": None,
        "features": [],
        "dependencies": 0,
        "dev_dependencies": 0,
        "has_git": False,
        "recent_files": [],
        "stage": "unknown",
        "tech_stack": [],
    }

    # --- package.json ---
    pkg_file = p / "package.json"
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
            deps = pkg.get("dependencies", {})
            dev_deps = pkg.get("devDependencies", {})
            ctx["dependencies"] = len(deps)
            ctx["dev_dependencies"] = len(dev_deps)
            all_deps = {**deps, **dev_deps}
            dep_str = " ".join(all_deps.keys()).lower()

            # 前端框架
            if "react" in all_deps:
                ctx["frontend"] = "React"
            elif "vue" in all_deps or "@vue/core" in all_deps:
                ctx["frontend"] = "Vue"
            elif "svelte" in all_deps:
                ctx["frontend"] = "Svelte"
            elif "@angular/core" in all_deps:
                ctx["frontend"] = "Angular"
            elif "solid-js" in all_deps:
                ctx["frontend"] = "Solid"

            # 全栈框架
            if "next" in all_deps:
                ctx["frontend"] = "Next.js"
            elif "nuxt" in all_deps:
                ctx["frontend"] = "Nuxt"
            elif "remix" in all_deps:
                ctx["frontend"] = "Remix"
            elif "astro" in all_deps:
                ctx["frontend"] = "Astro"

            # 后端（通过依赖推测）
            if "express" in all_deps or "koa" in all_deps or "fastify" in all_deps:
                ctx["backend"] = "Node.js"
            elif "prisma" in all_deps or "drizzle-orm" in all_deps:
                ctx["database"] = "ORM"

            # 数据库
            if "pg" in all_deps or "postgres" in all_deps:
                ctx["database"] = "PostgreSQL"
            elif "mysql" in all_deps or "mysql2" in all_deps:
                ctx["database"] = "MySQL"
            elif "mongodb" in all_deps or "mongoose" in all_deps:
                ctx["database"] = "MongoDB"
            elif "redis" in all_deps or "ioredis" in all_deps:
                ctx["features"].append("redis")
            elif "better-sqlite3" in all_deps or "sqlite" in all_deps:
                ctx["database"] = "SQLite"

            # 测试
            if "vitest" in all_deps:
                ctx["testing"] = "Vitest"
            elif "jest" in all_deps:
                ctx["testing"] = "Jest"
            elif "playwright" in all_deps or "@playwright/test" in all_deps:
                ctx["testing"] = "Playwright"

            # 部署
            if "vercel" in dep_str:
                ctx["deployment"] = "Vercel"
            elif "@netlify" in dep_str:
                ctx["deployment"] = "Netlify"
            elif "wrangler" in all_deps or "cloudflare" in dep_str:
                ctx["deployment"] = "Cloudflare"
            elif "docker" in dep_str or (p / "Dockerfile").exists():
                ctx["deployment"] = "Docker"

            # 特性检测
            feature_deps = {
                "stripe": ["payment", "支付"],
                "@supabase/supabase-js": ["supabase", "auth"],
                "firebase": ["firebase", "auth"],
                "next-auth": ["auth", "登录"],
                "@clerk/nextjs": ["auth", "登录"],
                "tailwindcss": ["styling"],
                "three": ["3d"],
                "three.js": ["3d"],
                "chart.js": ["charts", "可视化"],
                "recharts": ["charts", "可视化"],
                "react-query": ["data-fetching"],
                "@tanstack/react-query": ["data-fetching"],
                "zustand": ["state-management"],
                "jotai": ["state-management"],
                "resend": ["email"],
                "@sendgrid/mail": ["email"],
                "openai": ["ai"],
                "@anthropic-ai/sdk": ["ai"],
                "@google/generative-ai": ["ai"],
                "sharp": ["image-processing"],
                "react-hook-form": ["forms"],
                "zod": ["validation"],
                "d3": ["visualization"],
            }
            for dep, feats in feature_deps.items():
                if dep in all_deps:
                    ctx["features"].extend(feats)

        except Exception:
            pass

    # --- Python 项目 ---
    if (p / "requirements.txt").exists() or (p / "pyproject.toml").exists() or (p / "Pipfile").exists():
        ctx["backend"] = ctx["backend"] or "Python"
        for fname in ("requirements.txt", "pyproject.toml", "Pipfile"):
            f = p / fname
            if f.exists():
                try:
                    content = f.read_text(encoding="utf-8").lower()
                    if "django" in content: ctx["backend"] = "Django"
                    elif "fastapi" in content: ctx["backend"] = "FastAPI"
                    elif "flask" in content: ctx["backend"] = "Flask"
                    if "pytest" in content: ctx["testing"] = "pytest"
                except Exception:
                    pass

    # --- Go ---
    if (p / "go.mod").exists():
        ctx["backend"] = "Go"

    # --- Rust / Tauri ---
    if (p / "Cargo.toml").exists():
        ctx["backend"] = "Rust"
    if (p / "src-tauri" / "Cargo.toml").exists():
        ctx["frontend"] = ctx["frontend"] or "Web"
        ctx["features"].append("tauri")

    # --- Git ---
    ctx["has_git"] = (p / ".git").is_dir()

    # --- 最近修改的文件 ---
    try:
        files = []
        for f in p.rglob("*"):
            if f.is_file() and ".git" not in str(f) and "node_modules" not in str(f):
                try:
                    mtime = f.stat().st_mtime
                    files.append((mtime, f.relative_to(p)))
                except Exception:
                    pass
        files.sort(reverse=True)
        ctx["recent_files"] = [str(f) for _, f in files[:10]]
    except Exception:
        pass

    # --- 项目类型 ---
    if ctx["frontend"] and ctx["backend"]:
        ctx["type"] = "fullstack"
    elif ctx["frontend"] == "Next.js" or ctx["frontend"] == "Nuxt" or ctx["frontend"] == "Remix":
        ctx["type"] = "fullstack"
    elif ctx["frontend"]:
        ctx["type"] = "web-frontend"
    elif ctx["backend"]:
        ctx["type"] = "backend"
    elif (p / "src-tauri").exists():
        ctx["type"] = "desktop"

    # --- 项目阶段推断 ---
    if ctx["dependencies"] == 0 and ctx["dev_dependencies"] == 0:
        ctx["stage"] = "empty"
    elif ctx["dependencies"] < 5:
        ctx["stage"] = "setup"  # 刚搭建
    elif "auth" in ctx["features"] or "登录" in ctx["features"]:
        ctx["stage"] = "core-features"  # 核心功能开发中
    elif ctx["testing"]:
        ctx["stage"] = "testing"  # 测试阶段
    elif ctx["deployment"]:
        ctx["stage"] = "deploying"  # 部署阶段
    else:
        ctx["stage"] = "developing"  # 常规开发

    # --- Tech Stack 标签 ---
    if ctx["frontend"]: ctx["tech_stack"].append(ctx["frontend"])
    if ctx["backend"]: ctx["tech_stack"].append(ctx["backend"])
    if ctx["database"]: ctx["tech_stack"].append(ctx["database"])
    if ctx["testing"]: ctx["tech_stack"].append(ctx["testing"])
    ctx["tech_stack"].extend(ctx["features"])

    return ctx


# ============================================================
# 阶段 → 推荐策略
# ============================================================

STAGE_RECOMMENDATIONS = {
    "empty": {
        "message": "🆕 新项目！建议先搭建基础架构",
        "suggest": ["skill-creator", "frontend-design"],
        "categories": ["架构设计", "开发规范"],
    },
    "setup": {
        "message": "🔧 项目搭建中，框架和代码规范类技能能帮你少走弯路",
        "suggest": ["react-best-practices", "frontend-design"],
        "categories": ["最佳实践", "代码规范"],
    },
    "core-features": {
        "message": "⚡ 核心功能开发中，安全和性能类技能正当时",
        "suggest": ["security-best-practices", "postgres-best-practices", "web-perf"],
        "categories": ["安全", "性能"],
    },
    "developing": {
        "message": "💻 开发进行中，质量监控和调试技能能让你事半功倍",
        "suggest": ["sentry-sdk-setup", "testing", "webapp-testing"],
        "categories": ["监控", "调试", "测试"],
    },
    "testing": {
        "message": "🧪 测试阶段！覆盖率提升和安全审计是上线前必做",
        "suggest": ["testing-handbook-skills", "insecure-defaults", "audit-context-building"],
        "categories": ["测试覆盖率", "安全审计"],
    },
    "deploying": {
        "message": "🚀 部署/上线阶段，监控告警和性能优化要跟上",
        "suggest": ["sentry-sdk-setup", "sentry-create-alert", "web-perf"],
        "categories": ["监控", "报警", "性能"],
    },
}

# ============================================================
# 技术栈 → 推荐技能
# ============================================================

TECHSTACK_RECOMMENDATIONS = {
    "React": {
        "skills": ["react-best-practices", "sentry-react-sdk", "webapp-testing"],
        "reason": "React 项目标配最佳实践和错误监控",
    },
    "Vue": {
        "skills": ["webapp-testing", "sentry-sdk-setup"],
        "reason": "Vue 项目也需要端到端测试和错误监控",
    },
    "Next.js": {
        "skills": ["next-best-practices", "next-cache-components", "web-perf"],
        "reason": "Next.js 项目必装缓存策略和性能优化",
    },
    "Nuxt": {
        "skills": ["web-perf", "webapp-testing"],
        "reason": "Nuxt 项目的性能优化和测试必备",
    },
    "Node.js": {
        "skills": ["postgres-best-practices", "insecure-defaults", "security-best-practices"],
        "reason": "Node.js 后端必须关注安全和数据库优化",
    },
    "Django": {
        "skills": ["postgres-best-practices", "security-best-practices"],
        "reason": "Django 项目的数据库优化和安全配置",
    },
    "FastAPI": {
        "skills": ["postgres-best-practices", "security-best-practices"],
        "reason": "FastAPI 项目的数据库和安全最佳实践",
    },
    "PostgreSQL": {
        "skills": ["postgres-best-practices"],
        "reason": "PostgreSQL 最佳实践 —— 让查询飞起来",
    },
    "MongoDB": {
        "skills": ["security-best-practices"],
        "reason": "MongoDB 项目也要关注安全",
    },
    "Vitest": {
        "skills": ["property-based-testing"],
        "reason": "已经在用 Vitest，可以试试属性测试提升覆盖率",
    },
    "Jest": {
        "skills": ["property-based-testing"],
        "reason": "Jest + 属性测试 = 更强的测试覆盖",
    },
    "Playwright": {
        "skills": ["web-perf"],
        "reason": "Playwright 测试已经很棒了，加上性能审计更完整",
    },
    "Vercel": {
        "skills": ["web-perf"],
        "reason": "Vercel 部署后做个性能审计，让 Lighthouse 分数更高",
    },
    "payment": {
        "skills": ["stripe-best-practices", "building-secure-contracts"],
        "reason": "支付功能上线前务必做安全审计",
    },
    "auth": {
        "skills": ["create-auth", "best-practices-auth", "insecure-defaults"],
        "reason": "认证系统的安全至关重要，不能省审计",
    },
    "ai": {
        "skills": ["mcp-builder"],
        "reason": "AI 项目可以试试 MCP 集成更多能力",
    },
    "redis": {
        "skills": ["web-perf"],
        "reason": "Redis 缓存已经上了，配合性能审计更完善",
    },
    "charts": {
        "skills": ["web-perf"],
        "reason": "数据可视化项目也要关注渲染性能",
    },
    "3d": {
        "skills": ["web-perf"],
        "reason": "3D 项目的性能优化是关键挑战",
    },
}


# ============================================================
# 推理：上下文 → 推荐
# ============================================================

def generate_advisor_recommendations(ctx, user_text=None):
    """
    根据项目上下文生成推荐
    返回：{message, suggestions:[{name, reason, stage_trigger}], stage, tech_stack}
    """
    recommendations = []
    seen = set()

    # 1. 基于项目阶段的推荐
    stage = ctx.get("stage", "unknown")
    if stage in STAGE_RECOMMENDATIONS:
        stage_rec = STAGE_RECOMMENDATIONS[stage]
        for skill_name in stage_rec["suggest"]:
            if skill_name not in seen:
                recommendations.append({
                    "name": skill_name,
                    "reason": stage_rec["message"],
                    "trigger": f"project_stage:{stage}",
                    "priority": "high",
                })
                seen.add(skill_name)

    # 2. 基于技术栈的推荐
    tech_stack = ctx.get("tech_stack", [])
    features = ctx.get("features", [])

    # 技术栈本身
    for tech in tech_stack:
        if tech in TECHSTACK_RECOMMENDATIONS:
            rec = TECHSTACK_RECOMMENDATIONS[tech]
            for skill_name in rec["skills"]:
                if skill_name not in seen:
                    recommendations.append({
                        "name": skill_name,
                        "reason": rec["reason"],
                        "trigger": f"tech_stack:{tech}",
                        "priority": "medium",
                    })
                    seen.add(skill_name)

    # 特性标签（payment, auth 等）
    for feat in features:
        if feat in TECHSTACK_RECOMMENDATIONS:
            rec = TECHSTACK_RECOMMENDATIONS[feat]
            for skill_name in rec["skills"]:
                if skill_name not in seen:
                    recommendations.append({
                        "name": skill_name,
                        "reason": rec["reason"],
                        "trigger": f"feature:{feat}",
                        "priority": "high",
                    })
                    seen.add(skill_name)

    # 3. 基于用户显式描述（语义搜索增强）
    if user_text:
        try:
            from semantic_search import search, load_skills_for_search
            skills = load_skills_for_search()
            if skills:
                search_results, engine = search(user_text, skills, top_n=5)
                for skill, score in search_results:
                    name = skill.get("name", skill.get("slug", "?"))
                    if name not in seen and score > 0.3:
                        recommendations.append({
                            "name": name,
                            "reason": f"匹配你的描述「{user_text}」(置信度 {score:.0%})",
                            "trigger": f"semantic_search:{engine}",
                            "priority": "high" if score > 0.6 else "medium",
                            "score": round(score, 4),
                        })
                        seen.add(name)
        except ImportError:
            pass  # semantic_search 不可用就跳过

    # 排序：high 优先
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))

    return {
        "stage": stage,
        "project_type": ctx.get("type", "unknown"),
        "tech_stack": tech_stack,
        "context_message": STAGE_RECOMMENDATIONS.get(stage, {}).get("message", ""),
        "recommendations": recommendations[:8],
        "has_git": ctx.get("has_git", False),
        "total_dependencies": ctx.get("dependencies", 0) + ctx.get("dev_dependencies", 0),
    }


# ============================================================
# 状态管理（防止重复推荐）
# ============================================================

ADVISOR_STATE_FILE = CACHE_DIR / "advisor_state.json"


def load_advisor_state():
    """加载推荐状态（上次推荐时间、已忽略的推荐等）"""
    if ADVISOR_STATE_FILE.exists():
        try:
            return json.loads(ADVISOR_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_recommendations": {}, "last_check": 0, "dismissed": []}


def save_advisor_state(state):
    """保存推荐状态到本地 JSON 文件"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ADVISOR_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def should_recommend(ctx, force=False):
    """
    判断是否应该推荐（避免重复打扰）
    返回 True/False
    """
    if force:
        return True
    state = load_advisor_state()
    # 同一项目、同一阶段，1小时内不重复推荐
    project_key = f"{ctx.get('path', '')}:{ctx.get('stage', '')}"
    last = state.get("last_recommendations", {}).get(project_key, 0)
    if time.time() - last < 3600:  # 1h
        return False
    return True


def mark_recommended(ctx):
    """标记已推荐（记录推荐时间，避免重复推荐）"""
    state = load_advisor_state()
    project_key = f"{ctx.get('path', '')}:{ctx.get('stage', '')}"
    state.setdefault("last_recommendations", {})[project_key] = time.time()
    save_advisor_state(state)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Context Advisor —— 上下文感知技能推荐")
    parser.add_argument("user_text", nargs="?", help="用户描述（可选）")
    parser.add_argument("--cwd", default=".", help="项目路径")
    parser.add_argument("--mode", choices=["manual", "hook", "session", "check"], default="manual")
    parser.add_argument("--force", action="store_true", help="强制推荐（忽略防重复）")
    parser.add_argument("--profile", action="store_true", help="仅输出上下文信息")
    args = parser.parse_args()

    # 1. 分析上下文
    ctx = analyze_project_context(args.cwd)

    if args.profile:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 2. 快速检查模式
    if args.mode == "check":
        recs = generate_advisor_recommendations(ctx, args.user_text)
        top = recs["recommendations"][:3]
        print(json.dumps({
            "stage": recs["stage"],
            "project_type": recs["project_type"],
            "top_recommendations": top,
            "should_interrupt": len(top) > 0 and any(r.get("priority") == "high" for r in top),
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 3. Hook 模式：简洁 + 防重复
    if args.mode == "hook":
        if not should_recommend(ctx, force=args.force):
            print(json.dumps({"skip": True, "reason": "already_recently_recommended"}, ensure_ascii=False))
            sys.exit(0)
        recs = generate_advisor_recommendations(ctx, args.user_text)
        top = recs["recommendations"][:3]
        if top:
            mark_recommended(ctx)
        output = {
            "skip": False,
            "stage": recs["stage"],
            "message": recs["context_message"],
            "recommendations": top,
            "should_interrupt": any(r.get("priority") == "high" for r in top) and len(top) >= 2,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 4. 手动/会话模式：完整输出
    recs = generate_advisor_recommendations(ctx, args.user_text)
    recs["mode"] = args.mode
    recs["should_interrupt"] = args.mode == "session" and len(recs["recommendations"]) >= 2
    print(json.dumps(recs, ensure_ascii=False, indent=2))
