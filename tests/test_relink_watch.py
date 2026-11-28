import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from messagebox.onboarding import relink_watch


def answer(authenticated=None, returncode=0, stdout=None):
    body = stdout if stdout is not None else json.dumps({"data": {"authenticated": authenticated}})
    return lambda *args, **kwargs: SimpleNamespace(returncode=returncode, stdout=body)


class RelinkWatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.count = root / "logged-out"
        self.enabled = root / "enabled"
        self.configured = root / "configured"
        self.configured.write_text("configured\n", encoding="ascii")
        self.resets = []

    def check(self, run, channels=("1", "2")):
        return relink_watch.check(
            run=run,
            reset=lambda **kwargs: self.resets.append(kwargs),
            channels=list(channels),
            count_path=self.count,
            enabled_path=self.enabled,
            configured_path=self.configured,
        )

    def test_two_clean_logged_out_answers_reenter_setup_keeping_wifi(self):
        self.assertEqual(self.check(answer(False)), "logged-out")
        self.assertEqual(self.resets, [])
        self.assertEqual(self.check(answer(False)), "relink")
        self.assertEqual(len(self.resets), 1)
        self.assertTrue(self.resets[0]["keep_wifi"])
        self.assertFalse(self.count.exists())

    def test_failed_checks_never_count_and_login_clears_the_count(self):
        self.check(answer(False))
        for run in (answer(returncode=1), answer(stdout="not json"), answer(stdout="{}")):
            self.assertEqual(self.check(run), "unknown")
        self.assertEqual(self.check(answer(True)), "authenticated")
        self.assertEqual(self.check(answer(False)), "logged-out")
        self.assertEqual(self.resets, [])

    def test_skips_single_button_boxes_setup_mode_and_boxes_without_hotspot_setup(self):
        self.assertEqual(self.check(answer(False), channels=()), "skipped")
        self.enabled.write_text("enabled\n", encoding="ascii")
        self.assertEqual(self.check(answer(False)), "skipped")
        self.enabled.unlink()
        self.configured.unlink()
        self.assertEqual(self.check(answer(False)), "skipped")
        self.assertFalse(self.count.exists())


if __name__ == "__main__":
    unittest.main()
