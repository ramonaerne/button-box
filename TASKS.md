# Tasks: two-channel box (fork)

Source of intent: `MODIFICATION.md` (the human's words, unchanged). This file
records the facts found, the decisions taken in four question rounds
(2026-11-24), and the resulting tasks with acceptance criteria.

## Glossary

| Term | Meaning |
| --- | --- |
| **Channel** | One physical button + its LED + at most one bound chat. Two channels at first. |
| **Chat** | The WhatsApp conversation a channel is bound to: a person or a group. Use "chat", not "recipient". Upstream uses "recipient" for NFC/default routing, which channel boxes don't use. |
| **Approved chat** | A chat the builder added over the terminal. Only approved chats can be bound to a channel. |
| **Bind / rebind** | Assign an approved chat to a channel. A rebind is **pending** until confirmed on the box. |
| **Tap** | Press released before the hold threshold (`MIN_HOLD_S` = 0.4 s). |
| **Hold** | Press still down after the hold threshold ("long press"). |
| **Hold mode** | Upstream `hold_release`: tap plays the next waiting message; hold records; release sends. |
| **Guided mode** | Upstream `tap_review`, the upstream default: tap plays waiting messages, then a countdown, recording, and "press to send". |
| **Turn rule** | Per channel: after N messages are sent (`sends_per_reply`), that channel can't send again until a newer reply from its chat has been **played** (D15). |
| **Box account** | The single WhatsApp account/number the box uses. It's fixed, and the household never relinks it. |

## Facts found in the repo

- The microphone is opened only on demand: `arecord` is spawned per recording
  and stopped afterwards (`messagebox/button_send.py`). Nothing listens
  continuously, so this only needs verifying on the hardware.
- The runtime is built for one button, one LED and one shared queue. Routing
  goes NFC card → recent sender → default recipient. Channels are a new
  routing model, and the core change is in `button_send.py`.
- The poller already stores each incoming message's chat in a private
  sidecar, so the queue can be split per channel.
- NFC is optional; with no cards enrolled, routing ignores it.
- The Wi-Fi reset (hold button 1 for 10 s while powering on,
  `onboarding/reset.py`) clears only Wi-Fi. WhatsApp and contacts are kept.
- The dashboard has no login and is bound to the Wi-Fi interface. It already
  covers WhatsApp pairing, contacts, settings, Wi-Fi changes and the queue,
  including holding messages.
- The Zero 2 W passes the installer board gate. Path B (hotspot + browser) is
  unvalidated on the Zero 2 W.
- Audio detection handles one USB card with both capture and playback (the
  dongle). Mixer control names (`PCM`, `Mic`) may not match a cheap dongle.

### Base branch (2026-11-24)

Work is based on `release/v0.3.16` (upstream's working branch; the fork
tracks it as `fork/release/v0.3.16`), not `main`. Facts that changed versus
`main`:
- The Comitup board gate already accepts the Pi Zero 2 W (and Pi 3).
- Hold to talk now runs through `GuidedSession`. With **review before send**
  on (the default), releasing plays the recording back, and a further tap
  sends it.
- Microphone capture needs a one-shot permit taken from a physical gpiozero
  `Button` (`messagebox/mic_capture.py`, `docs/mic-access-audit.md`).
  Channels take it from the pressed button.
- There is a cloud transport besides wacli. Channels are wacli-only.

## Risks

1. **WhatsApp linked-device logout.** If the box account's phone is offline
   for about 14 days, the box is logged out. The builder keeps that phone and
   must open WhatsApp regularly. Signal (`signal-cli` as the primary device)
   would remove this, but its memory use on 512 MB is unchecked.
2. **Unofficial client.** `wacli` use can get the number banned. The box
   account must be a dedicated, expendable number.
3. **Upstream divergence.** No PRs (D16), so pulling later upstream fixes
   gets harder over time. Merge upstream only when a fix is needed.
4. **No-login dashboard.** Anyone on the household Wi-Fi can request a rebind.
   This is mitigated by the physical confirmation (T6).
5. **Personal data.** Relatives' numbers are entered only on the box (in the
   terminal), never in chats, issues, logs or the repo.
