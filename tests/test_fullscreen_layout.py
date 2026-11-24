import unittest
import config


class TestFullscreenLayout(unittest.TestCase):
    def test_fullscreen_canvas_width(self):
        self.assertEqual(config.CANVAS_WIDTH, config.WINDOW_WIDTH)
        self.assertEqual(config.CANVAS_WIDTH, 1360)

    def test_runway_centering_in_canvas(self):
        # Runway centers in 2-runway layout should be centered around X=680
        rwy1 = config.RUNWAY_LAYOUTS[2][0]
        mid_x = (rwy1["start"][0] + rwy1["end"][0]) / 2.0
        self.assertGreater(mid_x, 550)
        self.assertLess(mid_x, 800)


if __name__ == "__main__":
    unittest.main()

