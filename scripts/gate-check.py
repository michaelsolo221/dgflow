"""Pre-push gate checks — run before cxas push."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GECX_CONFIG = ROOT / "night-line" / "gecx-config.json"


def check_deployed_app_id():
    """Gate: deployed_app_id must be non-null (populated by first cxas push)."""
    config = json.loads(GECX_CONFIG.read_text())
    app_id = config.get("deployed_app_id")
    if not app_id:
        print("FAIL: deployed_app_id is null. Run `cxas push` first to create the app on the platform.")
        return False
    print(f"OK: deployed_app_id = {app_id}")
    return True


def main():
    ok = True
    ok &= check_deployed_app_id()
    # ponytail: add more gates as the build matures
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
