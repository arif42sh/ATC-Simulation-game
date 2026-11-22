import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from environment.aircraft import Aircraft
from gui.display import DisplayRenderer

class TestDisplayRendering(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1360, 768))
        self.renderer = DisplayRenderer(self.screen)

    def test_fuel_color_thresholds(self):
        ac_green = Aircraft("BG-1", "B737", 80.0, x=100.0, y=100.0)
        ac_amber = Aircraft("BG-2", "B737", 35.0, x=100.0, y=100.0)
        ac_red = Aircraft("BG-3", "B737", 12.0, x=100.0, y=100.0)
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_green.fuel_level), (50, 220, 90))
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_amber.fuel_level), (255, 185, 35))
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_red.fuel_level), (240, 50, 50))

if __name__ == "__main__":
    unittest.main()
