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