6. **Power.** Speakers must be powered from the 5 V rail, not the Pi's data
   port; PSU >= 2.5 A.

## Decisions

| # | Decision |
| --- | --- |
| D1 | Upstream default stays guided mode. This box (and the gift) runs hold mode via the existing setting. Both modes must work with channels before an upstream PR. |
| D2 | Fork; PR upstream wherever it makes sense. Build channels as a generic N-button feature. |
| D3 | Limit = turn rule, per channel, no other cap (N set by D15). Several replies play one after another, oldest first. |
| D4 | Setup: Path A (terminal) for the builder's testing; Path B (hotspot + browser) for the gift household. |
| D5 | WhatsApp only. Keep the send/receive calls in one place; Signal comes later. |
| D6 | The turn unlocks when a reply has been **played**, not merely received. |
| D7 | Phase 1: hotspot for Wi-Fi + dashboard for binding. Phase 2: the Path B portal binds channels. Phase 2 is required before the gift ships. |
| D8 | Any rebind outside the terminal needs a physical confirmation on the box. |
| D9 | Gift household: joins Wi-Fi and binds approved chats to buttons. They never relink WhatsApp or see the box account's other chats. |
| D10 | The builder keeps the box account's phone. Signal is reassessed later. |
| D11 | No remote access to the gift box. Support is the Wi-Fi reset gesture plus a phone call. |
| D12 | Confirmation: after a rebind request, that button's LED blinks fast. Holding that button for 5 s within 5 min confirms. Until then the button keeps its old chat and doesn't record. An unconfirmed rebind expires. |
| D13 | The household picks only from a short list of approved chats (relatives) that the builder enters in the terminal. |
| D14 | (2026-11-25, provisional) Keep **review before send** on (upstream default) for now. Revisit with a real mic before the gift ships (T12). Turning it off gives "hold to talk, release sends" (the original MODIFICATION.md idea) but removes the undo; the turn rule (T5) limits the cost of an accidental send. |
| D16 | (2026-11-28) Replaces D2: no upstream PRs. The fork has drifted (Pi changes, new features) and stays a fork. T0 and T4 are dropped; "(upstream)" labels below are historical. Per-reply limit (D15) is final; no per-day limit. Signal stays deferred. |
| D17 | (2026-11-28) Replaces D7, D8, D9, D12, D13: each button is bound to its own WhatsApp group. "Reassigning" means changing the group's members on a phone. Binding happens in the setup page (replacing recipient + NFC steps) or the runtime dashboard, without box confirmation (accepted risk until the dashboard-off plan). Setup is redone after a reset: hotspot, Wi-Fi, WhatsApp, buttons. |
| D15 | (2026-11-26) Replaces the one-turn rule: up to N sends per channel between replies, N set in the dashboard (off/1/2/3/5, default off). Reset when a newer reply is **played**, not just received. Per channel. Limit reached → wait tone only, mic stays closed. Not a security boundary: the dashboard has no login. |

Accepted defaults: each channel binds one chat (person or group). Only
approved chats are allowed incoming. An unbound button gives a fail beep and
never falls back. NFC is not installed or used. LED N is on while channel N
has messages waiting, blinks to ring, and stays on while recording.
Ringtone, volume and quiet hours are shared. Pins: B1 GPIO17/LED GPIO26,
B2 GPIO27/LED GPIO22. Buttons go to GND with a pull-up; LEDs are
active-high through the MOSFET. One interaction at a time; the other button
is ignored while busy. Incoming messages during recording queue, and the
ring waits. The turn rule is a setting, off upstream and on here. A failed
send doesn't use the turn; a message waiting in the outbox does. The first
message is allowed. Turn state survives a reboot. In a group, any member's
reply counts. A blocked press plays a generated "wait" tone. A chat can be
bound to only one channel. A rebind clears the turn state, and messages
still waiting from the old chat move to the dashboard's hold list. Terminal
binding needs no box confirmation; portal and dashboard binding do. The gift
ships in hold mode with the turn rule on, after a per-unit acceptance run and
a Wi-Fi reset. Recordings are capped at 60 s. A WhatsApp logout shows a
distinct blink on all LEDs.

