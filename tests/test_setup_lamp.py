import unittest

from messagebox.onboarding.setup_lamp import start_blinking


class FakeLed:
    def __init__(self, pin):
        self.pin = pin
        self.blinks = []

    def blink(self, **timing):
        self.blinks.append(timing)


class SetupLampTests(unittest.TestCase):
    def test_every_channel_led_blinks_in_the_same_rhythm(self):
        leds = start_blinking("25:24,8:23", FakeLed)
        self.assertEqual([led.pin for led in leds], [24, 23])
        self.assertEqual({str(led.blinks) for led in leds}, {str([{"on_time": 0.5, "off_time": 0.5}])})

    def test_single_button_box_blinks_nothing(self):
        self.assertEqual(start_blinking("", FakeLed), [])


if __name__ == "__main__":
    unittest.main()
