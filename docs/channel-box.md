# Two-button channel box (fork)

A channel box has two buttons, green and red. Each button is bound to one
WhatsApp group: a tap plays that group's waiting voice messages, and a hold
records a reply to it. To change who a button reaches, change the group's
members on a phone; the box itself is rarely touched. Everything here is
active when `MSGBOX_CHANNEL_PINS` is set in `/etc/messagebox/env`; single-button
boxes keep the upstream behaviour.

## Hardware

| Part | Notes |
| --- | --- |
| Raspberry Pi Zero 2 W | Passes the installer board gate. |
| USB audio dongle (C-Media) | One card for microphone and speaker. Its mixer controls are `Speaker`, `Mic` and `Auto Gain Control`. |
| Small speaker | Powered from the 5 V rail, not from the Pi's data port. |
| Microphone | On the dongle's input. It is opened only while recording. |
| Two arcade buttons with LEDs | Buttons to GND with pull-ups. The 5 V LEDs need a switch: here the DialPhone adapter (DRV8876); one logic-level MOSFET per LED works too. |
| Power supply | At least 2.5 A. |

Parts, photos and the optional adapter (and how to do without it) are in
[`hardware/README.md`](../hardware/README.md). Wiring
used here, from [`hardware/schematic-2-channel.svg`](../hardware/schematic-2-channel.svg):

| Channel | Button | LED | Notes |
| --- | --- | --- | --- |
| 1 green | GPIO25 | GPIO24 (DRV8876 EN/IN1, coil A) | Green is also the reset button. |
| 2 red | GPIO8 | GPIO23 (DRV8876 PH/IN2, coil B) | |

The DRV8876 has PMODE lifted for independent outputs. Its nSLEEP is GPIO18;
hold it high with `gpio=18=op,dh` in `/boot/firmware/config.txt`.

## Configuration

These lines in `/etc/messagebox/env` make a channel box (edit with
`sudoedit /etc/messagebox/env`; never `tee`, which empties the file):

```sh
MSGBOX_BUTTON_PIN=25        # channel 1 button; read by the reset gesture
MSGBOX_LED_PIN=24
MSGBOX_CHANNEL_PINS=25:24,8:23
MSGBOX_SPEAKER_CONTROL=Speaker   # the dongle has no PCM control
```

## Using the box

- **Tap** a button: plays that group's waiting messages, oldest first. Its LED
  is on while messages wait and blinks when one arrives. With nothing waiting,
  a tap replays that group's most recently played message, as often as wanted.
  The box keeps the last 10 played messages (both buttons together) for up to
  14 days; if none from that group is kept, the tap does nothing.
- **Hold** a button: records after the press cue; release to stop.
- **Replay and send:** with *review before send* on, the box replays the
  recording. Heard to the end, it sends (swoosh). Press any time during the
  replay to throw it away; the "deleted" sound confirms nothing was sent.
  Recordings under 1.5 s or without speech are deleted.
- The optional *messages per reply* limit plays the "oops" tone and keeps the
  microphone closed until a reply from that group has been played.

## Setup and changes

The dashboard exists only during setup. After **Finish setup** it is off; there
is no login-free page on the household Wi-Fi.

To change chats, buttons, WhatsApp or Wi-Fi, do a **full reset**:

1. Unplug the box, hold **green**, plug it in, and keep holding for about
   45 seconds.
2. Both LEDs blink while the box waits for setup.
3. Join the box's hotspot with the password on the label and choose the Wi-Fi.
4. Open `http://button-box-<id>.local/`. WhatsApp stays linked; approved chats
   and button bindings are kept.
5. In **Manage chats and buttons**, choose a chat for each button, then press
   **Finish setup** on the Setup page. The jingle plays and the LEDs stop
   blinking.

A developer on the LAN can instead use SSH, and start the dashboard for a
moment with `sudo systemctl start messagebox-dash` (stop it again, or reboot).

## WhatsApp logout recovery

WhatsApp logs the box out when the box account's phone has been offline for
about 14 days, and occasionally for other reasons. Keep that phone online.

When it happens, the box notices within about 10 minutes, keeps its Wi-Fi and
switches to setup: both LEDs blink. Then, on a phone call with the account's
owner:

1. Open `http://button-box-<id>.local/` and enter the box's WhatsApp number.
2. Read the pairing code to the owner, who enters it on their phone under
   WhatsApp → Linked devices → Link a device → Link with phone number instead.
3. The same account keeps its chats and button bindings. Press **Finish setup**.

Relinking a different account clears all chats and bindings.

## Label (required before a box leaves)

The household needs these to redo setup after a reset or logout, and there is
no remote access to look them up. Print them on a label stuck to the box (a
loose insert gets lost):

- Box name (`button-box-<id>`) and setup address `http://button-box-<id>.local/`
- Hotspot name and password, from `sudo messagebox-init-wifi-onboarding`
  (`sudo grep -E '^ap_(name|password)' /etc/comitup.conf` shows them again)
- The box's WhatsApp number
- "Both lights blinking: call <name, phone number>"
- "To start over: hold green while plugging in, keep holding about 45 seconds"

Treat the hotspot password as a credential: do not commit it or keep an
unprotected digital copy. Rerunning the initializer creates a new password and
makes the label wrong.

## Before shipping

- Run the per-unit acceptance (T11 in `TASKS.md`), including
  `sudo grep -c 'dport 22' /etc/messagebox-onboarding/firewall.nft` printing 0.
- Reserve a fixed address for the box in the household router if possible;
  after a reset, browsers can otherwise keep the old address for a while.
- Do a full reset and power the box off; the household finishes setup.
