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

    def _register_new_aircraft_in_db(self):
        """Logs newly arrived aircraft into aircraft & missions_requests tables once."""
        if not self.db_logger:
            return
        for ac in self.airbase.aircraft_fleet:
            if ac.flight_id not in self._logged_aircraft_ids:
                self._logged_aircraft_ids.add(ac.flight_id)
                ac_id, req_id = self.db_logger.log_aircraft_and_request(ac.to_dict())
                ac.db_aircraft_id = ac_id
                ac.db_request_id = req_id

    def step(self, dt: float):
        """Executes one PEAS cycle: Observe -> Plan/Re-plan -> Poll Async -> HITL 10s Timeout."""
        self._register_new_aircraft_in_db()
        current_state = self.observer.observe()

        # Check if async Gemini 2.5 Flash response finished
        async_res = self.planner.poll_async_upgrade(current_state)
        if async_res:
            if async_res.get("rejected_cloud_plan"):
                self.stats["validation_rejections"] += 1
                self.reward_system.evaluate_action("INVALID_AI_DECISION", note="; ".join(async_res.get("issues", [])))
                self.ui_state["last_validation_msg"] = f"Rejected unsafe LLM plan ({async_res.get('validation_code')})"
            else:
                self._apply_plan_to_ui_and_db(async_res)

        # Event-driven re-planning check
        if self.planner.should_replan(self.last_observed_state, current_state):
            if self.last_observed_state and current_state["situational_metrics"]["pending_count"] > 0:
                self.stats["replan_events"] += 1
            plan = self.planner.generate_plan(current_state, trigger_async_llm=True)
            self._apply_plan_to_ui_and_db(plan)

        # Check HITL 10-second timeout per pending aircraft (only while a compatible runway is free)
        pending_ranked = self.airbase.get_ranked_pending_aircraft()
        if pending_ranked:
            available_rwys = self.airbase.get_available_runways()
            for ac in pending_ranked:
                has_compatible = any(r.supports_aircraft(ac.min_runway_length_m) for r in available_rwys)
                if not has_compatible:
                    if ac.hitl_decision_timer < 2.0:
                        ac.hitl_decision_timer = 2.0
                elif ac.hitl_pending and ac.hitl_decision_timer <= 0.0:
                    if self._execute_timeout_takeover(ac, current_state):
                        break

        # Sync landed outcomes to DB once
        if self.db_logger:
            for ac in self.airbase.aircraft_fleet:
                if ac.status in (FlightStatus.LANDED, FlightStatus.CRASHED) and ac.db_aircraft_id:
                    if not ac.db_outcome_synced:
                        ac.db_outcome_synced = True
                        self.db_logger.update_aircraft_outcome(
                            ac.db_aircraft_id, ac.db_request_id, ac.fuel_level, ac.status, ac.waiting_time
                        )

        self.last_observed_state = current_state