## Tasks

Phase 1 is the builder's test box (Path A). Phase 2 is the gift (Path B).

### Phase 1

- [-] **T0 Upstream issue** — dropped (D16).
- [x] **T1 Channel bindings (upstream)** — done 2026-11-24 (contacts schema v3, `messagebox-contact bind/unbind`) — store channel → chat with the
      private contacts document (atomic write, lock, 0600 as today).
      *AC:* a contacts document without channels loads unchanged, and the
      single-button box behaves exactly as before. A chat can't be bound to
      two channels. Binding a chat that isn't approved is refused. Removing an
      approved chat unbinds its channel. Card IDs, JIDs and numbers never
      appear in logs or public API output.
- [~] **T2 Pins (upstream)** — `MSGBOX_CHANNEL_PINS` done; wiring doc moves to T8 — configure N button/LED pairs in
      `/etc/messagebox/env`. *AC:* `config/env.example` documents them.
      With only the existing `MSGBOX_BUTTON_PIN`/`MSGBOX_LED_PIN`, there is
      one channel, as today. Duplicate pins are refused at startup. The
      docs show the two-button + MOSFET LED wiring.
- [~] **T3 Channel runtime, hold mode (upstream)** — code + tests + mock-pin smoke test done; physical check pending — *AC:* a tap on button N
      plays the oldest waiting message from channel N's chat only. A hold
      records, and release sends to channel N's chat only. An unbound
      channel gives a fail beep and sends nothing. LED N reflects only
      channel N's waiting messages. While one channel plays or records,
      presses on the other are ignored. Incoming messages from unapproved
      chats are not queued. Restart recovery (in-flight, outbox, played
      archive) still works per channel. NFC, recent-sender and default
      routing are never used on a channel box.
- [-] **T4 Guided mode with channels** — dropped (D16); channel boxes run
      hold mode only.
- [~] **T5 Sends per reply (upstream setting, D15)** — code + tests done; physical check pending — settings key
      `sends_per_reply`, one of off/1/2/3/5, default off, editable in the
      dashboard like `max_recording_seconds`. *AC:* when off, behaviour is
      unchanged (wacli test). When N is set: each send accepted into the
      outbox counts for its channel; discarded, cancelled-in-review and
      failed sends don't. At N, a hold on that channel plays the "wait" tone
      and never opens the mic. The count resets when a message from that
      chat that arrived after the last counted send has been **played**; in a
      group any member's reply counts. Channels count independently.
      Counters survive a reboot, a rebind resets that channel, and lowering N
      applies at once. Fleet fixture regenerated (`settings_contract.py`).
- [-] **T6 Dashboard binding with confirmation** — dropped (D17).
- [ ] **T6b Path A binding** — `messagebox-dev-onboard` adds approved
      chats and binds channels (no box confirmation). *AC:* a fresh Pi
      reaches a two-channel working box using only the terminal flow and
      README steps.
- [ ] **T8 Audio dongle + hardware docs** — *AC:* the mixer control names for
      the dongle are checked and set by setup (or documented in env). Volume
      changes take effect. Power and wiring notes (speaker on the 5 V rail,
      MOSFET LEDs, PSU) are in `hardware/README.md`.
- [ ] **T9 Messenger seam** — *AC:* send/receive/download calls go through
      one module boundary that tests can inject. No Signal code.
- [ ] **T10 Tests** — `make check` passes. The contract tests cover the
      AC above, including restart/idempotency for bindings, pending rebinds
      and turn state.

### Phase 2 (gift)

