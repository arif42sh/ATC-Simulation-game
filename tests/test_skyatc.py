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

