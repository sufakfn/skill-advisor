#!/usr/bin/env python3
"""Context Advisor v2.0 - Proactive Recommendation Engine"""

import json, os, time
from pathlib import Path

CONFIG_DIR = Path.home() / ".skill-advisor"
CONFIG_FILE = CONFIG_DIR / "config.toml"
FEEDBACK_FILE = CONFIG_DIR / "feedback.json"
STATE_FILE = CONFIG_DIR / "state.json"

def load_config():
    defaults = {"advisor": {"level": "balanced", "cooldown_minutes": 60, "max_per_session": 5}, "language": {"default": "zh"}}
    try:
        import tomllib
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                user_cfg = tomllib.load(f)
            for section, values in user_cfg.items():
                if section in defaults:
                    defaults[section].update(values)
    except:
        pass
    return defaults

def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except:
        pass
    return {"recommendations": [], "session_count": 0}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def load_feedback():
    try:
        if FEEDBACK_FILE.exists():
            return json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
    except:
        pass
    return {"dismissed": [], "installed": [], "not_needed": []}

def save_feedback(feedback):
    FEEDBACK_FILE.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")

def should_recommend(skill_name, config, state):
    """Should we recommend this skill? Returns (bool, reason)"""
    level = config.get("advisor", {}).get("level", "balanced")
    if level == "off":
        return False, "disabled"
    cooldown = config.get("advisor", {}).get("cooldown_minutes", 60)
    now = time.time()
    for rec in state.get("recommendations", []):
        if rec.get("skill") == skill_name:
            elapsed = (now - rec.get("timestamp", 0)) / 60
            if elapsed < cooldown:
                return False, "cooldown"
    if state.get("session_count", 0) >= config.get("advisor", {}).get("max_per_session", 5):
        return False, "session limit"
    feedback = load_feedback()
    if skill_name in feedback.get("dismissed", []):
        return False, "dismissed"
    if skill_name in feedback.get("not_needed", []):
        return False, "not needed"
    return True, "ok"

def record_recommendation(skill_name, state):
    state.setdefault("recommendations", [])
    state["recommendations"].append({"skill": skill_name, "timestamp": time.time()})
    state["session_count"] = state.get("session_count", 0) + 1
    save_state(state)

def record_feedback(skill_name, action):
    feedback = load_feedback()
    for key in ["dismissed", "installed", "not_needed"]:
        if skill_name in feedback.get(key, []):
            feedback[key].remove(skill_name)
    feedback.setdefault(action, []).append(skill_name)
    save_feedback(feedback)

if __name__ == "__main__":
    config = load_config()
    state = load_state()
    print("Config:", config)
    ok, reason = should_recommend("react-best-practices", config, state)
    print(f"Should recommend: {ok} ({reason})")
