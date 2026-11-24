import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

gpiozero = types.ModuleType("gpiozero")
gpiozero.Button = object
gpiozero.LED = object
with mock.patch.dict(sys.modules, {"gpiozero": gpiozero}):
    import messagebox.button_send as button_send  # noqa: E402
from messagebox.contacts import ContactStore  # noqa: E402
from messagebox.settings import defaults  # noqa: E402


GRANDMA = "15551234567@s.whatsapp.net"
FAMILY = "120363123456789@g.us"


class FakeButton:
    def __init__(self, pressed=False):
        self.is_pressed = pressed


class FakeLed:
    def __init__(self):
        self.lit = False

    def on(self):
        self.lit = True

    def off(self):
        self.lit = False


class ChannelPinTests(unittest.TestCase):
    def test_pins_parse_in_button_order_and_reject_ambiguity(self):
        self.assertEqual(button_send.parse_channel_pins(""), [])
        self.assertEqual(
            button_send.parse_channel_pins("17:26, 27:22"),
            [("1", 17, 26), ("2", 27, 22)],
        )
        for raw in ("17", "17:26,26:22", "17:x", ",".join(f"{n}:{n + 30}" for n in range(9))):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                button_send.parse_channel_pins(raw)


class ChannelRoutingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.queue_path = root / "queue"
        self.queue_path.mkdir()
        self.contacts = ContactStore(root / "contacts.json", clock=lambda: 1000)
        self.contacts.add_contact(GRANDMA, "Grandma", receive_after=0)
        self.contacts.add_contact(FAMILY, "Family", receive_after=0)
        self.contacts.bind_channel(1, GRANDMA)
        self.channels = [
            {"id": "1", "button": FakeButton(), "led": FakeLed()},
            {"id": "2", "button": FakeButton(), "led": FakeLed()},
        ]
        settings = defaults({})
        self.patches = (
            mock.patch.object(button_send, "CONTACTS_FILE", str(root / "contacts.json")),
            mock.patch.object(button_send, "QUEUE_DIR", str(self.queue_path)),
            mock.patch.object(button_send, "channels", self.channels),
            mock.patch.object(button_send, "caregiver_settings", return_value=settings),
            mock.patch.object(button_send, "quiet_hours", return_value=False),
            mock.patch.object(button_send, "log"),
            mock.patch.object(button_send, "log_event"),
            mock.patch.object(button_send, "beep"),
            mock.patch.object(button_send, "wait_for_stable_open"),
            mock.patch.object(button_send, "button", FakeButton(), create=True),
            mock.patch.object(button_send, "led", FakeLed(), create=True),
        )
        for patcher in self.patches:
            patcher.start()
        self.settings = settings

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.directory.cleanup()

    def queue_from(self, chat, name):
        wav = self.queue_path / name
        wav.write_bytes(b"audio")
        Path(str(wav) + ".json").write_text(json.dumps({"chat": chat}), encoding="utf-8")

    def dispatch(self, channel):
        self.channels[channel - 1]["button"].is_pressed = True
        seen = {}

        def handle(closed_at, **_):
            seen["button"] = button_send.button
            seen["chat"] = button_send._channel_chat
            return True

        with mock.patch.object(button_send, "handle_confirmed_press", side_effect=handle) as handled:
            button_send.dispatch_press(0.0)
        self.channels[channel - 1]["button"].is_pressed = False
        return handled, seen

    def test_queue_and_lamps_are_split_per_bound_chat(self):
        self.queue_from(FAMILY, "0001-a.wav")
        self.queue_from(GRANDMA, "0002-b.wav")
        self.assertEqual(button_send.queued(GRANDMA), ["0002-b.wav"])
        self.assertEqual(len(button_send.queued()), 2)

        button_send.refresh_led(force=True)
        self.assertTrue(self.channels[0]["led"].lit)
        # Family has a message waiting but is not bound: its lamp stays dark.
        self.assertFalse(self.channels[1]["led"].lit)

    def test_press_is_handled_with_that_channels_button_and_chat_only(self):
        idle = button_send.button
        handled, seen = self.dispatch(1)
        handled.assert_called_once()
        self.assertIs(seen["button"], self.channels[0]["button"])
        self.assertEqual(seen["chat"], GRANDMA)
        self.assertIs(button_send.button, idle)
        self.assertIsNone(button_send._channel_chat)

    def test_unbound_or_unreadable_channel_fails_closed(self):
        handled, _ = self.dispatch(2)
        handled.assert_not_called()
        button_send.beep.assert_called_once_with("fail")

        button_send.beep.reset_mock()
        Path(button_send.CONTACTS_FILE).write_text("broken", encoding="utf-8")
        handled, _ = self.dispatch(1)
        handled.assert_not_called()
        button_send.beep.assert_called_once_with("fail")

    def hold_flow(self, intent):
        with mock.patch.object(button_send, "_channel_chat", GRANDMA), mock.patch.object(
            button_send, "acknowledge_and_classify_legacy_press", return_value=intent
        ), mock.patch.object(button_send, "claim_fresh_card_intent") as card, mock.patch.object(
            button_send, "reconcile_card_selections"
        ), mock.patch.object(button_send, "play_next_legacy") as play, mock.patch.object(
            button_send, "PiGuidedIO"
        ) as io, mock.patch.object(button_send, "GuidedSession") as session, mock.patch.object(
            button_send, "mark_queue_known"
        ), mock.patch.object(button_send, "sound_pack"):
            button_send.record_and_send_legacy(self.settings, pressed_at=0.0)
        card.assert_not_called()
        return play, io, session

    def test_tap_plays_and_hold_records_only_the_bound_chat(self):
        play, io, _ = self.hold_flow("play")
        play.assert_called_once_with(GRANDMA)
        io.assert_not_called()

        play, io, session = self.hold_flow("record")
        play.assert_not_called()
        self.assertEqual(io.call_args.args[0], GRANDMA)
        self.assertEqual(session.return_value.run.call_args.kwargs["recipient"], GRANDMA)


if __name__ == "__main__":
    unittest.main()
