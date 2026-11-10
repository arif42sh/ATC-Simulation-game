"""
=============================================================================
SkyATC AI - Database Queries, Analytics & CSV Report Exporter (Module 8)
=============================================================================
"""

import csv
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import config
from .db import get_db


class DatabaseLogger:
    """High-level repository for all 9 V2 operational tables + CSV export."""

    def __init__(self):
        self.db = get_db()

    def is_mysql_connected(self) -> bool:
        return self.db.is_mysql()

    # -------------------------------------------------------------------------
    # Write Operations (9 Tables)
    # -------------------------------------------------------------------------

    def sync_runways(self, level_id: int, runways: Dict[str, Any]):
        """Persists runway definitions and current status for the active level."""
        for r_id, rwy in runways.items():
            existing = self.db.fetchone("SELECT runway_id FROM runways WHERE runway_id = %s", (r_id,))
            if existing:
                self.db.execute(
                    """UPDATE runways SET runway_name = %s, level_id = %s, length_m = %s,
                       runway_status = %s, current_aircraft_id = %s, updated_at = CURRENT_TIMESTAMP
                       WHERE runway_id = %s""",
                    (rwy.name, level_id, rwy.length_m, rwy.status, rwy.current_aircraft, r_id),
                )
            else:
                self.db.execute(
                    """INSERT INTO runways (runway_id, runway_name, level_id, length_m, runway_status, current_aircraft_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (r_id, rwy.name, level_id, rwy.length_m, rwy.status, rwy.current_aircraft),
                )

    def log_aircraft_and_request(self, ac_dict: Dict[str, Any]) -> tuple[int, int]:
        """Inserts into aircraft & missions_requests; returns (aircraft_id, request_id)."""
        emerg_flag = 1 if ac_dict.get("emergency_type", "NONE") != "NONE" else 0
        ac_id = self.db.execute(
            """INSERT INTO aircraft
               (flight_id, model, aircraft_size, initial_fuel, current_fuel, emergency_status, emergency_type, current_distance, aircraft_status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                ac_dict["flight_id"],
                ac_dict.get("model", "B737"),
                ac_dict.get("aircraft_size", "MEDIUM"),
                ac_dict.get("fuel_level", 75.0),
                ac_dict.get("fuel_level", 75.0),
                emerg_flag,
                ac_dict.get("emergency_type", "NONE"),
                ac_dict.get("distance_nm", 10.0),
                ac_dict.get("status", "HOLDING"),
            ),
        )
        req_id = self.db.execute(
            """INSERT INTO missions_requests
               (aircraft_id, flight_id, request_type, waiting_time, current_priority, request_status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                ac_id,
                ac_dict["flight_id"],
                "LANDING",
                ac_dict.get("waiting_time", 0.0),
                ac_dict.get("priority_score", 0.0),
                "PENDING",
            ),
        )
        return ac_id, req_id

