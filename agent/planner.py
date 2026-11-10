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

