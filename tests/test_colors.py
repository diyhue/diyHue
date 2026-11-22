import colorsys
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

from functions.colors import hsv_to_rgb  # noqa: E402


def reference(h, s, v):
    return [round(c * 255) for c in colorsys.hsv_to_rgb((h % 65536) / 65536, s / 254, v / 254)]


class HsvToRgbTests(unittest.TestCase):
    def test_issue_examples_fade_to_white_not_black(self):
        self.assertEqual(hsv_to_rgb(0, 254, 254), [255, 0, 0])
        self.assertEqual(hsv_to_rgb(0, 127, 254), [255, 128, 128])
        self.assertEqual(hsv_to_rgb(0, 0, 254), [255, 255, 255])

    def test_primary_and_secondary_hues(self):
        self.assertEqual(hsv_to_rgb(21845, 254, 254), [0, 255, 0])   # 120 degrees
        self.assertEqual(hsv_to_rgb(43690, 254, 254), [0, 0, 255])   # 240 degrees
        self.assertEqual(hsv_to_rgb(10923, 254, 254), [255, 255, 0])  # 60 degrees
        self.assertEqual(hsv_to_rgb(32768, 254, 254), [0, 255, 255])  # 180 degrees
        self.assertEqual(hsv_to_rgb(54613, 254, 254), [255, 0, 255])  # 300 degrees

    def test_matches_colorsys_across_the_range(self):
        for h in range(0, 65536, 997):
            for s in (0, 50, 127, 200, 254):
                for v in (1, 64, 127, 254):
                    got, want = hsv_to_rgb(h, s, v), reference(h, s, v)
                    for a, b in zip(got, want):
                        self.assertLessEqual(abs(a - b), 1, (h, s, v, got, want))


if __name__ == "__main__":
    unittest.main()
