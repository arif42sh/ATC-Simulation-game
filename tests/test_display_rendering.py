import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
from environment.aircraft import Aircraft
from gui.display import DisplayRenderer


class TestDisplayRendering(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1360, 768))
        self.renderer = DisplayRenderer(self.screen)

    def test_fuel_color_thresholds(self):
        ac_green = Aircraft("BG-1", "B737", x=100, y=100, fuel_level=80.0)
        ac_amber = Aircraft("BG-2", "B737", x=100, y=100, fuel_level=35.0)
        ac_red = Aircraft("BG-3", "B737", x=100, y=100, fuel_level=12.0)
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_green.fuel_level), (50, 220, 90))
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_amber.fuel_level), (255, 185, 35))
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_red.fuel_level), (240, 50, 50))

    def test_render_simulation_frame(self):
        from environment.airbase import Airbase
        from environment.levels import LevelManager
        from agent.agent import ATCAgent
        airbase = Airbase(level_id=1)
        level_mgr = LevelManager(airbase)
        level_mgr.start_level(1)
        agent = ATCAgent(airbase)
        agent.step(0.1)

        # Trigger simulation frame render (calls _draw_ai_spotlight, _draw_flow_approach_path, etc.)
        self.renderer.render_simulation(
            airbase=airbase,
            agent=agent,
            level_mgr=level_mgr,
            selected_ac=None,
            override_mode=False,
            drag_state=None,
            is_paused=False,
            sim_speed=1.0,
            modal_state=None,
            muted=False,
        )

    def test_flow_approach_path_and_reticle(self):
        self.renderer._draw_flow_approach_path((100.0, 100.0), (300.0, 300.0), (50, 220, 90))
        self.renderer._draw_hud_reticle(150.0, 150.0, 22.0, (255, 215, 65))
        self.renderer._draw_plane_sprite(150.0, 150.0, 90.0, (220, 230, 240))


if __name__ == "__main__":
    unittest.main()

