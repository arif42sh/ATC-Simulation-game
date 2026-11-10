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


