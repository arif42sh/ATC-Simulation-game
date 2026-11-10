"""
=============================================================================
SkyATC AI - Airbase Environment Manager (Module 3 + Data Structures)
Manages 2-4 dynamic runways, O(1) Flight ID Hash Map, FIFO queue, and collisions.
=============================================================================
"""

import random
from collections import deque
from typing import Dict, List, Optional, Any, Deque, Tuple
import config
from config import RunwayStatus
from .runway import Runway
from .aircraft import Aircraft, FlightStatus


class WeatherCondition:
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    FOG = "FOG"
    CROSSWIND = "CROSSWIND"
    STORM = "STORM"


class Airbase:
    """
    2D Airbase Simulation Environment supporting 2 to 4 runways depending on level,
    Hash Map O(1) aircraft lookup, FIFO arrival queue, and safety crash detection.
    """

    def __init__(self, level_id: int = 1):
        self.level_id = level_id
        self.runways: Dict[str, Runway] = {}

        # Core Data Structures (Report Section 11)
        self.aircraft_fleet: List[Aircraft] = []
        self.aircraft_map: Dict[str, Aircraft] = {}      # O(1) Hash Map keyed by flight_id
        self.arrival_queue: Deque[str] = deque()         # FIFO arrival order queue
        self._arrival_seq_counter: int = 0

        # Weather & Environmental Conditions
        self.weather = WeatherCondition.CLEAR
        self.wind_speed_kts = 10.0
        self.wind_direction_deg = 90.0
        self.visibility_km = 10.0

        # Airbase Perimeter Holding Orbit Waypoints (10 spaced slots inside canvas X=0..975, Y=50..768)
        self.holding_orbits: List[Tuple[float, float]] = [
            (110.0, 130.0),
            (110.0, 650.0),
            (855.0, 130.0),
            (855.0, 650.0),
            (275.0, 125.0),
            (300.0, 665.0),
            (690.0, 125.0),
            (665.0, 665.0),
            (95.0, 290.0),
            (865.0, 485.0),
        ]
        self.spawn_points: List[Tuple[float, float]] = [
            (55.0, 95.0),
            (55.0, 700.0),
            (920.0, 95.0),
            (920.0, 700.0),
            (270.0, 72.0),
            (300.0, 705.0),
            (695.0, 72.0),
            (665.0, 705.0),
            (45.0, 290.0),
            (925.0, 485.0),
        ]

        # Operational history & crash diagnostics
        self.flight_history: List[Dict[str, Any]] = []
        self.crashed_aircraft: Optional[Aircraft] = None

        self.setup_for_level(level_id)

    def setup_for_level(self, level_id: int):
        """Configures 2, 3, or 4 runways and resets state for the given level."""
        self.level_id = max(1, min(20, int(level_id)))
        lvl_cfg = config.LEVEL_CONFIGS[self.level_id]
        rwy_count = lvl_cfg["runway_count"]

        self.runways.clear()
        for r_cfg in config.RUNWAY_LAYOUTS[rwy_count]:
            self.runways[r_cfg["id"]] = Runway(
                runway_id=r_cfg["id"],
                name=r_cfg["name"],
                length_m=r_cfg["length_m"],
                start=r_cfg["start"],
                end=r_cfg["end"],
                heading=r_cfg["heading"],
            )

        self.aircraft_fleet.clear()
        self.aircraft_map.clear()
        self.arrival_queue.clear()
        self.flight_history.clear()
        self.crashed_aircraft = None
        self._arrival_seq_counter = 0

        self.weather = WeatherCondition.CLEAR
        self.wind_speed_kts = lvl_cfg["wind_speed_kts"]
        self.wind_direction_deg = random.choice([90.0, 180.0, 270.0, 60.0])
        self.visibility_km = 10.0

    def add_aircraft(self, aircraft: Aircraft):
        """Registers aircraft in Hash Map, FIFO queue, and assigns an unoccupied perimeter orbit."""
        self._arrival_seq_counter += 1
        aircraft.arrival_seq = self._arrival_seq_counter

        active_orbits = {
            (round(ac.orbit_x, 1), round(ac.orbit_y, 1))
            for ac in self.aircraft_fleet
            if ac.status == FlightStatus.HOLDING
        }
        slot_idx = (self._arrival_seq_counter - 1) % len(self.holding_orbits)
        for offset in range(len(self.holding_orbits)):
            cand_idx = (self._arrival_seq_counter - 1 + offset) % len(self.holding_orbits)
            cand_orbit = (round(self.holding_orbits[cand_idx][0], 1), round(self.holding_orbits[cand_idx][1], 1))
            if cand_orbit not in active_orbits:
                slot_idx = cand_idx
                break

        if abs(aircraft.x - 120.0) < 1e-3 and abs(aircraft.y - 180.0) < 1e-3:
            sx, sy = self.spawn_points[slot_idx]
            aircraft.x, aircraft.y = sx, sy
        ox, oy = self.holding_orbits[slot_idx]
        aircraft.orbit_x, aircraft.orbit_y = ox, oy

        self.aircraft_fleet.append(aircraft)
        self.aircraft_map[aircraft.flight_id] = aircraft
        self.arrival_queue.append(aircraft.flight_id)

