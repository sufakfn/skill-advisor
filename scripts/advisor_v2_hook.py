#!/usr/bin/env python3
"""PostToolUse hook - 文件保存后自动分析并推荐技能"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

def main():
    # 读取 hook 输入（Claude Code 通过 stdin 传递上下文）
    try:
        hook_input = json.loads(sys.stdin.read())
    except:
        hook_input = {}
    
    # 获取修改的文件路径
    file_path = hook_input.get("file_path", "")
    tool_name = hook_input.get("tool_name", "")
    
    if not file_path:
        return
    
    # 加载 advisor v2
    sys.path.insert(0, str(SCRIPT_DIR))
    from advisor_v2 import load_config, load_state, should_recommend, record_recommendation
    from advisor import analyze_project_context, get_stage_recommendations
    
    config = load_config()
    state = load_state()
    level = config.get("advisor", {}).get("level", "balanced")
    
    if level == "off":
        return
    if level == "quiet":
        return  # quiet 模式不打扰
    
    # 分析项目上下文
    try:
        ctx = analyze_project_context()
        stage = ctx.get("stage", "unknown")
        tech_stack = ctx.get("tech_stack", [])
        recommendations = get_stage_recommendations(stage, tech_stack)
    except:
        return
    
    # 过滤 + 推荐
    for rec in recommendations[:3]:
        skill = rec if isinstance(rec, str) else rec.get("name", "")
        if not skill:
            continue
        ok, reason = should_recommend(skill, config, state)
        if ok:
            record_recommendation(skill, state)
            # 输出给 Claude（Claude 决定是否展示）
            print(f"[advisor] Detected {stage} stage. Consider: {skill}")
            break  # 每次只推荐 1 个

if __name__ == "__main__":
    main()
