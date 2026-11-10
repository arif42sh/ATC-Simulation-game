"""
=============================================================================
SkyATC AI - Scenario & Dynamic Event Loader
Loads structured V2 evaluation test scenarios from data/scenarios.json.
=============================================================================
"""

import json
from typing import Optional
import config
from .aircraft import Aircraft, EmergencyType
from .airbase import Airbase, WeatherCondition
from .levels import LevelManager


class EventManager:
    """
    Loads evaluation scenarios (for headless benchmarking & unit tests)
    and wraps LevelManager dynamic events.
    """

    def __init__(self, airbase: Airbase, level_manager: Optional[LevelManager] = None):
        self.airbase = airbase
        self.level_manager = level_manager or LevelManager(airbase)
        self.scenarios_file = config.DATA_DIR / "scenarios.json"
        self.active_scenario_name = "Standard Airbase Level"

    def load_scenario(self, scenario_key: str) -> bool:
        """Loads a pre-configured V2 landing scenario from data/scenarios.json."""
        if not self.scenarios_file.exists():
            return False

        try:
            with open(self.scenarios_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenario = data.get("scenarios", {}).get(scenario_key)
            if not scenario:
                return False

            self.active_scenario_name = scenario.get("title", scenario_key)
            level_id = int(scenario.get("level_id", 1))
            self.airbase.setup_for_level(level_id)
            self.level_manager.current_level = level_id
            self.level_manager.auto_spawn_enabled = False

            w_data = scenario.get("weather", {})
            self.airbase.set_weather(
                condition=w_data.get("condition", WeatherCondition.CLEAR),
                wind_speed_kts=w_data.get("wind_speed_kts", 10.0),
                wind_direction_deg=w_data.get("wind_direction_deg", 90.0),
                visibility_km=w_data.get("visibility_km", 10.0),
            )

            # Optional runway state overrides (e.g., maintenance / occupied)
            for r_id, r_state in scenario.get("runway_states", {}).items():
                rwy = self.airbase.runways.get(r_id)
                if rwy:
                    if r_state == "UNDER_MAINTENANCE":
                        rwy.set_maintenance("Scenario Maintenance", 30.0)
                    elif r_state == "UNAVAILABLE":
                        rwy.set_unavailable("Scenario Unavailable", 30.0)

            for idx, ac_raw in enumerate(scenario.get("aircraft", []), start=1):
                flight_id = ac_raw.get("flight_id", f"BG-{100 + idx}")
                ac = Aircraft(
                    flight_id=flight_id,
                    model=ac_raw.get("model", "B737"),
                    fuel_level=ac_raw.get("fuel_level", 75.0),
                    emergency_type=ac_raw.get("emergency_type", EmergencyType.NONE),
                )
                if "waiting_time" in ac_raw:
                    ac.waiting_time = float(ac_raw["waiting_time"])

                pre_rwy = ac_raw.get("pre_assigned_runway")
                self.airbase.add_aircraft(ac)
                if pre_rwy:
                    self.airbase.authorize_landing(flight_id, pre_rwy)

            return True
        except Exception as exc:
            print(f"[EVENT ERROR] Could not load scenario '{scenario_key}': {exc}")
            return False
