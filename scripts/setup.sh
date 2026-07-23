#!/bin/bash
# 首次使用自动配置钩子
# 每次启动 Claude Code 时自动拉取最新数据

HOOK_DIR=~/.claude/hooks
HOOK_FILE="$HOOK_DIR/post_session_start.sh"

mkdir -p "$HOOK_DIR"

# 检查是否已配置
if grep -q "skill-advisor" "$HOOK_FILE" 2>/dev/null; then
  echo "auto-update already configured"
  exit 0
fi

# 添加自动更新命令
echo '' >> "$HOOK_FILE"
echo '# skill-advisor: auto-update database' >> "$HOOK_FILE"
echo 'cd ~/.claude/skills/skill-advisor && git pull --quiet 2>/dev/null || true' >> "$HOOK_FILE"

# 确保可执行
chmod +x "$HOOK_FILE" 2>/dev/null || true

echo "auto-update configured successfully"
