"""
=============================================================================
SkyATC AI - Database Connector & V2 9-Table Schema Manager (Module 8)
Supports MySQL (Primary) with automatic SQLite fallback and V2 migration.
=============================================================================
"""

import sqlite3
from typing import Optional, List
import config

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


class DatabaseManager:
    """
    Unified MySQL/SQLite persistence engine implementing the 9 tables specified
    in Update_report_V2 Section 12.2-12.3.
    """

    SCHEMA_VERSION = "v2_report"

    def __init__(self):
        self.engine_type = "sqlite"
        self.connection = None
        self._init_connection()
        self._create_schema()

