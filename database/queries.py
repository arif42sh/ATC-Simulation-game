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

    def update_aircraft_outcome(self, ac_id: Optional[int], req_id: Optional[int], fuel: float, status: str, wait_sec: float):
        if ac_id:
            self.db.execute(
                "UPDATE aircraft SET current_fuel = %s, aircraft_status = %s WHERE aircraft_id = %s",
                (round(fuel, 1), status, ac_id),
            )
        if req_id:
            req_status = "COMPLETED" if status == "LANDED" else ("FAILED" if status == "CRASHED" else "ACTIVE")
            self.db.execute(
                "UPDATE missions_requests SET waiting_time = %s, request_status = %s WHERE request_id = %s",
                (round(wait_sec, 1), req_status, req_id),
            )

    def log_agent_decision(
        self,
        request_id: Optional[int],
        flight_id: str,
        priority: int,
        assigned_runway: Optional[str],
        ai_reason: str,
        decision_source: str,
        validation_status: str,
        decision_time_ms: float,
    ) -> int:
        return self.db.execute(
            """INSERT INTO agent_decisions
               (request_id, flight_id, recommended_priority, assigned_runway_id, ai_reason, decision_source, validation_status, decision_time_ms)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (request_id, flight_id, priority, assigned_runway, ai_reason, decision_source, validation_status, round(decision_time_ms, 2)),
        )

    def update_agent_decision(
        self,
        decision_id: int,
        priority: int,
        assigned_runway: Optional[str],
        ai_reason: str,
        decision_source: str,
        validation_status: str,
        decision_time_ms: float,
    ):
        self.db.execute(
            """UPDATE agent_decisions
               SET recommended_priority = %s, assigned_runway_id = %s, ai_reason = %s,
                   decision_source = %s, validation_status = %s, decision_time_ms = %s
               WHERE decision_id = %s""",
            (priority, assigned_runway, ai_reason, decision_source, validation_status, round(decision_time_ms, 2), decision_id),
        )

    def log_player_decision(
        self,
        decision_id: Optional[int],
        aircraft_id: Optional[int],
        flight_id: str,
        selected_runway: Optional[str],
        decision_type: str,  # 'ACCEPT_AI', 'OVERRIDE', 'TIMEOUT_AUTO_EXECUTE'
    ):
        self.db.execute(
            """INSERT INTO player_decisions
               (decision_id, selected_aircraft_id, flight_id, selected_runway_id, decision_type)
               VALUES (%s, %s, %s, %s, %s)""",
            (decision_id, aircraft_id, flight_id, selected_runway, decision_type),
        )

