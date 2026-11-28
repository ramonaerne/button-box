#!/bin/sh
# Developer-only: copy changed runtime Python and the dev runner onto an
# already provisioned test box, then restart the runtime services that are
# running. Only files that setup already installed are replaced (--existing);
# new files, units, sounds, packages or config still need scripts/provision.sh.
# The box's installed-code manifest no longer matches afterwards, so use this
# on test boxes only.
set -eu

[ "$#" -eq 1 ] || { echo "Usage: $0 user@host" >&2; exit 2; }
TARGET=$1
case "$TARGET" in
  -*|*[!A-Za-z0-9._@-]*) echo "Invalid SSH target: $TARGET" >&2; exit 2 ;;
esac

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

# Keep repository modes (syncloop.sh is executable) but install as root.
rsync -rlpt --checksum --existing --itemize-changes --exclude __pycache__ \
  --chown=root:root --rsync-path="sudo rsync" \
  "$REPO_DIR/messagebox/" "$TARGET:/opt/messagebox/messagebox/"
rsync -pt --checksum --itemize-changes --chown=root:root --chmod=F755 \
  --rsync-path="sudo rsync" \
  "$REPO_DIR/scripts/dev/virtual-buttons.py" "$TARGET:/opt/messagebox/dev/virtual-buttons.py"

# Sync is left running: restarting it drops the WhatsApp connection, and sends
# fail with "store is locked" until it reconnects. Restart it by hand after
# changing syncloop.sh.
ssh "$TARGET" sudo systemctl try-restart \
  messagebox-button.service messagebox-poller.service messagebox-dash.service
echo "Pushed; running button, poller and dashboard services were restarted."
