import unittest
import math
from environment.aircraft import Aircraft, FlightStatus
import config

class TestCasualDynamics(unittest.TestCase):
    def test_holding_orbit_dynamics(self):
        ac = Aircraft(flight_id="BG-101", model="B737", x=500.0, y=100.0, orbit_center=(500.0, 150.0), orbit_radius=50.0)
        ac.status = FlightStatus.HOLDING
        initial_dist = math.hypot(ac.x - ac.orbit_center_x, ac.y - ac.orbit_center_y)
        ac.update(1.0)
        new_dist = math.hypot(ac.x - ac.orbit_center_x, ac.y - ac.orbit_center_y)
        self.assertAlmostEqual(initial_dist, new_dist, delta=10.0)
        self.assertEqual(ac.status, FlightStatus.HOLDING)

    def test_interactive_speed_factor_presence(self):
        self.assertTrue(hasattr(config, "INTERACTIVE_SPEED_FACTOR"))
        self.assertLessEqual(config.INTERACTIVE_SPEED_FACTOR, 0.85)

if __name__ == "__main__":
    unittest.main()
