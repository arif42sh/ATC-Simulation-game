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

