"""i18n manager - runtime language switching"""

import json
from pathlib import Path

I18N_DIR = Path(__file__).parent / "i18n"
_translations = {}
_current_lang = "zh"

DEFAULT_TRANSLATIONS = {
    "search_placeholder": "Search skills...",
    "search_button": "Search",
    "results_count": "{count} results",
    "no_results": "No skills found",
    "safety_safe": "Verified",
    "safety_unverified": "Unverified",
    "professor_pack": "Profession Packs",
    "combo_guide": "Combo Guide",
    "required": "Required",
    "suggested": "Suggested",
    "later": "Later",
}


def load_language(lang):
    global _translations, _current_lang
    _current_lang = lang
    try:
        f = I18N_DIR / (lang + ".json")
        if f.exists():
            _translations = json.loads(f.read_text(encoding="utf-8"))
        else:
            _translations = DEFAULT_TRANSLATIONS
    except:
        _translations = DEFAULT_TRANSLATIONS


def t(key, **kwargs):
    """Get translation for key"""
    text = _translations.get(key, DEFAULT_TRANSLATIONS.get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_language():
    """Get current language from config"""
    try:
        cfg_path = Path.home() / ".skill-advisor" / "config.toml"
        if cfg_path.exists():
            import tomllib
            with open(cfg_path, "rb") as f:
                cfg = tomllib.load(f)
            return cfg.get("language", {}).get("default", "zh")
    except:
        pass
    return "zh"


def set_language(lang):
    """Set language and reload"""
    load_language(lang)
    # Persist to config
    try:
        cfg_path = Path.home() / ".skill-advisor" / "config.toml"
        cfg_path.parent.mkdir(exist_ok=True)
        if cfg_path.exists():
            content = cfg_path.read_text(encoding="utf-8")
        else:
            content = "[language]" + chr(10) + "default = \"zh\"" + chr(10)
        lines = content.split(chr(10))
        for i, line in enumerate(lines):
            if line.startswith("default ="):
                lines[i] = "default = \"" + lang + "\""
                break
        cfg_path.write_text(chr(10).join(lines), encoding="utf-8")
    except:
        pass


def list_languages():
    """List available languages"""
    return ["zh", "en", "ja", "ko"]


# Auto-load on import
load_language(get_language())
