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

