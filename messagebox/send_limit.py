"""Per-channel send limit: at most N sends until a newer reply is played (D15).

State is one small JSON document keyed by channel number. Each entry keeps a
hash of the bound chat, so a rebind starts that channel at zero, and never
stores the chat identifier itself.
"""

import hashlib
import json
from pathlib import Path

from messagebox.cloud_device import atomic_json


def _chat_key(chat):
    return hashlib.sha256(chat.encode("utf-8")).hexdigest()[:16]


def _load(path):
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        # A limit is not a safety boundary; an unreadable counter restarts at
        # zero rather than locking the button forever.
        return {}
    return document if isinstance(document, dict) else {}


def _entry(document, channel, chat):
    entry = document.get(str(channel))
    if (not isinstance(entry, dict) or entry.get("chat") != _chat_key(chat)
            or type(entry.get("count")) is not int or type(entry.get("since_ms")) is not int):
        return {"chat": _chat_key(chat), "count": 0, "since_ms": 0}
    return entry


def limit_reached(path, channel, chat, limit):
    """Return True when this channel already used its sends for the bound chat."""
    if not limit:
        return False
    return _entry(_load(path), channel, chat)["count"] >= limit


def record_send(path, channel, chat, sent_ms):
    """Count one send accepted into the outbox."""
    document = _load(path)
    entry = _entry(document, channel, chat)
    document[str(channel)] = {**entry, "count": entry["count"] + 1, "since_ms": sent_ms}
    atomic_json(Path(path), document)


def record_played(path, channel, chat, arrived_ms):
    """Reset the channel when a reply that arrived after its last send is played."""
    document = _load(path)
    entry = _entry(document, channel, chat)
    if entry["count"] and arrived_ms > entry["since_ms"]:
        document[str(channel)] = {**entry, "count": 0}
        atomic_json(Path(path), document)
