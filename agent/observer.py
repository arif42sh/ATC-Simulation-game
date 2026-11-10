"""
=============================================================================
SkyATC AI - State Observer (PEAS Sensors Layer)
Perceives dynamic airbase state, aircraft queue, fuel, distance, and runways.
=============================================================================
"""

from typing import Dict, Any
import config
from config import RunwayStatus
from environment.airbase import Airbase


class StateObserver:
    """Implements the PEAS Sensor component for the ATC Agent."""

    def __init__(self, airbase: Airbase):
        self.airbase = airbase

    def observe(self) -> Dict[str, Any]:
        base_state = self.airbase.get_state_summary()
        pending = [ac for ac in base_state["aircraft"] if ac["status"] == "HOLDING"]
        emergencies = [
            ac for ac in pending
            if ac["emergency_type"] != "NONE" or ac["fuel_level"] <= config.FUEL_CRITICAL_THRESHOLD
        ]
        available_runways = [
            r_id for r_id, r in base_state["runways"].items()
            if r["status"] == RunwayStatus.AVAILABLE
        ]
        runway_signature = tuple((r_id, r["status"]) for r_id, r in sorted(base_state["runways"].items()))

        base_state["situational_metrics"] = {
            "pending_count": len(pending),
            "emergency_count": len(emergencies),
            "available_runway_count": len(available_runways),
            "runway_signature": runway_signature,
            "pending_ids": tuple(sorted(ac["flight_id"] for ac in pending)),
            "weather_warning": base_state["weather"]["condition"] in ("STORM", "CROSSWIND"),
        }
        return base_state
