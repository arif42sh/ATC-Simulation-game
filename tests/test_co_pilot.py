import unittest
from environment.airbase import Airbase
from environment.aircraft import Aircraft, FlightStatus
from agent.agent import ATCAgent
import config


class TestCoPilot(unittest.TestCase):
    def setUp(self):
        self.airbase = Airbase(level_id=1)
        self.agent = ATCAgent(self.airbase, None)

    def test_co_pilot_finds_actionable_aircraft(self):
        ac1 = Aircraft("BG-201", "B737", x=500, y=100)
        ac1.status = FlightStatus.HOLD
        self.airbase.add_aircraft(ac1)
        self.agent.step(0.1)
        target = self.agent.get_co_pilot_target()
        self.assertIsNotNone(target)
        ac, rwy = target
        self.assertEqual(ac.flight_id, "BG-201")
        self.assertIn("RWY", rwy.id)

    def test_guardrail_blocks_heavy_on_short_runway_without_penalty(self):
        ac = Aircraft("BG-777", "B777", x=500, y=100)
        self.airbase.add_aircraft(ac)
        rwy = self.airbase.runways["RWY 2"]
        rwy.length_m = 1800
        prev_score = self.agent.reward_system.cumulative_reward
        is_safe, msg = self.agent.validate_guardrail(ac, "RWY 2")
        self.assertFalse(is_safe)
        self.assertIn("short", msg.lower())
        self.assertEqual(self.agent.reward_system.cumulative_reward, prev_score)

    def test_rewards_config_contains_casual_dopamine_keys(self):
        self.assertIn("AI_SYNERGY_BONUS", config.REWARDS)
        self.assertIn("TOUCHDOWN_REWARD", config.REWARDS)
        self.assertIn("COMBO_STREAK", config.REWARDS)
        self.assertEqual(config.REWARDS["AI_SYNERGY_BONUS"], config.AI_SYNERGY_BONUS_PTS)


if __name__ == "__main__":
    unittest.main()
