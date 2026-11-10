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

    def get_aircraft(self, flight_id: str) -> Optional[Aircraft]:
        """O(1) Hash Map retrieval by Flight ID (Report Section 11.3)."""
        return self.aircraft_map.get(flight_id)

    def get_pending_requests(self) -> List[Aircraft]:
        """Returns all aircraft currently waiting in HOLDING pattern for clearance."""
        return [ac for ac in self.aircraft_fleet if ac.status == FlightStatus.HOLDING]

    def get_active_aircraft(self) -> List[Aircraft]:
        """Returns all non-landed, non-crashed aircraft."""
        return [ac for ac in self.aircraft_fleet if ac.is_active_in_airspace()]

    def get_ranked_pending_aircraft(self) -> List[Aircraft]:
        """Returns pending holding aircraft in exact AI Priority Queue order."""
        pending = self.get_pending_requests()
        pending.sort(key=lambda a: (-a.get_priority_score(), a.arrival_seq, a.flight_id))
        return pending

    def get_available_runways(self) -> List[Runway]:
        """Returns list of currently Available runways."""
        return [r for r in self.runways.values() if r.is_available()]

    def set_weather(self, condition: str, wind_speed_kts: float = 12.0, wind_direction_deg: float = 90.0, visibility_km: float = 10.0):
        """Updates weather and temporarily closes compromised short runway during severe storms."""
        self.weather = condition
        self.wind_speed_kts = wind_speed_kts
        self.wind_direction_deg = wind_direction_deg
        self.visibility_km = visibility_km

        # During STORM or extreme crosswind (>34 kts), shortest runway becomes Unavailable
        rwy_ids = list(self.runways.keys())
        if len(rwy_ids) >= 2:
            shortest_rwy = min(self.runways.values(), key=lambda r: r.length_m)
            if condition == WeatherCondition.STORM or (condition == WeatherCondition.CROSSWIND and wind_speed_kts >= 34.0):
                if shortest_rwy.status == RunwayStatus.AVAILABLE:
                    shortest_rwy.set_unavailable(f"Weather ({condition})", duration_seconds=22.0)
            elif shortest_rwy.status == RunwayStatus.UNAVAILABLE and "Weather" in shortest_rwy.status_reason:
                shortest_rwy.release()

    def authorize_landing(self, flight_id: str, runway_id: str, force_unsafe: bool = False) -> bool:
        """
        Clears aircraft to intercept and land on the specified runway.
        If force_unsafe=True (e.g., manual override test), allows collision detection to catch conflicts.
        """
        aircraft = self.get_aircraft(flight_id)
        runway = self.runways.get(runway_id)
        if not aircraft or not runway:
            return False

        if not force_unsafe and not runway.is_available():
            return False

        aircraft.assign_runway_geometry(
            runway_id=runway_id,
            approach_pos=(runway.approach_x, runway.approach_y),
            start_pos=(runway.start_x, runway.start_y),
            end_pos=(runway.end_x, runway.end_y),
            ux=runway.ux,
            uy=runway.uy,
            angle_deg=runway.screen_angle_deg,
        )

        if runway.is_available():
            runway.reserve(flight_id, duration_seconds=0.0)
        return True

    def hold_aircraft(self, flight_id: str) -> bool:
        """Returns aircraft to holding orbit and releases any runway reserved by it."""
        aircraft = self.get_aircraft(flight_id)
        if not aircraft:
            return False
        if aircraft.assigned_runway and aircraft.assigned_runway in self.runways:
            rwy = self.runways[aircraft.assigned_runway]
            if rwy.current_aircraft == flight_id:
                rwy.release()
        aircraft.return_to_holding_orbit()
        return True

    def update(self, dt: float) -> Optional[Aircraft]:
        """
        Steps runway timers, aircraft kinematics, collision/fuel crash detection.
        Returns the crashed Aircraft if a fatal failure occurs, else None.
        """
        for runway in self.runways.values():
            runway.update(dt)

        for ac in self.aircraft_fleet:
            ac.update(dt)
            if ac.status == FlightStatus.CRASHED and self.crashed_aircraft is None:
                self.crashed_aircraft = ac
                if ac.assigned_runway and ac.assigned_runway in self.runways:
                    rwy = self.runways[ac.assigned_runway]
                    if rwy.current_aircraft == ac.flight_id:
                        rwy.release()

            if not ac.history_recorded and ac.status == FlightStatus.LANDED:
                ac.history_recorded = True
                if ac.assigned_runway and ac.assigned_runway in self.runways:
                    rwy = self.runways[ac.assigned_runway]
                    if rwy.current_aircraft == ac.flight_id:
                        rwy.release()
                self.flight_history.append({
                    "flight_id": ac.flight_id,
                    "model": ac.model,
                    "size": ac.aircraft_size,
                    "runway": ac.assigned_runway or "RWY 1",
                    "wait": int(ac.waiting_time),
                    "fuel": int(ac.fuel_level),
                    "is_emergency": ac.is_emergency(),
                    "emergency_type": ac.emergency_type,
                    "decision_maker": ac.decision_maker or "AI_AGENT",
                })

        # Check simultaneous runway rollout conflict (two aircraft rolling on same runway)
        rolling = [ac for ac in self.aircraft_fleet if ac.status == FlightStatus.ROLLING_LAND]
        for i in range(len(rolling)):
            for j in range(i + 1, len(rolling)):
                if rolling[i].assigned_runway == rolling[j].assigned_runway:
                    rolling[i].status = FlightStatus.CRASHED
                    rolling[i].crash_reason = (
                        f"Runway Conflict: {rolling[i].flight_id} and {rolling[j].flight_id} "
                        f"collided on {rolling[i].assigned_runway}!"
                    )
                    self.crashed_aircraft = rolling[i]
                    break

        return self.crashed_aircraft

