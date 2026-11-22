import unittest
import math
from environment.aircraft import Aircraft, FlightStatus
import config


class TestCasualDynamics(unittest.TestCase):
    def test_holding_orbit_dynamics(self):
        # Aircraft already in steady holding orbit
        ac = Aircraft(
            flight_id="BG-101",
            model="B737",
            x=540.0,
            y=100.0,
            orbit_center=(500.0, 100.0),
            orbit_radius=40.0,
            heading=90.0,
        )
        ac.status = FlightStatus.HOLD
        self.assertTrue(hasattr(ac, "orbit_center_x"))
        self.assertEqual(ac.orbit_center_x, 500.0)
        self.assertEqual(ac.orbit_center_y, 100.0)

        initial_dist = math.hypot(ac.x - ac.orbit_center_x, ac.y - ac.orbit_center_y)
        self.assertAlmostEqual(initial_dist, 40.0, delta=1.0)

        # Advance simulation step
        ac.update(1.0)
        new_dist = math.hypot(ac.x - ac.orbit_center_x, ac.y - ac.orbit_center_y)
        self.assertAlmostEqual(new_dist, 40.0, delta=1.0)
        self.assertEqual(ac.status, FlightStatus.HOLD)

    def test_interactive_speed_factor_presence(self):
        self.assertTrue(hasattr(config, "INTERACTIVE_SPEED_FACTOR"))
        self.assertLessEqual(config.INTERACTIVE_SPEED_FACTOR, 0.85)
        self.assertTrue(hasattr(config, "COMBO_TIMEOUT_SECONDS"))
        self.assertEqual(config.COMBO_TIMEOUT_SECONDS, 14.0)


if __name__ == "__main__":
    unittest.main()
