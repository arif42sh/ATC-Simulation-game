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

    def start_level(self, level_id: int) -> Dict[str, Any]:
        """Initializes airbase and traffic queue for a specific level (1-20)."""
        self.current_level = max(1, min(20, int(level_id)))
        self.level_cfg = config.LEVEL_CONFIGS[self.current_level]

        self.airbase.setup_for_level(self.current_level)
        self.spawned_count = 0
        self.target_aircraft = self.level_cfg["total_aircraft"]
        self.spawn_timer = 0.0
        self.event_timer = 0.0
        self.flight_counter = 101 + (self.current_level - 1) * 15
        self.auto_spawn_enabled = True

        # Spawn initial 2-3 flights with a brief grace window so player can orient first
        initial_wave = min(3 if self.current_level >= 6 else 2, self.target_aircraft)
        for idx in range(initial_wave):
            force_emerg = (idx == 0 and self.current_level >= 4)
            ac = self.spawn_aircraft(force_emergency=force_emerg)
            ac.hitl_initial_timer = config.HITL_TIMEOUT_SECONDS + 4.0
            ac.hitl_decision_timer = ac.hitl_initial_timer

        hint = (
            "Drag a plane to a GREEN runway, or press [SPACE] / ACCEPT AI PLAN"
            if self.current_level <= 2
            else f"{self.level_cfg['runway_count']} Runways Active | Land {self.target_aircraft} Aircraft Safely"
        )
        self.trigger_banner(
            f"LEVEL {self.current_level:02d} — {self.level_cfg['difficulty']}",
            hint,
            "NORMAL",
            4.5,
        )
        return self.level_cfg

