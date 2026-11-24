import unittest
from environment.runway import Runway


class TestBidirectionalRunway(unittest.TestCase):
    def test_runway_threshold_selection(self):
        rwy = Runway("RWY 1", "Runway 1", 3000, start=(300, 300), end=(700, 300), heading=90)

        # Point closer to Start (left end) -> landing from left to right
        thresh_start = rwy.get_closest_threshold(200, 300)
        self.assertEqual(thresh_start["direction"], "START_TO_END")
        self.assertAlmostEqual(thresh_start["start"][0], 300)
        self.assertAlmostEqual(thresh_start["end"][0], 700)
        self.assertAlmostEqual(thresh_start["ux"], 1.0)

        # Point closer to End (right end) -> landing from right to left
        thresh_end = rwy.get_closest_threshold(800, 300)
        self.assertEqual(thresh_end["direction"], "END_TO_START")
        self.assertAlmostEqual(thresh_end["start"][0], 700)
        self.assertAlmostEqual(thresh_end["end"][0], 300)
        self.assertAlmostEqual(thresh_end["ux"], -1.0)


if __name__ == "__main__":
    unittest.main()

