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


