"""
=============================================================================
SkyATC AI - Database Connector & V2 9-Table Schema Manager (Module 8)
Supports MySQL (Primary) with automatic SQLite fallback and V2 migration.
=============================================================================
"""

from typing import Optional, List
import config

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    sqlite3 = None
    SQLITE_AVAILABLE = False

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


class DatabaseManager:
    """
    Unified MySQL/SQLite/Web-Memory persistence engine implementing the 9 tables
    specified in Update_report_V2 Section 12.2-12.3.
    """

    SCHEMA_VERSION = "v2_report"

    def __init__(self):
        self.engine_type = "sqlite"
        self.connection = None
        self._init_connection()
        self._create_schema()

    def _init_connection(self):
        """Connects to MySQL first (2s timeout); falls back to SQLite or Web memory."""
        if config.IS_WEB or config.DB_TYPE.lower() == "memory":
            self.connection = None
            self.engine_type = "memory"
            print("[DATABASE] Browser memory/localStorage engine active.")
            return

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

        if SQLITE_AVAILABLE and sqlite3 is not None:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(config.SQLITE_DB_PATH), check_same_thread=False, timeout=3.0)
            self.connection.row_factory = sqlite3.Row
            self.engine_type = "sqlite"
            print(f"[DATABASE] SQLite connected: {config.SQLITE_DB_PATH}")
        else:
            self.connection = None
            self.engine_type = "memory"
            print("[DATABASE] SQLite unavailable; using in-memory storage fallback.")

    def _is_v2_schema_active(self, cursor) -> bool:
        """Checks if existing database already carries the V2 9-table schema."""
        try:
            cursor.execute("SELECT version FROM schema_meta LIMIT 1")
            row = cursor.fetchone()
            if row:
                ver = row["version"] if isinstance(row, dict) else row[0]
                return ver == self.SCHEMA_VERSION
        except Exception:
            return False
        return False

    def _create_schema(self):
        """Creates all 9 tables for V2, cleanly migrating any legacy V1 tables."""
        if self.engine_type == "memory" or not self.connection:
            return
        auto_inc = "AUTO_INCREMENT" if self.engine_type == "mysql" else "AUTOINCREMENT"
        ts_default = "CURRENT_TIMESTAMP"

        try:
            cursor = self.connection.cursor()
            if not self._is_v2_schema_active(cursor):
                legacy_drops: List[str] = [
                    "DROP TABLE IF EXISTS reward_history",
                    "DROP TABLE IF EXISTS level_history",
                    "DROP TABLE IF EXISTS simulation_events",
                    "DROP TABLE IF EXISTS feedback",
                    "DROP TABLE IF EXISTS player_decisions",
                    "DROP TABLE IF EXISTS agent_decisions",
                    "DROP TABLE IF EXISTS missions_requests",
                    "DROP TABLE IF EXISTS runways",
                    "DROP TABLE IF EXISTS aircraft",
                    "DROP TABLE IF EXISTS schema_meta",
                ]
                for stmt in legacy_drops:
                    cursor.execute(stmt)

            table_queries = [
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    version VARCHAR(32) PRIMARY KEY
                );
                """,
                # 1. Aircraft
                f"""
                CREATE TABLE IF NOT EXISTS aircraft (
                    aircraft_id INTEGER PRIMARY KEY {auto_inc},
                    flight_id VARCHAR(32) NOT NULL,
                    model VARCHAR(32) DEFAULT 'B737',
                    aircraft_size VARCHAR(16) DEFAULT 'MEDIUM',
                    initial_fuel FLOAT NOT NULL,
                    current_fuel FLOAT NOT NULL,
                    emergency_status INTEGER DEFAULT 0,
                    emergency_type VARCHAR(64) DEFAULT 'NONE',
                    current_distance FLOAT DEFAULT 0.0,
                    aircraft_status VARCHAR(32) DEFAULT 'HOLDING',
                    created_at TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 2. Runways
                f"""
                CREATE TABLE IF NOT EXISTS runways (
                    runway_id VARCHAR(16) PRIMARY KEY,
                    runway_name VARCHAR(64) NOT NULL,
                    level_id INTEGER DEFAULT 1,
                    length_m INTEGER NOT NULL,
                    runway_status VARCHAR(32) DEFAULT 'Available',
                    current_aircraft_id VARCHAR(32) DEFAULT NULL,
                    updated_at TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 3. Missions/Requests
                f"""
                CREATE TABLE IF NOT EXISTS missions_requests (
                    request_id INTEGER PRIMARY KEY {auto_inc},
                    aircraft_id INTEGER,
                    flight_id VARCHAR(32) NOT NULL,
                    request_type VARCHAR(32) DEFAULT 'LANDING',
                    request_time TIMESTAMP DEFAULT {ts_default},
                    waiting_time FLOAT DEFAULT 0.0,
                    current_priority FLOAT DEFAULT 0.0,
                    request_status VARCHAR(32) DEFAULT 'PENDING'
                );
                """,
                # 4. Agent Decisions
                f"""
                CREATE TABLE IF NOT EXISTS agent_decisions (
                    decision_id INTEGER PRIMARY KEY {auto_inc},
                    request_id INTEGER,
                    flight_id VARCHAR(32) NOT NULL,
                    recommended_priority INTEGER DEFAULT 1,
                    assigned_runway_id VARCHAR(16),
                    ai_reason TEXT,
                    decision_source VARCHAR(32) DEFAULT 'LOCAL_UTILITY',
                    validation_status VARCHAR(32) DEFAULT 'VALID',
                    decision_time_ms FLOAT DEFAULT 0.0,
                    decision_timestamp TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 5. Player Decisions
                f"""
                CREATE TABLE IF NOT EXISTS player_decisions (
                    player_decision_id INTEGER PRIMARY KEY {auto_inc},
                    decision_id INTEGER,
                    selected_aircraft_id INTEGER,
                    flight_id VARCHAR(32) NOT NULL,
                    selected_runway_id VARCHAR(16),
                    decision_type VARCHAR(32) NOT NULL,
                    decision_timestamp TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 6. Feedback
                f"""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id INTEGER PRIMARY KEY {auto_inc},
                    decision_id INTEGER,
                    flight_id VARCHAR(32),
                    validation_result VARCHAR(32) NOT NULL,
                    execution_result VARCHAR(32) NOT NULL,
                    feedback_details TEXT,
                    recorded_at TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 7. Simulation Events
                f"""
                CREATE TABLE IF NOT EXISTS simulation_events (
                    event_id INTEGER PRIMARY KEY {auto_inc},
                    level_id INTEGER DEFAULT 1,
                    aircraft_id VARCHAR(32),
                    runway_id VARCHAR(16),
                    event_type VARCHAR(64) NOT NULL,
                    event_description TEXT,
                    event_timestamp TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 8. Level History
                f"""
                CREATE TABLE IF NOT EXISTS level_history (
                    level_history_id INTEGER PRIMARY KEY {auto_inc},
                    level_id INTEGER NOT NULL,
                    completion_status VARCHAR(32) NOT NULL,
                    final_score INTEGER DEFAULT 0,
                    total_landings INTEGER DEFAULT 0,
                    total_emergencies INTEGER DEFAULT 0,
                    completed_at TIMESTAMP DEFAULT {ts_default}
                );
                """,
                # 9. Reward History
                f"""
                CREATE TABLE IF NOT EXISTS reward_history (
                    reward_id INTEGER PRIMARY KEY {auto_inc},
                    level_id INTEGER DEFAULT 1,
                    aircraft_id VARCHAR(32),
                    event_type VARCHAR(64) NOT NULL,
                    reward_points INTEGER NOT NULL,
                    event_timestamp TIMESTAMP DEFAULT {ts_default}
                );
                """,
            ]

            for q in table_queries:
                cursor.execute(q)

            if self.engine_type == "mysql":
                cursor.execute("INSERT IGNORE INTO schema_meta (version) VALUES (%s)", (self.SCHEMA_VERSION,))
            else:
                cursor.execute("INSERT OR IGNORE INTO schema_meta (version) VALUES (?)", (self.SCHEMA_VERSION,))
                self.connection.commit()
            cursor.close()
        except Exception as err:
            print(f"[DATABASE ERROR] Schema init failed: {err}")

    def is_mysql(self) -> bool:
        return self.engine_type == "mysql"

    def is_memory(self) -> bool:
        return self.engine_type == "memory"

    def execute(self, query: str, params: tuple = ()) -> int:
        if not self.connection:
            return 0
        fmt = query.replace("%s", "?") if self.engine_type == "sqlite" else query.replace("?", "%s")
        try:
            cursor = self.connection.cursor()
            cursor.execute(fmt, params)
            if self.engine_type == "sqlite":
                self.connection.commit()
            last_id = int(getattr(cursor, "lastrowid", 0) or 0)
            cursor.close()
            return last_id
        except Exception as exc:
            print(f"[DATABASE ERROR] execute failed: {exc}")
            return 0

    def fetchall(self, query: str, params: tuple = ()) -> list:
        if not self.connection:
            return []
        fmt = query.replace("%s", "?") if self.engine_type == "sqlite" else query.replace("?", "%s")
        try:
            cursor = self.connection.cursor()
            cursor.execute(fmt, params)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        except Exception as exc:
            print(f"[DATABASE ERROR] fetchall failed: {exc}")
            return []

    def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        if not self.connection:
            return None
        fmt = query.replace("%s", "?") if self.engine_type == "sqlite" else query.replace("?", "%s")
        try:
            cursor = self.connection.cursor()
            cursor.execute(fmt, params)
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row is not None else None
        except Exception as exc:
            print(f"[DATABASE ERROR] fetchone failed: {exc}")
            return None

    def close(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass


_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
