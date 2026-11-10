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

