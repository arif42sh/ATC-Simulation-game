"""
=============================================================================
SkyATC AI - Google Gemini 2.5 Flash Client & Smart Utility Fallback (Module 4)
Uses official google-genai SDK with structured JSON output, async threads,
event-driven requests, and deterministic Min-Heap utility fallback.
=============================================================================
"""

import json
import time
import threading
from typing import Dict, Any, Callable, Optional
import config
from agent.decision import DecisionEngine

try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_SDK_AVAILABLE = False


SYSTEM_ATC_PROMPT = """
You are the Autonomous Runway Management Agent for SkyATC AI.
Analyze the incoming aircraft and runway state and return STRICT JSON only.

Rules:
1. Only assign runways whose status is "Available". Never assign "Occupied", "Unavailable", or "Under Maintenance".
2. Never assign two aircraft to the same runway or assign one aircraft twice.
3. Priority 1 MUST go to emergencies (ENGINE_PROBLEM, CRITICAL_FUEL, BIRD_STRIKE, MEDICAL) and lowest fuel.
4. Respect runway length constraints: aircraft min_runway_length_m must be <= runway length_m.
5. Keep "reasoning" concise (<= 65 characters) explaining the top priority choice.

Required JSON schema:
{
  "reasoning": "Fuel 12% <= Critical; RWY 1 occupied",
  "assignments": [
    {
      "flight_id": "BG-101",
      "priority": 1,
      "assigned_runway": "RWY 2",
      "action": "AUTHORIZE_LANDING",
      "rationale": "Critical fuel emergency routed to available RWY 2"
    }
  ]
}
"""


class LLMClient:
    """
    Integrates Google Gemini API (gemini-2.5-flash via google-genai SDK) with
    non-blocking background async calls and deterministic Min-Heap Utility fallback.
    """

    def __init__(self, decision_engine: Optional[DecisionEngine] = None):
        self.api_key = config.GEMINI_API_KEY.strip()
        self.model = config.AI_MODEL or "gemini-2.5-flash"
        self.decision_engine = decision_engine or DecisionEngine()

        self.sdk_ready = bool(self.api_key and GENAI_SDK_AVAILABLE)
        self.client = genai.Client(api_key=self.api_key) if self.sdk_ready else None

        self.active_mode = "LLM API Ready" if self.sdk_ready else "Local Utility Fallback"
        self.last_latency_ms: float = 0.0
        self.last_error: str = ""
        self._seq_lock = threading.Lock()
        self._latest_seq = 0

