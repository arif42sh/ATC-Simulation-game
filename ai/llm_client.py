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

        self.sdk_ready = bool((not config.IS_WEB) and self.api_key and GENAI_SDK_AVAILABLE)
        self.client = genai.Client(api_key=self.api_key) if self.sdk_ready else None

        self.active_mode = "LLM API Ready" if self.sdk_ready else "Local Utility Fallback"
        self.last_latency_ms: float = 0.0
        self.last_error: str = ""
        self._seq_lock = threading.Lock()
        self._latest_seq = 0

    def is_api_configured(self) -> bool:
        return self.sdk_ready

    def generate_plan_sync(self, state_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a plan synchronously (tries Gemini API if configured, else
        uses Deterministic Min-Heap Utility Engine).
        """
        t0 = time.perf_counter()
        if self.sdk_ready and self.client is not None:
            try:
                cloud_plan = self._call_gemini_sdk(state_summary)
                if cloud_plan and isinstance(cloud_plan.get("assignments"), list):
                    self.last_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    self.active_mode = f"LLM API ({self.model})"
                    self.last_error = ""
                    cloud_plan["source"] = "LLM_API"
                    cloud_plan["latency_ms"] = self.last_latency_ms
                    return cloud_plan
            except Exception as exc:
                self.last_error = str(exc)
                print(f"[AI WARNING] Gemini API failed ({exc}); using Local Utility Fallback.")

        plan = self.decision_engine.generate_deterministic_plan(state_summary)
        self.last_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        self.active_mode = "Local Utility Fallback"
        plan["source"] = "LOCAL_UTILITY"
        plan["latency_ms"] = self.last_latency_ms
        return plan

    def request_plan_async(
        self,
        state_summary: Dict[str, Any],
        on_complete: Callable[[int, Dict[str, Any]], None],
    ) -> int:
        """
        Non-blocking event-driven Gemini API request dispatched in a background thread.
        Returns sequence id; stale responses are ignored by caller if newer event occurred.
        """
        with self._seq_lock:
            self._latest_seq += 1
            req_seq = self._latest_seq

        if not self.sdk_ready or self.client is None:
            return req_seq

        def _worker():
            t0 = time.perf_counter()
            try:
                cloud_plan = self._call_gemini_sdk(state_summary)
                latency = round((time.perf_counter() - t0) * 1000.0, 2)
                if cloud_plan and isinstance(cloud_plan.get("assignments"), list):
                    with self._seq_lock:
                        if req_seq != self._latest_seq:
                            return
                    self.last_latency_ms = latency
                    self.active_mode = f"LLM API ({self.model})"
                    self.last_error = ""
                    cloud_plan["source"] = "LLM_API"
                    cloud_plan["latency_ms"] = latency
                    on_complete(req_seq, cloud_plan)
            except Exception as exc:
                self.last_error = str(exc)
                self.active_mode = "Local Utility Fallback"

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return req_seq

    def _call_gemini_sdk(self, state_summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calls Gemini 2.5 Flash with enforced structured JSON output."""
        if not self.client or types is None:
            return None

        compact_state = {
            "level_id": state_summary.get("level_id"),
            "weather": state_summary.get("weather"),
            "runways": {
                r_id: {
                    "length_m": r["length_m"],
                    "status": r["status"],
                    "heading": r.get("heading"),
                }
                for r_id, r in state_summary.get("runways", {}).items()
            },
            "holding_aircraft": [
                {
                    "flight_id": ac["flight_id"],
                    "model": ac["model"],
                    "size": ac["aircraft_size"],
                    "min_runway_length_m": ac["min_runway_length_m"],
                    "fuel_level": ac["fuel_level"],
                    "emergency_type": ac["emergency_type"],
                    "distance_nm": ac["distance_nm"],
                    "waiting_time": ac["waiting_time"],
                }
                for ac in state_summary.get("aircraft", [])
                if ac.get("status") == "HOLDING"
            ],
        }

        prompt = f"{SYSTEM_ATC_PROMPT}\n\nSimulation State:\n{json.dumps(compact_state)}"
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        raw_text = (response.text or "").strip()
        if not raw_text:
            return None
        return json.loads(raw_text)
