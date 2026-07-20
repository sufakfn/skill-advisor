"""Agent 安装路径注册表"""

AGENT_PATHS = {
    "claude-code": {
        "path": "~/.claude/skills/",
        "install_cmd": "cp -r {src} ~/.claude/skills/{name}/",
    },
    "cursor": {
        "path": "~/.cursor/skills/",
        "install_cmd": "cp -r {src} ~/.cursor/skills/{name}/",
    },
    "codex-cli": {
        "path": "~/.codex/skills/",
        "install_cmd": "cp -r {src} ~/.codex/skills/{name}/",
    },
    "gemini-cli": {
        "path": "~/.gemini/skills/",
        "install_cmd": "cp -r {src} ~/.gemini/skills/{name}/",
    },
    "vscode-copilot": {
        "path": "~/.vscode/skills/",
        "install_cmd": "cp -r {src} ~/.vscode/skills/{name}/",
    },
    "continue": {
        "path": "~/.continue/skills/",
        "install_cmd": "cp -r {src} ~/.continue/skills/{name}/",
    },
    "cline": {
        "path": "~/.cline/skills/",
        "install_cmd": "cp -r {src} ~/.cline/skills/{name}/",
    },
    "aider": {
        "path": "~/.aider/skills/",
        "install_cmd": "cp -r {src} ~/.aider/skills/{name}/",
    },
    "windsurf": {
        "path": "~/.windsurf/skills/",
        "install_cmd": "cp -r {src} ~/.windsurf/skills/{name}/",
    },
    "trae": {
        "path": "~/.trae/skills/",
        "install_cmd": "cp -r {src} ~/.trae/skills/{name}/",
    },
    "openclaw": {
        "path": "~/.openclaw/skills/",
        "install_cmd": "cp -r {src} ~/.openclaw/skills/{name}/",
    },
    "roo": {
        "path": "~/.roo/skills/",
        "install_cmd": "cp -r {src} ~/.roo/skills/{name}/",
    },
    "goose": {
        "path": "~/.goose/skills/",
        "install_cmd": "cp -r {src} ~/.goose/skills/{name}/",
    },
    "amp": {
        "path": "~/.amp/skills/",
        "install_cmd": "cp -r {src} ~/.amp/skills/{name}/",
    },
}


def get_install_command(agent, src, name):
    """获取指定 agent 的安装命令"""
    agent_cfg = AGENT_PATHS.get(agent)
    if not agent_cfg:
        return f"cp -r {src} ~/.{agent}/skills/{name}/"
    return agent_cfg["install_cmd"].format(src=src, name=name)


def list_agents():
    """列出所有支持的 agent"""
    return list(AGENT_PATHS.keys())
