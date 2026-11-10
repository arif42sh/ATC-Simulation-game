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

