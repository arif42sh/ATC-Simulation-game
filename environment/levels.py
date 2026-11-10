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

    def trigger_banner(self, title: str, message: str, alert_type: str = "NORMAL", duration: float = 3.5):
        self.active_banner = {
            "title": title,
            "message": message,
            "type": alert_type,
            "timer": duration,
        }

    def spawn_aircraft(self, force_emergency: Optional[bool] = None) -> Aircraft:
        """Spawns a new incoming aircraft tailored to the current level's difficulty."""
        flight_id = f"BG-{self.flight_counter}"
        self.flight_counter += 1
        self.spawned_count += 1

        # Choose aircraft model & size based on level heavy_chance
        if random.random() < self.level_cfg["heavy_chance"]:
            model = random.choice(["B777", "A350", "C17"])
        elif self.current_level >= 11 and random.random() < 0.30:
            model = random.choice(["AT72", "C208"])
        else:
            model = random.choice(["B737", "A320", "AT72"])

        f_min, f_max = self.level_cfg["fuel_range"]
        fuel = round(random.uniform(f_min, f_max), 1)

        is_emerg = force_emergency if force_emergency is not None else (random.random() < self.level_cfg["emergency_chance"])
        emerg = EmergencyType.NONE
        if is_emerg:
            emerg = random.choice([
                EmergencyType.CRITICAL_FUEL,
                EmergencyType.ENGINE_PROBLEM,
                EmergencyType.BIRD_STRIKE,
                EmergencyType.MEDICAL,
            ])
            if emerg == EmergencyType.CRITICAL_FUEL:
                fuel = round(random.uniform(15.5, 19.5), 1)
            elif emerg == EmergencyType.ENGINE_PROBLEM:
                fuel = min(fuel, round(random.uniform(26.0, 44.0), 1))

        ac = Aircraft(flight_id=flight_id, model=model, fuel_level=fuel, emergency_type=emerg)
        self.airbase.add_aircraft(ac)

        if ac.is_emergency():
            self.trigger_banner(
                "EMERGENCY INBOUND",
                f"{flight_id} ({model}) declares {emerg.replace('_', ' ')}! Fuel: {int(fuel)}%",
                "EMERGENCY",
                4.0,
            )
        return ac

    def trigger_random_runway_event(self):
        """Triggers temporary maintenance or weather restriction on higher levels."""
        if random.random() < 0.55:
            # Put one non-primary available runway under maintenance briefly
            candidates = [r for r in self.airbase.runways.values() if r.is_available() and r.id != "RWY 1"]
            if candidates:
                chosen = random.choice(candidates)
                chosen.set_maintenance("FOD Sweep & Maintenance", duration_seconds=15.0)
                self.trigger_banner(
                    "RUNWAY MAINTENANCE",
                    f"{chosen.id} temporarily Under Maintenance (15s)",
                    "RUNWAY",
                    3.5,
                )
        else:
            cond = random.choice([WeatherCondition.RAIN, WeatherCondition.CROSSWIND, WeatherCondition.CLEAR])
            wind = self.level_cfg["wind_speed_kts"] + (16.0 if cond == WeatherCondition.CROSSWIND else 0.0)
            self.airbase.set_weather(cond, wind_speed_kts=wind, wind_direction_deg=random.choice([90.0, 180.0, 270.0]))
            if cond != WeatherCondition.CLEAR:
                self.trigger_banner(
                    "WEATHER UPDATE",
                    f"{cond} active — Wind {int(wind)} kts",
                    "WEATHER",
                    3.5,
                )

    def update(self, dt: float):
        """Advances wave spawn timers and dynamic runway/weather events."""
        if self.active_banner:
            self.active_banner["timer"] -= dt
            if self.active_banner["timer"] <= 0.0:
                self.active_banner = None

        if not self.auto_spawn_enabled:
            return

        # Spawn remaining aircraft up to level target
        active_count = len(self.airbase.get_active_aircraft())
        if self.spawned_count < self.target_aircraft and active_count < self.level_cfg["max_concurrent"]:
            self.spawn_timer += dt
            if self.spawn_timer >= self.level_cfg["spawn_interval"]:
                self.spawn_timer = 0.0
                self.spawn_aircraft()

        # Dynamic maintenance / weather shift events
        if self.level_cfg["maintenance_chance"] > 0.0:
            self.event_timer += dt
            if self.event_timer >= 20.0:
                self.event_timer = 0.0
                if random.random() < self.level_cfg["maintenance_chance"]:
                    self.trigger_random_runway_event()

    def is_level_complete(self) -> bool:
        """True once all target aircraft for the level have landed safely."""
        if self.airbase.crashed_aircraft is not None:
            return False
        landed = len(self.airbase.flight_history)
        active = len(self.airbase.get_active_aircraft())
        return self.spawned_count >= self.target_aircraft and active == 0 and landed >= self.target_aircraft
