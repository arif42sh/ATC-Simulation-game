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

    def _init_connection(self):
        """Connects to MySQL first (2s timeout); gracefully falls back to SQLite."""
        if config.DB_TYPE.lower() == "mysql" and PYMYSQL_AVAILABLE:
            try:
                self.connection = pymysql.connect(
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    database=config.DB_NAME,
                    connect_timeout=2,
                    read_timeout=2,
                    write_timeout=2,
                    autocommit=True,
                    cursorclass=pymysql.cursors.DictCursor,
                )
                self.engine_type = "mysql"
                print(f"[DATABASE] MySQL connected: {config.DB_NAME}@{config.DB_HOST}:{config.DB_PORT}")
                return
            except pymysql.err.OperationalError as op_err:
                if op_err.args[0] == 1049:
                    try:
                        tmp = pymysql.connect(
                            host=config.DB_HOST,
                            port=config.DB_PORT,
                            user=config.DB_USER,
                            password=config.DB_PASSWORD,
                            connect_timeout=2,
                            autocommit=True,
                        )
                        with tmp.cursor() as cur:
                            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}`;")
                        tmp.close()
                        self.connection = pymysql.connect(
                            host=config.DB_HOST,
                            port=config.DB_PORT,
                            user=config.DB_USER,
                            password=config.DB_PASSWORD,
                            database=config.DB_NAME,
                            connect_timeout=2,
                            read_timeout=2,
                            write_timeout=2,
                            autocommit=True,
                            cursorclass=pymysql.cursors.DictCursor,
                        )
                        self.engine_type = "mysql"
                        print(f"[DATABASE] Created & connected MySQL database '{config.DB_NAME}'")
                        return
                    except Exception:
                        pass
                print(f"[DATABASE] MySQL unavailable ({op_err}); falling back to SQLite.")
            except Exception as exc:
                print(f"[DATABASE] MySQL unavailable ({exc}); falling back to SQLite.")

        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(config.SQLITE_DB_PATH), check_same_thread=False, timeout=3.0)
        self.connection.row_factory = sqlite3.Row
        self.engine_type = "sqlite"
        print(f"[DATABASE] SQLite connected: {config.SQLITE_DB_PATH}")

