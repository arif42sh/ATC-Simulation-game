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

    def _apply_plan_to_ui_and_db(self, plan: Dict[str, Any]):
        """Updates sidebar recommendation text and logs top agent decision to DB."""
        self.ui_state["current_plan"] = plan
        self.ui_state["reason_badge"] = plan.get("reasoning", "Utility sequencing active.")
        source = plan.get("source", "LOCAL_UTILITY")
        self.ui_state["mode_label"] = f"LLM API ({config.AI_MODEL})" if source == "LLM_API" else "Local Utility Fallback"

        lines: List[str] = []
        for item in plan.get("assignments", [])[:3]:
            fid = item.get("flight_id")
            rwy = item.get("assigned_runway") or "HOLD ORBIT"
            prio = item.get("priority", 1)
            lines.append(f"Priority {prio}: {fid} -> {rwy}")

            sig = (item.get("assigned_runway"), source, plan.get("validation_code", "VALID"))
            if self.db_logger and fid:
                ac = self.airbase.get_aircraft(fid)
                prev_id = self._last_decision_id_by_flight.get(fid)
                if prev_id is None:
                    dec_id = self.db_logger.log_agent_decision(
                        request_id=ac.db_request_id if ac else None,
                        flight_id=fid,
                        priority=prio,
                        assigned_runway=item.get("assigned_runway"),
                        ai_reason=item.get("rationale", plan.get("reasoning", "")),
                        decision_source=source,
                        validation_status=plan.get("validation_code", "VALID"),
                        decision_time_ms=plan.get("latency_ms", 1.0),
                    )
                    if dec_id:
                        self._last_decision_id_by_flight[fid] = dec_id
                        self._last_decision_sig_by_flight[fid] = sig
                elif sig != self._last_decision_sig_by_flight.get(fid):
                    self.db_logger.update_agent_decision(
                        decision_id=prev_id,
                        priority=prio,
                        assigned_runway=item.get("assigned_runway"),
                        ai_reason=item.get("rationale", plan.get("reasoning", "")),
                        decision_source=source,
                        validation_status=plan.get("validation_code", "VALID"),
                        decision_time_ms=plan.get("latency_ms", 1.0),
                    )
                    self._last_decision_sig_by_flight[fid] = sig

        self.ui_state["plan_lines"] = lines

    def _execute_timeout_takeover(self, aircraft: Aircraft, current_state: Dict[str, Any]) -> bool:
        """Autonomous AI takeover when 10-second HITL timer reaches 0."""
        plan = self.planner.current_plan or self.planner.generate_plan(current_state, trigger_async_llm=False)

        # Re-validate right before execution to guarantee zero stale conflicts
        is_valid, _, valid_actions, _ = self.validator.validate_plan(plan, current_state)
        if not is_valid or not valid_actions:
            plan = self.planner.generate_plan(current_state, trigger_async_llm=False)
            valid_actions = plan.get("assignments", [])

        chosen_item = next((a for a in valid_actions if a.get("flight_id") == aircraft.flight_id), None)
        if not chosen_item or chosen_item.get("action") == "HOLD" or not chosen_item.get("assigned_runway"):
            # Safe hold orbit if no compatible runway is free (award conflict avoidance once per hold)
            aircraft.hitl_decision_timer = 4.0
            if not aircraft.hold_conflict_rewarded:
                aircraft.hold_conflict_rewarded = True
                self.stats["conflicts_prevented"] += 1
                self.reward_system.evaluate_action("RUNWAY_CONFLICT_AVOIDED", aircraft.flight_id, "Hold orbit while runways busy")
            return False

        rwy_id = chosen_item["assigned_runway"]
        if self.airbase.authorize_landing(aircraft.flight_id, rwy_id):
            aircraft.decision_maker = "AI_AGENT"
            self.stats["timeout_auto_executes"] += 1
            self._record_landing_rewards(aircraft, rwy_id, decision_type="TIMEOUT_AUTO_EXECUTE", is_override=False)
            self._push_notification(f"Timeout Auto-Execute: {aircraft.flight_id} -> {rwy_id}")
            self._refresh_plan_after_action()
            return True
        return False

