import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
from gui.game import SkyATCGame


class TestFullscreenControls(unittest.TestCase):
    def setUp(self):
        self.game = SkyATCGame(initial_level=1)

    def test_live_star_progress_ratio(self):
        ratio = self.game.get_star_progress_ratio()
        self.assertGreaterEqual(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)

    def test_sidebar_buttons_removed_from_gameplay(self):
        # In fullscreen gameplay, only top HUD buttons exist (Pause, Speed, SFX, Menu)
        self.game._switch_state("SIMULATION")
        btn_texts = [b.text for b in self.game.action_panel.buttons]
        self.assertNotIn("CLEAR LANDING [SPACE]", btn_texts)
        self.assertNotIn("OVERRIDE", btn_texts)
        self.assertIn("MENU", btn_texts)

    def test_drag_to_runway_bidirectional_threshold(self):
        self.game.agent.step(0.1)
        ac = self.game.airbase.aircraft_fleet[0]
        self.assertIsNotNone(ac)
        rwy = self.game.airbase.runways["RWY 1"]
        # Click/drop near east end of runway
        ok, msg = self.game.agent.override_assignment(ac.flight_id, "RWY 1", target_point=(rwy.end_x, rwy.end_y))
        self.assertTrue(ok)
        self.assertEqual(ac.assigned_runway, "RWY 1")
        self.assertAlmostEqual(ac.rwy_start_x, rwy.end_x)
        self.assertAlmostEqual(ac.rwy_ux, -1.0)


if __name__ == "__main__":
    unittest.main()