- [~] **T7a Button binding replaces recipient + NFC setup** — code + tests
      done 2026-11-28; Pi check pending (approved 2026-11-28). A channel box is one with
      `MSGBOX_CHANNEL_PINS` set; single-button boxes keep today's flow.
      1. Setup page, after WhatsApp: a "Buttons" step replaces default
         recipient, voice test and NFC. Two pickers, "Green button"
         (channel 1, GPIO25) and "Red button" (channel 2, GPIO8), list the
         discovered chats (same tokens as the recipient list, modelled on
         the NFC "Who is this card for?" view). Choosing one approves the
         chat (adds it to contacts) and binds it. "Finish" is enabled once
         both buttons are bound.
      2. Binding goes through the existing WhatsApp pairing worker (it owns
         the contacts store and recipient tokens): new action
         `recipient_bind(channel, token)` →
         `RecipientSetup.bind` → `ContactStore.add_contact` +
         `bind_channel`. No new service.
      3. No NFC services: on a channel box, `/onboarding/complete` and
         `completion.py` require linked WhatsApp + bound buttons (no default
         recipient, no voice proof), skip `nfc.finish()`/`nfc.status()`, and
         do not enable `messagebox-nfc.service`.
         `messagebox-onboarding-home.service` gets `Wants=` instead of
         `Requires=` on the NFC worker, and setup masks both NFC units when
         channel pins are set.
      4. The same Buttons view is reachable in the runtime dashboard, bound
         directly via `ContactStore` (`/api/contacts` `bind`/`unbind`).
      *AC:* a reset channel box with no NFC reader reaches runtime through
      the setup page by linking WhatsApp and binding both
      buttons; NFC units never start; only discovered chats can be bound,
      one chat per button; no JIDs in logs; single-button setup tests
      unchanged.
- [ ] **T7 Reset and hotspot setup on a channel box (D17)** — *AC:* the
      reset gesture puts the box back into hotspot setup and keeps WhatsApp,
      contacts and bindings. The portal does Wi-Fi only on a linked channel
      box: no WhatsApp relink, default-recipient, voice-gate or NFC step
      blocks completion, and completion does not enable NFC. Relinking to
      another account stays possible from the dashboard (existing unlink).
- [ ] **T6c Logout indicator** — *AC:* when WhatsApp auth is lost, all LEDs
      show a distinct pattern (different from ring/pending/recording) until
      auth returns.
- [ ] **T7b Zero 2 W Path B validation** — *AC:* on the physical box: the
      hotspot appears, Wi-Fi joins, and the Wi-Fi reset gesture keeps
      WhatsApp and bindings.
- [ ] **T12 Decide review before send for the gift** (open, D14) — *AC:* the
      shipped setting is chosen after testing with a real mic and a child-like
      user, and is recorded in D14.
- [ ] **T13 Dashboard message audio off (upstream setting)** — the no-login
      dashboard streams received voice messages (`/audio/<f>`) to anyone on
      the Wi-Fi. *AC:* an env setting (e.g. `MSGBOX_DASH_AUDIO=0`, documented
      in `config/env.example`, settable at install) removes playback: the
      endpoint returns 404 and the UI hides the play controls. Default keeps
      today's behaviour, and a wacli test proves it.
- [ ] **T11 Physical acceptance** — the per-unit run (`docs/box-acceptance.md`)
      plus: both channels send/receive to the right chat, the turn rule,
      rebind confirmation, the microphone open only while recording, and a
      reboot. After a fresh boot, the **first** hold on each button records
      and sends (known gap above); recheck wiring if it fails. Check `sudo grep -c 'dport 22' /etc/messagebox-onboarding/firewall.nft`
      prints 0 (no dev SSH-on-hotspot rule). Then a Wi-Fi reset before shipping.

### Later (optional)

- [ ] **Remove dev SSH-on-hotspot rule** (added 2026-11-28 by hand on
      `button-box-01`, not in the repo): a `tcp dport 22 accept` line tagged
      `# dev only: SSH on hotspot` in `/etc/messagebox-onboarding/firewall.nft`.
      Remove with `sudo sed -i '/dev only: SSH on hotspot/d'
      /etc/messagebox-onboarding/firewall.nft` (or rerun `scripts/setup.sh`).
      Must be gone before any box ships (T11).
