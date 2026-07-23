#!/bin/bash
# 首次使用配置
# 检查数据库年龄，超过 7 天提示更新

DB_PATH="$HOME/.claude/skills/skill-advisor/data/skill-advisor.db"

if [ ! -f "$DB_PATH" ]; then
  echo "⚠️ 数据库不存在，请运行: cd ~/.claude/skills/skill-advisor && git pull"
  exit 1
fi

# 检查文件修改时间（天）
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  AGE_DAYS=$(( ($(date +%s) - $(stat -f %m "$DB_PATH")) / 86400 ))
else
  # Linux / Git Bash
  AGE_DAYS=$(( ($(date +%s) - $(stat -c %Y "$DB_PATH")) / 86400 ))
fi

if [ "$AGE_DAYS" -ge 7 ]; then
  echo "⚠️ 数据库已 ${AGE_DAYS} 天未更新，建议运行:"
  echo "   cd ~/.claude/skills/skill-advisor && git pull"
  echo ""
  echo "或在 skill 内使用 'skill-advisor sync' 命令更新。"
else
  echo "✅ 数据库已是最新（${AGE_DAYS} 天前更新）"
fi
