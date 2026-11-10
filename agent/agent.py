"""
=============================================================================
SkyATC AI - Autonomous ATC Agent Controller (Modules 4 & 6)
Coordinates PEAS loop, 10s HITL window, Accept/Override, and DB logging.
=============================================================================
"""

from typing import Dict, Any, List, Optional
import config
from config import RunwayStatus
from environment.airbase import Airbase
from environment.aircraft import Aircraft, FlightStatus
from ai.llm_client import LLMClient
from database.queries import DatabaseLogger
from .observer import StateObserver
from .decision import DecisionEngine
from .validator import PlanValidator
from .planner import GoalBasedPlanner
from .reward import RewardSystem


class ATCAgent:
    """
    Utility-Based Agent with Goal-Based Planning, 9-rule Plan Validation,
    and a 10-second Human-in-the-Loop (HITL) control window.
    """

    def __init__(self, airbase: Airbase, db_logger: Optional[DatabaseLogger] = None):
        self.airbase = airbase
        self.db_logger = db_logger

        self.observer = StateObserver(self.airbase)
        self.decision_engine = DecisionEngine()
        self.llm_client = LLMClient(self.decision_engine)
        self.validator = PlanValidator()
        self.planner = GoalBasedPlanner(self.llm_client, self.validator, self.decision_engine)
        self.reward_system = RewardSystem(self.db_logger)

        self.last_observed_state: Dict[str, Any] = {}
        self.notifications: List[str] = []
        self._last_decision_id_by_flight: Dict[str, int] = {}
        self._last_decision_sig_by_flight: Dict[str, tuple] = {}
        self._logged_aircraft_ids: set = set()

        self.stats: Dict[str, Any] = {
            "landings": 0,
            "emergencies_handled": 0,
            "conflicts_prevented": 0,
            "validation_rejections": 0,
            "ai_accepts": 0,
            "player_overrides": 0,
            "timeout_auto_executes": 0,
            "replan_events": 0,
        }

        self.ui_state: Dict[str, Any] = {
            "mode_label": "Local Utility Fallback" if not self.llm_client.is_api_configured() else "LLM API Ready",
            "reason_badge": "Monitoring airspace for incoming aircraft...",
            "plan_lines": [],
            "current_plan": None,
            "last_validation_msg": "All safety guardrails active",
        }

    def reset_for_level(self, level_id: int):
        """Resets agent state and syncs level runways with database."""
        for k in self.stats:
            self.stats[k] = 0
        self.reward_system.reset(level_id)
        self.last_observed_state = {}
        self.notifications.clear()
        self._last_decision_id_by_flight.clear()
        self._last_decision_sig_by_flight.clear()
        self._logged_aircraft_ids.clear()
        self.planner.current_plan = None
        self.ui_state["current_plan"] = None
        self.ui_state["plan_lines"] = []
        self.ui_state["reason_badge"] = "Monitoring incoming priority queue..."
        if self.db_logger:
            self.db_logger.sync_runways(level_id, self.airbase.runways)

