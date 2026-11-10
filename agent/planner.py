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

