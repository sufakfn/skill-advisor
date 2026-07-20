#!/usr/bin/env python3
"""Phase 4.9 - Install Confirmation Prompt"""

import json
import sys
from pathlib import Path

def confirm_install(skill_name, safety="unverified"):
    """Show install confirmation prompt for non-official skills"""
    if safety == "safe":
        return True  # No prompt for known-safe sources
    
    print(f"⚠️  Installing non-verified skill: {skill_name}")
    print(f"   Safety status: {safety}")
    print(f"   ")
    print(f"   Only install skills from trusted sources.")
    print(f"   Review the skill code before use.")
    print(f"   ")
    response = input("Proceed with installation? [y/N]: ")
    return response.lower().strip() == "y"

if __name__ == "__main__":
    skill = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    safety = sys.argv[2] if len(sys.argv) > 2 else "unverified"
    ok = confirm_install(skill, safety)
    sys.exit(0 if ok else 1)
