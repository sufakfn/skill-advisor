"""
skill-advisor CLI 入口点 — 供 setuptools [project.scripts] 调用。

用法:
    skill-advisor search "query"         # 搜索（自动检查更新）
    skill-advisor search "query" --no-sync  # 搜索（跳过更新检查）
    skill-advisor sync                   # 手动同步最新数据
    skill-advisor stats                  # 显示统计
    skill-advisor rebuild-vectors        # 重建向量索引
"""

import os
import sys
from pathlib import Path

# 修复 Windows GBK 编码问题
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# 确保 scripts 目录在 path 中
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from skill_advisor_cli import main

if __name__ == "__main__":
    main()
