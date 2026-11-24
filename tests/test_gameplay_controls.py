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
        self.assertEqual(self.game._calculate_stars(crashed=False, score=180, max_score=200, ai_rescues=0), 3)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=180, max_score=200, ai_rescues=1), 2)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=110, max_score=200, ai_rescues=0), 2)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=40, max_score=200, ai_rescues=0), 1)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=-100, max_score=200, ai_rescues=4, total_aircraft=4), 0)

    def test_interactive_auto_takeover_enabled(self):
        self.assertTrue(self.game.agent.auto_takeover_enabled)

    def test_settings_toggle_and_cycling(self):
        # 1. Master Audio Toggle
        orig_audio = self.game.settings.get("master_audio", True)
        self.game._toggle_master_audio()
        self.assertEqual(self.game.settings["master_audio"], not orig_audio)
        self.game._toggle_master_audio()
        self.assertEqual(self.game.settings["master_audio"], orig_audio)

        # 2. SFX Volume Cycling: 1.0 -> 0.5 -> 0.0 -> 1.0
        self.game.settings["sfx_volume"] = 1.0
        self.game._cycle_sfx_volume()
        self.assertEqual(self.game.settings["sfx_volume"], 0.5)
        self.game._cycle_sfx_volume()
        self.assertEqual(self.game.settings["sfx_volume"], 0.0)
        self.game._cycle_sfx_volume()
        self.assertEqual(self.game.settings["sfx_volume"], 1.0)

        # 3. Airport Ambience Toggle
        orig_amb = self.game.settings.get("ambience", True)
        self.game._toggle_ambience()
        self.assertEqual(self.game.settings["ambience"], not orig_amb)
        self.game._toggle_ambience()
        self.assertEqual(self.game.settings["ambience"], orig_amb)

        # 4. Co-Pilot Mode Cycling & Guardrail Effects
        self.game.settings["copilot_mode"] = "BALANCED"
        self.game._cycle_copilot_mode()
        self.assertEqual(self.game.settings["copilot_mode"], "HARDCORE")
        self.assertFalse(self.game.agent.auto_takeover_enabled)

        self.game._cycle_copilot_mode()
        self.assertEqual(self.game.settings["copilot_mode"], "RELAXED")
        self.assertTrue(self.game.agent.auto_takeover_enabled)
        import config
        self.assertEqual(config.HITL_TIMEOUT_SECONDS, 30.0)

        self.game._cycle_copilot_mode()
        self.assertEqual(self.game.settings["copilot_mode"], "BALANCED")
        self.assertTrue(self.game.agent.auto_takeover_enabled)
        self.assertEqual(config.HITL_TIMEOUT_SECONDS, 20.0)

        # 5. Flight Trajectory Lines Toggle
        orig_tr = self.game.settings.get("trajectory_lines", True)
        self.game._toggle_trajectory_lines()
        self.assertEqual(self.game.settings["trajectory_lines"], not orig_tr)
        self.assertEqual(self.game.renderer.show_trajectory, not orig_tr)
        self.game._toggle_trajectory_lines()
        self.assertEqual(self.game.settings["trajectory_lines"], orig_tr)

        # 6. Modal Open & Close
        self.game._open_settings()
        self.assertTrue(self.game.settings_open)
        self.game._close_settings()
        self.assertFalse(self.game.settings_open)

    def test_career_progress_reset(self):
        self.game._on_request_reset_career()
        self.assertTrue(self.game.reset_confirm_open)
        self.game._on_cancel_reset_career()
        self.assertFalse(self.game.reset_confirm_open)
        self.game._on_confirm_reset_career()
        self.assertFalse(self.game.reset_confirm_open)
        self.assertIn("reset", self.game.settings_toast.lower())

    def test_audio_manager_procedural_sound_suite(self):
        sound_mgr = self.game.sound
        self.assertIn("click", sound_mgr.sounds)
        self.assertIn("landing", sound_mgr.sounds)
        self.assertIn("touchdown", sound_mgr.sounds)
        self.assertIn("emergency", sound_mgr.sounds)
        self.assertIn("warning", sound_mgr.sounds)
        self.assertIn("victory", sound_mgr.sounds)
        sound_mgr.set_sfx_volume(0.5)
        self.assertEqual(sound_mgr.sfx_volume, 0.5)
        sound_mgr.set_master_volume(0.8)
        self.assertEqual(sound_mgr.master_volume, 0.8)


if __name__ == "__main__":
    unittest.main()
