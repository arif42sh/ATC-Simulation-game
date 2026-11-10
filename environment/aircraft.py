"""
=============================================================================
SkyATC AI - Aircraft Management & Kinematics (Module 2)
Landing-focused aircraft physics, holding orbits, fuel burn & priority metrics.
=============================================================================
"""

import math
from typing import Dict, Any, Optional, Tuple, List
import config


class EmergencyType:
    NONE = "NONE"
    CRITICAL_FUEL = "CRITICAL_FUEL"
    ENGINE_PROBLEM = "ENGINE_PROBLEM"
    BIRD_STRIKE = "BIRD_STRIKE"
    MEDICAL = "MEDICAL"


class FlightStatus:
    HOLDING = "HOLDING"            # Orbiting in perimeter holding pattern
    INTERCEPT = "INTERCEPT"        # Turning to intercept assigned runway approach fix
    APPROACHING = "APPROACHING"    # Final approach glideslope toward runway threshold
    ROLLING_LAND = "ROLLING_LAND"  # Touchdown & deceleration along runway centerline
    LANDED = "LANDED"              # Safely landed and vacated runway
    CRASHED = "CRASHED"            # Fuel exhausted or runway collision


class Aircraft:
    """
    Represents an incoming aircraft requesting landing at the airbase.
    Handles circular holding patterns, vector approach alignment, and fuel burn.
    """

    def __init__(
        self,
        flight_id: str,
        model: str = "B737",
        fuel_level: float = 75.0,
        emergency_type: str = EmergencyType.NONE,
        x: float = 120.0,
        y: float = 180.0,
        orbit_center: Tuple[float, float] = (140.0, 200.0),
        orbit_radius: float = 34.0,
        arrival_seq: int = 0,
    ):
        self.flight_id = flight_id
        self.callsign = flight_id  # Clean alias for telemetry consistency
        self.model = model

        spec = config.AIRCRAFT_SPECS.get(model, config.AIRCRAFT_SPECS["B737"])
        self.aircraft_size: str = spec["size"]
        self.min_runway_length_m: int = spec["min_runway_m"]
        self.cruise_speed: float = spec["speed_kts"]

        self.initial_fuel = max(1.0, min(100.0, float(fuel_level)))
        self.fuel_level = self.initial_fuel
        self.emergency_type = emergency_type
        if self.fuel_level <= config.FUEL_CRITICAL_THRESHOLD and self.emergency_type == EmergencyType.NONE:
            self.emergency_type = EmergencyType.CRITICAL_FUEL

        # Operational state
        self.status: str = FlightStatus.HOLDING
        self.assigned_runway: Optional[str] = None
        self.waiting_time: float = 0.0
        self.arrival_seq: int = arrival_seq
        self.crash_reason: str = ""

        # Human-in-the-Loop (HITL) 10-second decision window
        self.hitl_decision_timer: float = config.HITL_TIMEOUT_SECONDS
        self.hitl_initial_timer: float = config.HITL_TIMEOUT_SECONDS
        self.hitl_pending: bool = True
        self.decision_maker: Optional[str] = None

        # Position & Kinematics (2D screen space)
        self.x = float(x)
        self.y = float(y)
        self.orbit_x, self.orbit_y = float(orbit_center[0]), float(orbit_center[1])
        self.orbit_radius = float(orbit_radius)

        # Assigned runway geometry vectors (populated when cleared)
        self.approach_x = 200.0
        self.approach_y = 315.0
        self.rwy_start_x = 235.0
        self.rwy_start_y = 315.0
        self.rwy_end_x = 625.0
        self.rwy_end_y = 315.0
        self.rwy_ux = 1.0
        self.rwy_uy = 0.0
        self.rwy_angle_deg = 0.0

        self.speed = self.cruise_speed
        self.heading = math.degrees(math.atan2(self.orbit_y - self.y, self.orbit_x - self.x))
        self.altitude_ft = 3800.0
        self.distance_nm = self._compute_airbase_distance_nm()

        self.trail: List[Tuple[float, float]] = [(self.x, self.y)]
        self.touchdown_occurred = False
        self.touchdown_sound_played = False
        self.history_recorded = False
        self.db_outcome_synced = False
        self.hold_conflict_rewarded = False
        self.db_aircraft_id: Optional[int] = None
        self.db_request_id: Optional[int] = None

    def _compute_airbase_distance_nm(self) -> float:
        """Computes approximate distance from airbase center (420, 380) in NM."""
        px_dist = math.hypot(self.x - 420.0, self.y - 380.0)
        return round(px_dist / 24.0, 1)

    def assign_runway_geometry(
        self,
        runway_id: str,
        approach_pos: Tuple[float, float],
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        ux: float,
        uy: float,
        angle_deg: float,
    ):
        """Clears aircraft out of holding pattern onto final runway intercept."""
        self.assigned_runway = runway_id
        self.approach_x, self.approach_y = approach_pos
        self.rwy_start_x, self.rwy_start_y = start_pos
        self.rwy_end_x, self.rwy_end_y = end_pos
        self.rwy_ux = ux
        self.rwy_uy = uy
        self.rwy_angle_deg = angle_deg
        self.status = FlightStatus.INTERCEPT
        self.hitl_pending = False
        self.hold_conflict_rewarded = False

    def return_to_holding_orbit(self):
        """Places aircraft back into holding pattern (used for manual hold)."""
        if self.status == FlightStatus.HOLDING:
            self.hitl_decision_timer = config.HITL_TIMEOUT_SECONDS
            return
        self.assigned_runway = None
        self.status = FlightStatus.HOLDING
        self.hitl_pending = True
        self.hitl_decision_timer = config.HITL_TIMEOUT_SECONDS
        self.altitude_ft = 3800.0

    def is_emergency(self) -> bool:
        return self.emergency_type != EmergencyType.NONE or self.fuel_level <= config.FUEL_CRITICAL_THRESHOLD

    def is_active_in_airspace(self) -> bool:
        return self.status not in (FlightStatus.LANDED, FlightStatus.CRASHED)

    def update(self, dt: float):
        """Advances waiting time, HITL timer, fuel burn, and 2D motion."""
        if not self.is_active_in_airspace():
            return

        if self.status == FlightStatus.HOLDING:
            self.waiting_time += dt
            if self.hitl_pending and self.hitl_decision_timer > 0.0:
                self.hitl_decision_timer = max(0.0, self.hitl_decision_timer - dt)

        # Fuel burn (pauses after touchdown roll)
        if self.status in (FlightStatus.HOLDING, FlightStatus.INTERCEPT, FlightStatus.APPROACHING):
            burn_rate = (
                config.FUEL_CONSUMPTION_RATE_HOLDING
                if self.status == FlightStatus.HOLDING
                else config.FUEL_CONSUMPTION_RATE_APPROACH
            )
            self.fuel_level = max(0.0, self.fuel_level - burn_rate * dt)

            if self.fuel_level <= config.FUEL_CRITICAL_THRESHOLD and self.emergency_type == EmergencyType.NONE:
                self.emergency_type = EmergencyType.CRITICAL_FUEL

            if self.fuel_level <= 0.0:
                self.status = FlightStatus.CRASHED
                self.crash_reason = f"{self.flight_id} exhausted all fuel while waiting to land."
                self.speed = 0.0
                return

        self._update_position(dt)
        self.distance_nm = self._compute_airbase_distance_nm()

