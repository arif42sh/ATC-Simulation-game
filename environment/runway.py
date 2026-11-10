"""
=============================================================================
SkyATC AI - Runway Model (Module 3)
Manages individual runways, dynamic availability states, and geometry vectors.
=============================================================================
"""

import math
from typing import Optional, Dict, Any, Tuple
from config import RunwayStatus


class Runway:
    """
    Represents a physical runway supporting dynamic availability states:
    Available, Occupied, Unavailable, and Under Maintenance.
    """

    def __init__(
        self,
        runway_id: str,
        name: str,
        length_m: int,
        start: Tuple[float, float],
        end: Tuple[float, float],
        heading: int = 90,
    ):
        self.id = runway_id
        self.name = name
        self.length_m = length_m
        self.heading = heading

        # Physical screen geometry
        self.start_x, self.start_y = float(start[0]), float(start[1])
        self.end_x, self.end_y = float(end[0]), float(end[1])

        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        self.pixel_length = max(1.0, math.hypot(dx, dy))
        self.ux = dx / self.pixel_length
        self.uy = dy / self.pixel_length
        self.screen_angle_deg = math.degrees(math.atan2(dy, dx))

        # Final approach entry fix (upstream of threshold)
        self.approach_x = self.start_x - self.ux * 85.0
        self.approach_y = self.start_y - self.uy * 85.0
        self.center_x = (self.start_x + self.end_x) * 0.5
        self.center_y = (self.start_y + self.end_y) * 0.5

        # Dynamic Runway Status (Report Section 6.3)
        self.status: str = RunwayStatus.AVAILABLE
        self.status_reason: str = ""
        self.current_aircraft: Optional[str] = None
        self.occupancy_timer: float = 0.0
        self.closure_timer: float = 0.0
        self.total_operations_handled: int = 0

    def is_available(self) -> bool:
        """Returns True only if runway is Available and unoccupied."""
        return self.status == RunwayStatus.AVAILABLE and self.current_aircraft is None

    def supports_aircraft(self, min_runway_length_m: int) -> bool:
        """Checks whether this runway is long enough for the aircraft size."""
        return self.length_m >= min_runway_length_m

    def reserve(self, flight_id: str, duration_seconds: float = 0.0) -> bool:
        """
        Marks runway Occupied for an incoming landing clearance.
        When duration_seconds <= 0, stays locked until the aircraft lands/crashes/holds.
        """
        if not self.is_available():
            return False
        self.status = RunwayStatus.OCCUPIED
        self.status_reason = f"Landing clearance: {flight_id}"
        self.current_aircraft = flight_id
        self.occupancy_timer = max(0.0, float(duration_seconds))
        self.total_operations_handled += 1
        return True

    def occupy(self, flight_id: str, duration_seconds: float = 25.0):
        """Force-marks runway Occupied (used by scenario setup or landing roll)."""
        self.status = RunwayStatus.OCCUPIED
        self.status_reason = f"Active rollout: {flight_id}"
        self.current_aircraft = flight_id
        self.occupancy_timer = duration_seconds
        self.total_operations_handled += 1

    def set_unavailable(self, reason: str = "Weather / Crosswind", duration_seconds: float = 18.0):
        """Marks runway temporarily Unavailable."""
        self.status = RunwayStatus.UNAVAILABLE
        self.status_reason = reason
        self.current_aircraft = None
        self.occupancy_timer = 0.0
        self.closure_timer = duration_seconds

    def set_maintenance(self, reason: str = "Scheduled Inspection", duration_seconds: float = 20.0):
        """Marks runway Under Maintenance."""
        self.status = RunwayStatus.UNDER_MAINTENANCE
        self.status_reason = reason
        self.current_aircraft = None
        self.occupancy_timer = 0.0
        self.closure_timer = duration_seconds

    def release(self):
        """Restores runway to Available state."""
        self.status = RunwayStatus.AVAILABLE
        self.status_reason = ""
        self.current_aircraft = None
        self.occupancy_timer = 0.0
        self.closure_timer = 0.0

    def update(self, dt: float):
        """Advances occupancy and temporary maintenance/unavailability timers."""
        if self.status == RunwayStatus.OCCUPIED and self.occupancy_timer > 0.0:
            self.occupancy_timer -= dt
            if self.occupancy_timer <= 0.0:
                self.release()
        elif self.status in (RunwayStatus.UNAVAILABLE, RunwayStatus.UNDER_MAINTENANCE) and self.closure_timer > 0.0:
            self.closure_timer -= dt
            if self.closure_timer <= 0.0:
                self.release()

    def distance_to_point(self, px: float, py: float) -> float:
        """Shortest distance from screen point (px, py) to runway centerline segment."""
        vx = self.end_x - self.start_x
        vy = self.end_y - self.start_y
        len_sq = vx * vx + vy * vy
        if len_sq == 0:
            return math.hypot(px - self.start_x, py - self.start_y)
        t = max(0.0, min(1.0, ((px - self.start_x) * vx + (py - self.start_y) * vy) / len_sq))
        proj_x = self.start_x + t * vx
        proj_y = self.start_y + t * vy
        return math.hypot(px - proj_x, py - proj_y)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "length_m": self.length_m,
            "heading": self.heading,
            "status": self.status,
            "status_reason": self.status_reason,
            "current_aircraft": self.current_aircraft,
            "occupancy_timer": round(self.occupancy_timer, 1),
            "closure_timer": round(self.closure_timer, 1),
            "operations_count": self.total_operations_handled,
        }
