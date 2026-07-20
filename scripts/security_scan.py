#!/usr/bin/env python3
"""Phase 4.7 - Skill Security Scanner"""

import json, os, re, sqlite3, sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "skills.db"

SUSPICIOUS = {
    "dangerful_cmd": [r"rm\s+-rf\s+/", r"curl.*\|.*sh", r"wget.*\|.*sh"],
    "data_exfil": [r"requests\.(post|put)\s*\(", r"urllib.*urlopen", r"socket\s*\("],
    "obfuscation": [r"base64\.(b64decode|decode)", r"codecs\.decode", r"marshal\.loads"],
}

SEVERITY = {"dangerful_cmd": "HIGH", "data_exfil": "MEDIUM", "obfuscation": "MEDIUM"}

def scan_content(content, source="unknown"):
    findings = []
    for cat, patterns in SUSPICIOUS.items():
        for p in patterns:
            m = re.findall(p, content, re.IGNORECASE)
            if m:
                findings.append({"category": cat, "severity": SEVERITY.get(cat, "LOW"), "count": len(m), "source": source})
    return findings

def scan_dir(skill_dir):
    findings = []
    for f in Path(skill_dir).rglob("*"):
        if f.is_file() and f.suffix in (".md", ".py", ".sh", ".js"):
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                findings.extend(scan_content(content, str(f)))
            except Exception:
                pass
    return findings

def risk_level(findings):
    if not findings:
        return "SAFE"
    sevs = [f["severity"] for f in findings]
    if "HIGH" in sevs:
        return "HIGH"
    elif "MEDIUM" in sevs:
        return "MEDIUM"
    return "LOW"

def main():
    if len(sys.argv) < 2:
        print("Usage: python security_scan.py <skill_dir>")
        sys.exit(1)
    findings = scan_dir(sys.argv[1])
    risk = risk_level(findings)
    print("Risk: " + risk + ", " + str(len(findings)) + " findings")
    for f in findings[:5]:
        line = "  [" + f["severity"] + "] " + f["category"] + ": " + str(f["count"]) + " matches"
        print(line)

if __name__ == "__main__":
    main()
