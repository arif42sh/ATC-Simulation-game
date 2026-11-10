"""
=============================================================================
SkyATC AI - Level Progression Manager (Module 9)
Manages 20 progressive levels (Easy/Medium/Hard/Expert), 2-4 runways,
aircraft wave spawning, and dynamic runway maintenance/weather events.
=============================================================================
"""

import random
from typing import Dict, Any, Optional
import config
from .aircraft import Aircraft, EmergencyType
from .airbase import Airbase, WeatherCondition


class LevelManager:
    """
    Controls level setup, traffic generation, dynamic runway maintenance,
    and level completion status for Levels 01-20.
    """

    def __init__(self, airbase: Airbase):
        self.airbase = airbase
        self.current_level: int = 1
        self.level_cfg: Dict[str, Any] = config.LEVEL_CONFIGS[1]

        self.spawned_count: int = 0
        self.target_aircraft: int = self.level_cfg["total_aircraft"]
        self.spawn_timer: float = 0.0
        self.event_timer: float = 0.0
        self.flight_counter: int = 101

        self.active_banner: Optional[Dict[str, Any]] = None
        self.auto_spawn_enabled: bool = True

