import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
from gui.display import DisplayRenderer
from environment.aircraft import Aircraft, EmergencyType


class TestVisualAlerts(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1360, 768))
        self.renderer = DisplayRenderer(self.screen)

    def test_emergency_symbol_helper(self):
        ac_fuel = Aircraft("BG-1", fuel_level=8.0)
        ac_eng = Aircraft("BG-2", emergency_type=EmergencyType.ENGINE_PROBLEM)
        ac_med = Aircraft("BG-3", emergency_type=EmergencyType.MEDICAL)
        ac_norm = Aircraft("BG-4", fuel_level=80.0)

        self.assertEqual(self.renderer._get_emergency_symbol(ac_fuel), "FUEL")
        self.assertEqual(self.renderer._get_emergency_symbol(ac_eng), "ENGINE")
        self.assertEqual(self.renderer._get_emergency_symbol(ac_med), "MEDICAL")
        self.assertIsNone(self.renderer._get_emergency_symbol(ac_norm))


if __name__ == "__main__":
    unittest.main()
