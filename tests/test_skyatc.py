"""
=============================================================================
SkyATC AI V2 - Automated Unit & Integration Test Suite
Covers all 15 Report Test Cases (TC-01..TC-15), Data Structures,
9-Rule AI Plan Validator, 20-Level Scaling, 9-Table DB, and CSV Export.
=============================================================================
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import database.db as db_mod
from environment.airbase import Airbase
from environment.aircraft import Aircraft, FlightStatus, EmergencyType
from environment.levels import LevelManager
from environment.events import EventManager
from agent.agent import ATCAgent
from agent.decision import DecisionEngine
from agent.validator import PlanValidator
from database.queries import DatabaseLogger


class TestSkyATCV2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._orig_db_type = config.DB_TYPE
        cls._orig_sqlite_path = config.SQLITE_DB_PATH
        cls._orig_api_key = config.GEMINI_API_KEY
        cls._tmp_dir = tempfile.TemporaryDirectory()
        config.DB_TYPE = "sqlite"
        config.SQLITE_DB_PATH = Path(cls._tmp_dir.name) / "test_skyatc.db"
        config.GEMINI_API_KEY = ""
        db_mod._db_instance = None

    @classmethod
    def tearDownClass(cls):
        if db_mod._db_instance is not None:
            db_mod._db_instance.close()
            db_mod._db_instance = None
        config.DB_TYPE = cls._orig_db_type
        config.SQLITE_DB_PATH = cls._orig_sqlite_path
        config.GEMINI_API_KEY = cls._orig_api_key
        cls._tmp_dir.cleanup()

    def setUp(self):
        self.db_logger = DatabaseLogger()
        self.airbase = Airbase(level_id=1)
        self.level_mgr = LevelManager(self.airbase)
        self.event_mgr = EventManager(self.airbase, self.level_mgr)
        self.agent = ATCAgent(self.airbase, self.db_logger)

    def test_tc01_normal_aircraft_landing_request(self):
        """TC-01: Normal aircraft landing request produces valid landing plan."""
        ac = Aircraft("BG-101", model="B737", fuel_level=78.0)
        self.airbase.add_aircraft(ac)
        self.agent.step(0.5)
        plan = self.agent.ui_state["current_plan"]
        self.assertIsNotNone(plan)
        self.assertTrue(plan["is_valid"])
        self.assertEqual(plan["assignments"][0]["flight_id"], "BG-101")
        self.assertEqual(plan["assignments"][0]["action"], "AUTHORIZE_LANDING")

    def test_tc02_multiple_aircraft_priority_min_heap(self):
        """TC-02: Multiple requests sorted accurately via Min-Heap & Hash Map O(1) lookup."""
        a1 = Aircraft("BG-310", model="A320", fuel_level=70.0)
        a2 = Aircraft("BG-205", model="B737", fuel_level=35.0, emergency_type=EmergencyType.ENGINE_PROBLEM)
        a3 = Aircraft("BG-101", model="B737", fuel_level=12.0, emergency_type=EmergencyType.CRITICAL_FUEL)
        self.airbase.add_aircraft(a1)
        self.airbase.add_aircraft(a2)
        self.airbase.add_aircraft(a3)

        # Hash Map lookup check
        self.assertIs(self.airbase.get_aircraft("BG-205"), a2)

        # Min-Heap priority check + 1:1 Airbase Queue synchronization
        engine = DecisionEngine()
        ordered = engine.pop_sorted_priorities([a.to_dict() for a in self.airbase.aircraft_fleet])
        self.assertIn(ordered[0][1]["flight_id"], ("BG-101", "BG-205"))
        self.assertEqual(ordered[-1][1]["flight_id"], "BG-310")
        ranked = self.airbase.get_ranked_pending_aircraft()
        self.assertEqual([a.flight_id for a in ranked], [item[1]["flight_id"] for item in ordered])

        # Exact-tie synchronization (same score breaks by FIFO arrival_seq)
        tie_ab = Airbase(level_id=1)
        t1 = Aircraft("BG-901", fuel_level=70.0)
        t2 = Aircraft("BG-902", fuel_level=70.0)
        tie_ab.add_aircraft(t1)
        tie_ab.add_aircraft(t2)
        t2.distance_nm = t1.distance_nm
        tie_ranked = [a.flight_id for a in tie_ab.get_ranked_pending_aircraft()]
        tie_heap = [x[1]["flight_id"] for x in engine.pop_sorted_priorities([a.to_dict() for a in tie_ab.get_pending_requests()])]
        self.assertEqual(tie_ranked, ["BG-901", "BG-902"])
        self.assertEqual(tie_ranked, tie_heap)

    def test_tc03_tc04_critical_fuel_and_engine_emergencies(self):
        """TC-03 & TC-04: Critically low fuel & engine problem get highest priority over normal flights."""
        normal = Aircraft("BG-310", fuel_level=80.0)
        low_fuel = Aircraft("BG-101", fuel_level=12.0, emergency_type=EmergencyType.CRITICAL_FUEL)
        engine_prob = Aircraft("BG-205", fuel_level=40.0, emergency_type=EmergencyType.ENGINE_PROBLEM)
        self.airbase.add_aircraft(normal)
        self.airbase.add_aircraft(low_fuel)
        self.airbase.add_aircraft(engine_prob)
        self.agent.step(0.5)
        assignments = self.agent.ui_state["current_plan"]["assignments"]
        top_two = {a["flight_id"] for a in assignments[:2]}
        self.assertEqual(top_two, {"BG-101", "BG-205"})

    def test_tc05_tc06_conflict_free_when_one_runway_occupied(self):
        """TC-05 & TC-06: One runway occupied routes next aircraft to alternate available runway."""
        self.airbase.runways["RWY 1"].occupy("BG-999", duration_seconds=10.0)
        self.airbase.add_aircraft(Aircraft("BG-101", model="B737", fuel_level=50.0))
        self.airbase.add_aircraft(Aircraft("BG-102", model="AT72", fuel_level=60.0))
        self.agent.step(0.5)
        assignments = self.agent.ui_state["current_plan"]["assignments"]
        cleared = [a for a in assignments if a["action"] == "AUTHORIZE_LANDING"]
        self.assertEqual(len(cleared), 1)
        self.assertEqual(cleared[0]["assigned_runway"], "RWY 2")

    def test_tc07_tc08_runway_unavailable_and_dynamic_replan(self):
        """TC-07 & TC-08: Maintenance/weather closure or sudden emergency triggers dynamic re-plan."""
        self.airbase.setup_for_level(11)  # 3 runways
        self.airbase.add_aircraft(Aircraft("BG-401", model="A320", fuel_level=65.0))
        self.agent.step(0.5)

        # Put RWY 2 under maintenance & inject sudden emergency
        self.airbase.runways["RWY 2"].set_maintenance("FOD Check", 15.0)
        self.airbase.add_aircraft(Aircraft("BG-402", model="B737", fuel_level=11.0, emergency_type=EmergencyType.CRITICAL_FUEL))
        self.agent.step(0.5)

        self.assertGreater(self.agent.stats["replan_events"], 0)
        assignments = self.agent.ui_state["current_plan"]["assignments"]
        assigned_rwys = {a["assigned_runway"] for a in assignments if a["assigned_runway"]}
        self.assertNotIn("RWY 2", assigned_rwys)
        self.assertEqual(assignments[0]["flight_id"], "BG-402")

    def test_tc09_tc10_validator_rejects_conflicts_duplicates_and_short_runways(self):
        """TC-09 & TC-10: Validator catches double runway conflict, duplicate aircraft, and Heavy on short runway."""
        self.airbase.setup_for_level(16)  # 4 runways, RWY 4 = 1800m
        self.airbase.add_aircraft(Aircraft("BG-777", model="B777", fuel_level=50.0))
        self.airbase.add_aircraft(Aircraft("BG-101", model="AT72", fuel_level=60.0))
        state = self.agent.observer.observe()
        validator = PlanValidator()

        # Duplicate runway conflict
        bad_conflict = {
            "assignments": [
                {"flight_id": "BG-777", "action": "AUTHORIZE_LANDING", "assigned_runway": "RWY 1"},
                {"flight_id": "BG-101", "action": "AUTHORIZE_LANDING", "assigned_runway": "RWY 1"},
            ]
        }
        ok, issues, _, code = validator.validate_plan(bad_conflict, state)
        self.assertFalse(ok)
        self.assertEqual(code, "RUNWAY_CONFLICT")

        # Heavy B777 on 1800m short RWY 4
        bad_size = {
            "assignments": [
                {"flight_id": "BG-777", "action": "AUTHORIZE_LANDING", "assigned_runway": "RWY 4"},
            ]
        }
        ok2, _, _, code2 = validator.validate_plan(bad_size, state)
        self.assertFalse(ok2)
        self.assertEqual(code2, "CONSTRAINT_VIOLATION")

        # Duplicate aircraft assignment
        bad_dup = {
            "assignments": [
                {"flight_id": "BG-101", "action": "AUTHORIZE_LANDING", "assigned_runway": "RWY 3"},
                {"flight_id": "BG-101", "action": "AUTHORIZE_LANDING", "assigned_runway": "RWY 4"},
            ]
        }
        ok3, _, _, code3 = validator.validate_plan(bad_dup, state)
        self.assertFalse(ok3)
        self.assertEqual(code3, "DUPLICATE_ASSIGNMENT")

    def test_tc11_player_override_validation_and_execution(self):
        """TC-11: Player manual override validates and executes cleanly."""
        self.airbase.add_aircraft(Aircraft("BG-501", model="A320", fuel_level=60.0))
        self.agent.step(0.5)
        ok, msg = self.agent.override_assignment("BG-501", "RWY 2")
        self.assertTrue(ok, msg)
        self.assertEqual(self.airbase.get_aircraft("BG-501").assigned_runway, "RWY 2")
        self.assertEqual(self.agent.stats["player_overrides"], 1)

    def test_tc12_hitl_10s_timeout_auto_execute(self):
        """TC-12: When 10s decision window expires, AI automatically executes validated plan."""
        ac = Aircraft("BG-601", model="B737", fuel_level=55.0)
        self.airbase.add_aircraft(ac)
        self.assertEqual(ac.hitl_decision_timer, config.HITL_TIMEOUT_SECONDS)

        self.airbase.update(10.5)
        self.agent.step(10.5)

        self.assertFalse(ac.hitl_pending)
        self.assertEqual(ac.decision_maker, "AI_AGENT")
        self.assertEqual(self.agent.stats["timeout_auto_executes"], 1)
        self.assertGreater(self.agent.reward_system.cumulative_reward, 0)

    def test_tc13_llm_offline_fallback_and_explainable_reason(self):
        """TC-13: Offline/API failure seamlessly uses Min-Heap fallback with reason badge."""
        self.airbase.add_aircraft(Aircraft("BG-101", model="B737", fuel_level=12.0, emergency_type=EmergencyType.CRITICAL_FUEL))
        plan = self.agent.llm_client.generate_plan_sync(self.agent.observer.observe())
        self.assertEqual(plan["source"], "LOCAL_UTILITY")
        self.assertTrue(len(plan["reasoning"]) > 5)
        self.assertEqual(plan["assignments"][0]["flight_id"], "BG-101")

    def test_tc14_tc15_20_level_runway_scaling_and_db_csv_export(self):
        """TC-14 & TC-15: 20-level runway progression (2->2->3->4), DB persistence & CSV export."""
        self.airbase.setup_for_level(1)
        self.assertEqual(len(self.airbase.runways), 2)
        self.airbase.setup_for_level(6)
        self.assertEqual(len(self.airbase.runways), 2)
        self.airbase.setup_for_level(11)
        self.assertEqual(len(self.airbase.runways), 3)
        self.airbase.setup_for_level(16)
        self.assertEqual(len(self.airbase.runways), 4)

        self.db_logger.log_level_history(1, "COMPLETED", 145, 4, 1)
        prog = self.db_logger.get_level_progression()
        self.assertIn(1, prog["completed_levels"])

        csv_path = self.db_logger.export_logs_to_csv()
        self.assertTrue(csv_path.exists())
        csv_path.unlink(missing_ok=True)

    def test_all_v2_scenarios_and_fuel_crash_detection(self):
        """Verifies all V2 scenarios execute cleanly and fuel 0% triggers crash diagnostics."""
        for key in (
            "normal_landing", "simultaneous_requests", "critical_fuel_emergency",
            "engine_problem_emergency", "one_runway_occupied", "runway_maintenance_storm",
            "heavy_aircraft_runway_length", "expert_4_runways",
        ):
            self.assertTrue(self.event_mgr.load_scenario(key))
            self.agent.reset_for_level(self.airbase.level_id)
            self.agent.step(0.5)
            self.assertIsNotNone(self.agent.ui_state["current_plan"])

        # Fuel crash detection check
        starved = Aircraft("BG-000", fuel_level=1.0)
        self.airbase.setup_for_level(1)
        self.airbase.add_aircraft(starved)
        crashed = self.airbase.update(6.5)
        self.assertIs(crashed, starved)
        self.assertEqual(starved.status, FlightStatus.CRASHED)

    def test_runway_lock_hold_release_and_compatible_hitl_gating(self):
        """Verifies landing locks do not expire mid-rollout, HOLD frees runways, and HITL waits for compatible runways."""
        # 1. Slow aircraft from east orbit stays locked on RWY 1 until LANDED, then releases cleanly
        self.airbase.setup_for_level(1)
        slow = Aircraft("BG-SLOW", model="C208", fuel_level=80.0, x=890.0, y=665.0)
        self.airbase.add_aircraft(slow)
        self.agent.reset_for_level(1)
        self.assertTrue(self.airbase.authorize_landing("BG-SLOW", "RWY 1"))

        elapsed = 0.0
        while slow.status != FlightStatus.LANDED and elapsed < 65.0:
            self.airbase.update(0.5)
            elapsed += 0.5
            if slow.status != FlightStatus.LANDED:
                self.assertEqual(self.airbase.runways["RWY 1"].current_aircraft, "BG-SLOW")
        self.assertEqual(slow.status, FlightStatus.LANDED)
        self.assertTrue(self.airbase.runways["RWY 1"].is_available())

        # 2. Manual HOLD releases occupied runway and applies EMERGENCY_DELAYED when holding an emergency
        self.airbase.setup_for_level(1)
        emerg = Aircraft("BG-EM1", model="B737", fuel_level=18.0, emergency_type=EmergencyType.CRITICAL_FUEL)
        self.airbase.add_aircraft(emerg)
        self.agent.reset_for_level(1)
        self.agent.step(0.2)
        self.assertTrue(self.agent.accept_ai_plan())
        assigned_rwy = emerg.assigned_runway
        self.assertIsNotNone(assigned_rwy)
        ok, _ = self.agent.override_assignment("BG-EM1", "HOLD")
        self.assertTrue(ok)
        self.assertTrue(self.airbase.runways[assigned_rwy].is_available())
        self.assertIn("EMERGENCY_DELAYED", [h["event_key"] for h in self.agent.reward_system.history])

        # 3a. Rule 8 allows landing a small AT72 on short 1800m RWY 4 while Heavy emergency waits for Heavy runway
        self.airbase.setup_for_level(16)
        for rid in ("RWY 1", "RWY 2", "RWY 3"):
            self.airbase.runways[rid].occupy(f"OCC-{rid}", duration_seconds=20.0)
        heavy_emerg = Aircraft("BG-HVY", model="B777", fuel_level=45.0, emergency_type=EmergencyType.ENGINE_PROBLEM)
        small = Aircraft("BG-SML", model="AT72", fuel_level=60.0)
        self.airbase.add_aircraft(heavy_emerg)
        self.airbase.add_aircraft(small)
        self.agent.reset_for_level(16)

        validator = PlanValidator()
        ok_r4, issues_r4, _, code_r4 = validator.validate_plan(
            {"assignments": [{"flight_id": "BG-SML", "action": "AUTHORIZE_LANDING", "assigned_runway": "RWY 4"}]},
            self.agent.observer.observe(),
        )
        self.assertTrue(ok_r4, f"{code_r4}: {issues_r4}")

        # 3b. Heavy aircraft waiting while only short 1800m RWY 4 is available does NOT spin timeout_auto_executes
        self.airbase.setup_for_level(16)
        for rid in ("RWY 1", "RWY 2", "RWY 3"):
            self.airbase.runways[rid].occupy(f"OCC-{rid}", duration_seconds=25.0)
        heavy_only = Aircraft("BG-HVY2", model="B777", fuel_level=45.0, emergency_type=EmergencyType.ENGINE_PROBLEM)
        self.airbase.add_aircraft(heavy_only)
        self.agent.reset_for_level(16)

        for _ in range(25):
            self.airbase.update(0.5)
            self.agent.step(0.5)
        self.assertGreaterEqual(heavy_only.hitl_decision_timer, 2.0)
        self.assertEqual(self.agent.stats["timeout_auto_executes"], 0)

    def test_web_memory_db_and_pure_python_audio_fallback(self):
        """Verifies WebAssembly pure-Python memory DB persistence & numpy-free SFX synthesis."""
        import gui.audio as audio_mod

        prev_inst = db_mod._db_instance
        prev_type = config.DB_TYPE
        prev_numpy = audio_mod.NUMPY_AVAILABLE
        csv_path = None
        try:
            config.DB_TYPE = "memory"
            db_mod._db_instance = None
            mem_logger = DatabaseLogger()
            self.assertEqual(mem_logger.db.engine_type, "memory")

            ab = Airbase(level_id=1)
            mem_agent = ATCAgent(ab, mem_logger)
            mem_agent.reset_for_level(1)
            em = Aircraft("BG-WEB", model="B737", fuel_level=14.0, emergency_type=EmergencyType.CRITICAL_FUEL)
            ab.add_aircraft(em)
            mem_agent.step(0.2)
            self.assertTrue(mem_agent.accept_ai_plan())

            mem_logger.update_aircraft_outcome(em.db_aircraft_id, em.db_request_id, 13.5, FlightStatus.LANDED, 1.0)
            mem_logger.log_level_history(1, "COMPLETED", 160, 4, 1)

            counters = mem_logger.get_global_counters()
            self.assertEqual(counters["aircraft_landed"], 1)
            self.assertEqual(counters["hi_score"], 160)

            prog = mem_logger.get_level_progression()
            self.assertEqual(prog["completed_levels"], [1])
            self.assertEqual(prog["max_unlocked"], 2)

            stats = mem_logger.get_stats_dashboard_data()
            self.assertEqual(stats["total_missions"], 1)
            self.assertEqual(stats["successful_landings"], 1)
            self.assertEqual(stats["emergencies_handled"], 1)
            self.assertGreater(len(stats["recent_logs"]), 0)

            csv_path = mem_logger.export_logs_to_csv()
            self.assertTrue(csv_path.exists())

            # Pure-Python array('h') synthesis fallback when numpy is absent
            audio_mod.NUMPY_AVAILABLE = False
            snd_mgr = audio_mod.SoundManager()
            if snd_mgr.enabled:
                self.assertIn("click", snd_mgr.sounds)
        finally:
            if csv_path is not None:
                csv_path.unlink(missing_ok=True)
            audio_mod.NUMPY_AVAILABLE = prev_numpy
            config.DB_TYPE = prev_type
            db_mod._db_instance = prev_inst


if __name__ == "__main__":
    unittest.main()
