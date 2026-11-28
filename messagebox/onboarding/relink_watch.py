"""Re-enter setup on the current Wi-Fi when WhatsApp logs a channel box out.

Runs as root from messagebox-relink-watch.timer. A box WhatsApp has logged out
can neither send nor receive, and channel boxes have no dashboard, so setup is
the only way to relink. Wi-Fi is kept; the household opens the setup page and
pairs again. Only clean "not authenticated" answers count, twice in a row.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from messagebox.contacts import configured_channels
from messagebox.onboarding.paths import (
    MESSAGEBOX_HOME,
    ONBOARDING_CONFIGURED_PATH,
    ONBOARDING_ENABLED_PATH,
    WACLI_PATH,
    WHATSAPP_LIVE_STORE,
)
from messagebox.onboarding.reset import perform_reset


COUNT_PATH = Path("/run/messagebox-relink-watch/logged-out")
CONFIRMATIONS = 2
# Read-only and as the store's owner, so root never creates files in it.
AUTH_COMMAND = [
    "runuser", "-u", "messagebox", "--", "env",
    f"HOME={MESSAGEBOX_HOME}", f"WACLI_STORE_DIR={WHATSAPP_LIVE_STORE}",
    str(WACLI_PATH), "--read-only", "--json", "auth", "status",
]


def authenticated(run):
    """True/False from a clean wacli answer; None when the check itself failed."""
    try:
        result = run(AUTH_COMMAND, capture_output=True, text=True, timeout=30, check=False)
        document = json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if isinstance(document, dict) and isinstance(document.get("data"), dict):
        document = document["data"]
    value = document.get("authenticated") if isinstance(document, dict) else None
    return value if isinstance(value, bool) else None


def check(
    *,
    run=subprocess.run,
    reset=perform_reset,
    channels=None,
    count_path=COUNT_PATH,
    enabled_path=ONBOARDING_ENABLED_PATH,
    configured_path=ONBOARDING_CONFIGURED_PATH,
):
    channels = configured_channels() if channels is None else channels
    if not channels or Path(enabled_path).exists() or not Path(configured_path).is_file():
        return "skipped"
    state = authenticated(run)
    count_path = Path(count_path)
    if state is True:
        count_path.unlink(missing_ok=True)
        return "authenticated"
    if state is None:
        return "unknown"
    try:
        count = int(count_path.read_text(encoding="ascii")) + 1
    except (OSError, ValueError):
        count = 1
    if count < CONFIRMATIONS:
        count_path.write_text(str(count), encoding="ascii")
        return "logged-out"
    count_path.unlink(missing_ok=True)
    reset(runner=run, keep_wifi=True)
    return "relink"


def main():
    try:
        result = check()
    except Exception as exc:
        print(f"relink watch failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"relink watch: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