- [ ] **Reset reads channel pin 1** — `onboarding/reset.py` uses the first
      button of `MSGBOX_CHANNEL_PINS` when set. Not needed while
      `MSGBOX_BUTTON_PIN=25` is in the env.
- [~] **Keep WhatsApp linked across a reset** — done 2026-11-28 (needed for
      button binding on a terminal-linked box): an idle pairing engine adopts a
      non-empty live store once `wacli auth status` confirms it. Pi check pending.
- [ ] **Both-button reset gesture** — see T7 discussion (power-on, both
      buttons).

### Dev tooling

- [x] `scripts/dev/push-code.sh user@host`: copies already-installed runtime
      Python and the runner to a provisioned test box and restarts button,
      poller and dashboard (not sync). Verified on the Pi Zero 2 W.
- [x] `scripts/dev/virtual-buttons.py`: real runtime on gpiozero mock pins,
      driven from the terminal; always records a fake mic (tone, or
      `--mic-file WAV`) so terminal input never opens the real microphone.
      Installed to `/opt/messagebox/dev/`. Documented in
      `docs/developer-onboarding.md`.

### Known gaps (from T1–T3)

- 2026-11-26, physical box: a hold on red (channel 2) did nothing (no LED,
  no recording) while a tap played its messages; after boot, channel 1
  only sent after a message had been received. Not reproduced yet. Suspect
  the silent `except speaker.SpeakerBusy: return False` in the press
  handler or a mic open failure; capture `journalctl -u
  messagebox-button.service` during a failing hold.
  Seen again after a reboot, only on the first press; could also be a loose
  connection. Verified in T11.
- Messages from approved but unbound chats still queue (dashboard shows
  them), but no button plays them.
- Fresh install still needs a USB audio card for detection (`setup.sh` and
  `messagebox-audio-detect.service`). A USB dongle without a mic plugged in
  is enough.
- If the speaker card is missing, the volume `amixer` call fails and retries
  every loop, flooding logs (existing behaviour).

### Hold flow with review on (as observed on the Pi, 2026-11-25)

1. Press and hold: the press cue plays, and recording starts once it ends
   (LED on).
2. Release: recording stops. Under 1.5 s or not meaningful → "deleted" cue,
   nothing sent.
3. Review voice line, then playback of the recording.
4. Send prompt voice line.
5. One short press within **10 s** sends it (confirmation cue, then the
   swoosh once sent). Presses during the playback are discarded.
6. No press → "deleted" cue + "not sent"; nothing is sent. A recording that
   hits the maximum length always goes through review.

This is not obvious to a first-time user (see T12).

### Setup notes from the first Zero 2 W install (2026-11-24/25)

- The hostname must be `button-box-<id>` or `message-box-<id>`; otherwise
  the dashboard and Wi-Fi onboarding refuse to start.
- The C-Media dongle's mixer controls are `Speaker`, `Mic` and
  `Auto Gain Control`. `MSGBOX_SPEAKER_CONTROL=Speaker` must be set by hand
  (T8).
- An env file can lack `MSGBOX_CHANNEL_PINS`; add it by hand.
- `messagebox-dev-onboard` also enables NFC. Without a reader the NFC service
  fails and the script disables all services, so answer "n" and enable
  `button sync poller` by hand.
- The first send right after the services start can fail with "store is
  locked" while sync connects. The outbox retries.
- Receiving cannot be tested while the box is linked to the tester's own
  number: messages from the box account (including "message yourself" and
  groups where only you post) are skipped by design. Test with a second
  account, or give the box its own number. Receiving on the Pi is
  **not yet verified**.
- Run wacli as the `messagebox` user with
  `WACLI_STORE_DIR=/var/lib/messagebox/wacli`; using another user creates a
  separate, stray linked session.

### Later / reassess

- Signal via `signal-cli` as the primary device (removes the phone
  dependency). First check memory use on a Zero 2 W.
