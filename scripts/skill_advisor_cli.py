#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-advisor CLI — 统一入口，支持搜索、更新、统计。

用法:
  python scripts/skill_advisor_cli.py search "query"         # 搜索（自动检查更新）
  python scripts/skill_advisor_cli.py search "query" --no-sync  # 搜索（跳过更新检查）
  python scripts/skill_advisor_cli.py sync                   # 手动同步最新数据
  python scripts/skill_advisor_cli.py stats                  # 显示统计
  python scripts/skill_advisor_cli.py rebuild-vectors        # 重建向量索引

自动同步逻辑:
  - 每次 search 时检查距上次同步是否超过 24h
  - 超过则后台 git pull（不阻塞搜索）
  - 有新数据 → 增量重建向量索引
"""

import os
import sys

# 修复 Windows GBK 编码
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

import argparse
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "data" / "skill-advisor.db"
SYNC_STATE_PATH = ROOT_DIR / "data" / ".sync_state"
VECTOR_DEPENDENCY_INSTALLED = False

# 尝试导入向量依赖
try:
    from skill_advisor.vector_search import search_vector, get_engine_status
    VECTOR_DEPENDENCY_INSTALLED = True
except ImportError:
    pass

from skill_advisor.search import search_skills, search_hybrid, get_stats


def get_last_sync_time():
    """获取上次同步时间戳"""
    if SYNC_STATE_PATH.exists():
        try:
            return float(SYNC_STATE_PATH.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def set_last_sync_time():
    """记录当前同步时间"""
    SYNC_STATE_PATH.write_text(str(time.time()))


def should_auto_sync(interval_hours=24):
    """检查是否应该自动同步"""
    last = get_last_sync_time()
    if last == 0:
        return True
    elapsed = time.time() - last
    return elapsed > (interval_hours * 3600)


def git_pull():
    """静默执行 git pull，返回 (success, message)"""
    try:
        result = subprocess.run(
            ["git", "pull", "--quiet"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "已同步到最新"
        else:
            return False, result.stderr.strip() or "同步失败"
    except subprocess.TimeoutExpired:
        return False, "同步超时"
    except FileNotFoundError:
        return False, "git 未安装（跳过同步）"
    except Exception as e:
        return False, f"同步错误: {e}"


def check_git_available():
    """检查是否在 git 仓库中"""
    git_dir = ROOT_DIR / ".git"
    return git_dir.exists()


def rebuild_vectors_safely():
    """安全地重建向量索引（如果依赖可用）"""
    if not VECTOR_DEPENDENCY_INSTALLED:
        return False, "向量依赖未安装 (pip install -e '.[vector]')"
    try:
        from build_vectors import build_all
        conn = sqlite3.connect(str(DB_PATH))
        result = build_all(conn, incremental=False)  # 全量重建
        conn.close()
        return True, f"向量索引已重建: {result['built']} 条"
    except Exception as e:
        return False, f"向量重建失败: {e}"


def cmd_search(query, limit=10, online=True, no_sync=False, engine="auto"):
    """搜索命令"""

    # 自动同步检查
    synced = False
    if not no_sync and check_git_available():
        if should_auto_sync():
            print("🔄 检查数据更新...", flush=True)
            ok, msg = git_pull()
            if ok:
                synced = True
                set_last_sync_time()
                print(f"  ✅ {msg}", flush=True)
            else:
                print(f"  ⚠️ {msg}", flush=True)

    # 执行搜索
    if engine == "vector" and VECTOR_DEPENDENCY_INSTALLED:
        result = search_hybrid(query, limit=limit)
    else:
        result = search_skills(query, limit=limit, online=online)

    # 输出结果
    results = result.get("results") or result.get("local_results", [])
    source = result.get("source", "local")
    elapsed = result.get("elapsed_ms", 0)

    print()
    print("=" * 55)
    print(f'🔍 "{query}" — {len(results)} 个结果 ({elapsed}ms)')
    if synced:
        print("📦 数据已自动同步到最新")
    print("=" * 55)

    for i, r in enumerate(results, 1):
        name = r.get("name", "?")
        desc = r.get("description", "")
        inst = r.get("installs", 0)
        rel = r.get("relevance")
        src = r.get("source", "")

        # 截断描述
        if desc and len(desc) > 80:
            desc = desc[:77] + "..."

        # 格式化输出
        line = f"  {i:>2}. {name}"
        if rel is not None:
            line += f" (相关度: {rel:.0%})"
        if inst > 0:
            line += f"  ↓{inst:,}"
        print(line)

        if desc:
            print(f"      {desc}")

        if src:
            print(f"      来源: {src}")

    print("=" * 55)

    # 提示
    if not VECTOR_DEPENDENCY_INSTALLED:
        print("💡 安装向量搜索: pip install -e '.[vector]'")

    return results


def cmd_sync():
    """手动同步命令"""
    if not check_git_available():
        print("❌ 不是 git 仓库，无法同步")
        print("   如果是 pip 安装，请改用: pip install --upgrade skill-advisor")
        return False

    print("🔄 同步最新数据...")
    ok, msg = git_pull()
    if ok:
        print(f"  ✅ {msg}")
        set_last_sync_time()

        # 检查是否是新数据库，尝试重建向量
        stats = get_stats()
        if stats.get("total_skills", 0) > 0:
            print(f"  📊 数据库: {stats['total_skills']:,} 技能")
            if VECTOR_DEPENDENCY_INSTALLED:
                print("  🔄 重建向量索引...")
                ok2, msg2 = rebuild_vectors_safely()
                print(f"    {'✅' if ok2 else '⚠️'} {msg2}")
        return True
    else:
        print(f"  ❌ {msg}")
        return False


def cmd_stats():
    """统计命令"""
    stats = get_stats()
    print()
    print("=" * 50)
    print("📊 skill-advisor 统计")
    print("=" * 50)
    print(f"  总技能:     {stats.get('total_skills', 0):>8,}")
    print(f"  有描述:     {stats.get('with_description', 0):>8,}")
    print(f"  数据库大小: {stats.get('database_size_mb', 0):>8.1f} MB")
    print(f"  路径:       {stats.get('database_path', '?')}")

    if VECTOR_DEPENDENCY_INSTALLED:
        vs = get_engine_status()
        print(f"  向量引擎:   {vs.get('engine', '?')}")
        print(f"  向量数量:   {vs.get('count', 0):>8,}")

    # 上次同步
    last = get_last_sync_time()
    if last > 0:
        age_hours = (time.time() - last) / 3600
        print(f"  上次同步:   {age_hours:.1f} 小时前")
    else:
        print(f"  上次同步:   从未")

    print("=" * 50)


def main():
    import os
    # 离线模式，避免网络检查延迟
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    parser = argparse.ArgumentParser(
        description="skill-advisor CLI — 智能技能推荐",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s search "react 最佳实践"
  %(prog)s search "做演示" --limit 5
  %(prog)s search "query" --no-sync  # 跳过自动同步
  %(prog)s sync                       # 手动同步最新数据
  %(prog)s stats                      # 显示统计
  %(prog)s warm-up                    # 预加载模型（加速首次搜索）
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # search
    p_search = subparsers.add_parser("search", help="搜索技能")
    p_search.add_argument("query", help="搜索词")
    p_search.add_argument("--limit", type=int, default=10, help="结果数量")
    p_search.add_argument("--no-sync", action="store_true", help="跳过自动同步")
    p_search.add_argument("--online", action="store_true", help="允许在线搜索")
    p_search.add_argument("--engine", choices=["auto", "vector", "fts"], default="auto")

    # sync
    subparsers.add_parser("sync", help="同步最新数据")

    # stats
    subparsers.add_parser("stats", help="显示统计")

    # rebuild-vectors
    subparsers.add_parser("rebuild-vectors", help="重建向量索引")

    # warm-up
    subparsers.add_parser("warm-up", help="预加载模型（加速首次搜索）")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args.query, limit=args.limit, online=args.online,
                   no_sync=args.no_sync, engine=args.engine)
    elif args.command == "sync":
        cmd_sync()
    elif args.command == "stats":
        cmd_stats()
    elif args.command == "rebuild-vectors":
        ok, msg = rebuild_vectors_safely()
        print(f"{'✅' if ok else '❌'} {msg}")
    elif args.command == "warm-up":
        # 预加载模型
        from skill_advisor import warm_up
        if warm_up():
            print("✅ 模型预加载成功，后续搜索将更快")
        else:
            print("⚠️ 模型加载失败，向量搜索不可用（FTS5 搜索仍可用）")
    else:
        # 默认：如果没有子命令，把整个参数当作搜索词
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            cmd_search(" ".join(sys.argv[1:]))
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
