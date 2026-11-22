import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
from gui.game import SkyATCGame
from environment.aircraft import Aircraft, FlightStatus


class TestGameplayControls(unittest.TestCase):
    def setUp(self):
        self.game = SkyATCGame(initial_level=1)

    def test_spacebar_clearance_executes_target(self):
        # Step simulation to observe current fleet
        self.game.agent.step(0.1)
        target = self.game.agent.get_co_pilot_target()
        self.assertIsNotNone(target)
        ac, rwy = target
        self.assertEqual(ac.status, FlightStatus.HOLDING)

        executed = self.game._on_clear_landing_space()
        self.assertTrue(executed)
        self.assertIn(ac.status, (FlightStatus.INTERCEPT, FlightStatus.APPROACHING))

    def test_star_rating_calculation(self):
        self.assertEqual(self.game._calculate_stars(crashed=True, score=200, max_score=200), 0)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=180, max_score=200), 3)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=110, max_score=200), 2)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=40, max_score=200), 1)

    def test_interactive_auto_takeover_disabled(self):
        self.assertFalse(self.game.agent.auto_takeover_enabled)


if __name__ == "__main__":
    unittest.main()
