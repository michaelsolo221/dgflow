#!/usr/bin/env python3
"""
Pre-commit / CI check: every app.json session param with an empty default must be
set by at least one callback. Catches the 'declared but never injected' class of bug.

Usage:
    python night-line/scripts/check_session_params.py
"""

import json
import re
import sys
from pathlib import Path

APP_JSON = Path("night-line/cxas_app/NightLine/app.json")
CALLBACKS_ROOT = Path("night-line/cxas_app/NightLine/agents")

# Params auto-injected by the CXAS telephony platform — not set by our callbacks.
PLATFORM_INJECTED = {"caller_id"}

app = json.loads(APP_JSON.read_text())
declarations = app.get("variableDeclarations", [])

# Params with empty defaults are the ones that MUST be set at runtime by a callback.
unset_params = [
    d["name"]
    for d in declarations
    if d.get("schema", {}).get("default", None) == "" and d["name"] not in PLATFORM_INJECTED
]

if not unset_params:
    sys.exit(0)

# Grep all callback python_code.py files for state["<name>"] assignments.
callback_sources = "\n".join(p.read_text() for p in CALLBACKS_ROOT.rglob("*/python_code.py"))

missing = []
for param in unset_params:
    pattern = rf"state\[.{re.escape(param)}.\]\s*="
    if not re.search(pattern, callback_sources):
        missing.append(param)

if missing:
    print("ERROR: app.json declares session params with empty defaults that no callback sets:")
    for p in missing:
        print(f"  - {p}")
    print("Add a state assignment in the relevant before_agent_callback init, or set a non-empty default in app.json.")
    sys.exit(1)

print(f"OK: all {len(unset_params)} empty-default session params are set by callbacks.")
