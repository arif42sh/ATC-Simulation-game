"""
=============================================================================
SkyATC AI - Goal-Based Operational Planner (Module 4)
Event-driven planning, async Gemini integration, and dynamic re-planning.
=============================================================================
"""

import threading
from typing import Dict, Any, Optional
from ai.llm_client import LLMClient
from .decision import DecisionEngine
from .validator import PlanValidator


class GoalBasedPlanner:
    """
    Coordinates landing sequences across 2-4 runways.
    Produces immediate validated Min-Heap plans and upgrades asynchronously via
    Gemini 2.5 Flash on key simulation events (arrival, emergency, runway change).
    """

    def __init__(self, llm_client: LLMClient, validator: PlanValidator, decision_engine: DecisionEngine):
        self.llm_client = llm_client
        self.validator = validator
        self.decision_engine = decision_engine

        self.current_plan: Optional[Dict[str, Any]] = None
        self.plan_version: int = 0
        self._pending_async_plan: Optional[Dict[str, Any]] = None
        self._async_lock = threading.Lock()
        self._last_async_seq: int = 0

    def should_replan(self, prev_state: Dict[str, Any], curr_state: Dict[str, Any]) -> bool:
        """
        Event-driven trigger check (Game Improvement Sec 2):
        Only re-plan on new arrivals, emergency changes, runway status shifts, or weather shifts.
        """
        if not prev_state:
            return bool(curr_state.get("situational_metrics", {}).get("pending_count", 0) > 0)

        p_met = prev_state.get("situational_metrics", {})
        c_met = curr_state.get("situational_metrics", {})

        # 1. New aircraft arrival or queue change
        if p_met.get("pending_ids") != c_met.get("pending_ids"):
            return True

        # 2. New emergency declared
        if c_met.get("emergency_count", 0) > p_met.get("emergency_count", 0):
            return True

        # 3. Runway availability / maintenance / occupancy status changed
        if p_met.get("runway_signature") != c_met.get("runway_signature"):
            return True

        # 4. Weather condition changed
        if prev_state.get("weather", {}).get("condition") != curr_state.get("weather", {}).get("condition"):
            return True

        return False

    def generate_plan(self, airbase_state: Dict[str, Any], trigger_async_llm: bool = True) -> Dict[str, Any]:
        """
        Immediately produces a validated deterministic Min-Heap plan so UI & HITL
        never stall, and optionally dispatches an event-driven Gemini 2.5 Flash request.
        """
        raw_plan = self.decision_engine.generate_deterministic_plan(airbase_state)
        is_valid, issues, valid_actions, val_code = self.validator.validate_plan(raw_plan, airbase_state)

        self.plan_version += 1
        sanitized = {
            "version": self.plan_version,
            "reasoning": raw_plan.get("reasoning", "Utility plan ready."),
            "source": "LOCAL_UTILITY",
            "is_valid": is_valid,
            "validation_code": val_code,
            "issues": issues,
            "assignments": valid_actions,
            "latency_ms": self.llm_client.last_latency_ms or 1.2,
        }
        self.current_plan = sanitized

        if trigger_async_llm and self.llm_client.is_api_configured():
            pending_count = airbase_state.get("situational_metrics", {}).get("pending_count", 0)
            if pending_count > 0:
                def _on_llm_ready(seq: int, cloud_plan: Dict[str, Any]):
                    with self._async_lock:
                        if seq >= self._last_async_seq:
                            self._pending_async_plan = cloud_plan

                self._last_async_seq = self.llm_client.request_plan_async(airbase_state, _on_llm_ready)

        return sanitized

