"""Blink every channel LED while a channel box is in setup mode.

The button service owns the LEDs in normal mode but does not run during setup,
so without this a box waiting for setup (Wi-Fi reset or WhatsApp relink) looks
dead. Started with comitup; stopping it turns the LEDs off.
"""

from __future__ import annotations

import os
import signal

from messagebox.contacts import parse_channel_pins


def start_blinking(raw_pins, led_factory):
    leds = [led_factory(led) for _, _, led in parse_channel_pins(raw_pins)]
    for lamp in leds:
        lamp.blink(on_time=0.5, off_time=0.5)  # same phase on every button
    return leds


def _stop(*_):
    raise SystemExit(0)  # unwinds into the finally below, which switches the LEDs off


def main():
    from gpiozero import LED  # Lazy so tests and non-Pi imports need no GPIO stack.

    leds = start_blinking(os.environ.get("MSGBOX_CHANNEL_PINS", ""), LED)
    if not leds:
        return 0
    signal.signal(signal.SIGTERM, _stop)
    try:
        signal.pause()
    finally:
        for lamp in leds:
            lamp.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
