#!/usr/bin/env python3
"""Developer-only: run the button runtime with buttons typed in the terminal.

Runs the real messagebox.button_send loop on gpiozero mock pins, so routing,
queueing, sending and playback behave as in the service. Stop the service
first because this process takes its place:

    sudo systemctl stop messagebox-button.service
    sudo -u messagebox -H python3 /opt/messagebox/dev/virtual-buttons.py

Commands: "t 1" taps button 1, "h 1 5" holds button 1 for 5 s, "q" quits.
LED changes are printed. Recording always uses a fake microphone (a tone, or
a looped WAV given with --mic-file): terminal input must never open the real
microphone, which stays reserved for physical presses (docs/mic-access-audit.md).
Without a speaker, run with MSGBOX_SPK_DEV=null in the environment.
"""

import argparse
import os
import shlex
import sys
import tempfile
import threading
import time
from pathlib import Path

# Installed at /opt/messagebox/dev; the package lives in /opt/messagebox.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Stands in for mic_capture's "arecord -t raw -f S16_LE -r 16000 -c 1" to stdout.
FAKE_ARECORD = """#!/bin/sh
exec ffmpeg -loglevel error -nostdin -re {source} -ac 1 -ar 16000 -f s16le -
"""


def load_env_file(path):
    """Apply KEY=VALUE lines like systemd EnvironmentFile; real env wins."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        key, separator, value = line.strip().partition("=")
        if separator and key and not key.startswith("#"):
            os.environ.setdefault(key, value)


def install_fake_mic(wav):
    source = (
        f"-stream_loop -1 -i {shlex.quote(wav)}"
        if wav
        else "-f lavfi -i sine=frequency=440:sample_rate=48000"
    )
    directory = tempfile.mkdtemp(prefix="fake-mic-")
    shim = Path(directory) / "arecord"
    shim.write_text(FAKE_ARECORD.format(source=source), encoding="utf-8")
    shim.chmod(0o700)
    os.environ["PATH"] = f"{directory}:{os.environ.get('PATH', '')}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mic-file", default="", metavar="WAV", help="loop WAV instead of a tone"
    )
    options = parser.parse_args()

    os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
    os.environ.setdefault("WACLI_STORE_DIR", "/var/lib/messagebox/wacli")
    load_env_file("/etc/messagebox/env")
    load_env_file("/run/messagebox-audio/audio.env")
    install_fake_mic(options.mic_file)

    from gpiozero import Device

    import messagebox.button_send as runtime

    pairs = runtime.parse_channel_pins(runtime.CHANNEL_PINS) or [
        ("1", runtime.BUTTON_PIN, runtime.LED_PIN)
    ]
    runtime_thread = threading.Thread(target=runtime.main, daemon=True)
    runtime_thread.start()
    time.sleep(1)  # Let main() claim the pins before we touch them.
    if not runtime_thread.is_alive():
        print("runtime stopped; see output above")
        return 1
    factory = Device.pin_factory
    buttons = {number: factory.pin(pin) for number, pin, _ in pairs}
    leds = {number: factory.pin(pin) for number, _, pin in pairs}

    def watch_leds():
        last = {}
        while True:
            for number, pin in leds.items():
                state = bool(pin.state)
                if last.get(number) != state:
                    print(f"  LED {number} {'ON' if state else 'off'}", flush=True)
                    last[number] = state
            time.sleep(0.05)

    threading.Thread(target=watch_leds, daemon=True).start()
    print(f"buttons: {', '.join(buttons)}. Commands: t N | h N SECONDS | q", flush=True)
    for line in sys.stdin:
        if not runtime_thread.is_alive():
            print("runtime stopped; see output above")
            return 1
        words = line.split()
        if not words:
            continue
        if words[0] == "q":
            return 0
        if words[0] not in {"t", "h"} or len(words) < 2 or words[1] not in buttons:
            print("usage: t N | h N SECONDS | q")
            continue
        try:
            seconds = 0.15 if words[0] == "t" else float(words[2] if len(words) > 2 else 3)
        except ValueError:
            print("usage: h N SECONDS")
            continue
        pin = buttons[words[1]]
        pin.drive_low()  # Buttons pull up; pressed reads low.
        threading.Timer(seconds, pin.drive_high).start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
