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

    def log_feedback(
        self,
        decision_id: Optional[int],
        flight_id: str,
        validation_result: str,
        execution_result: str,
        feedback_details: str,
    ):
        self.db.execute(
            """INSERT INTO feedback (decision_id, flight_id, validation_result, execution_result, feedback_details)
               VALUES (%s, %s, %s, %s, %s)""",
            (decision_id, flight_id, validation_result, execution_result, feedback_details),
        )

    def log_event(self, level_id: int, event_type: str, description: str, aircraft_id: str = "", runway_id: str = ""):
        self.db.execute(
            """INSERT INTO simulation_events (level_id, aircraft_id, runway_id, event_type, event_description)
               VALUES (%s, %s, %s, %s, %s)""",
            (level_id, aircraft_id, runway_id, event_type, description),
        )

    def log_level_history(self, level_id: int, status: str, final_score: int, landings: int, emergencies: int):
        self.db.execute(
            """INSERT INTO level_history (level_id, completion_status, final_score, total_landings, total_emergencies)
               VALUES (%s, %s, %s, %s, %s)""",
            (level_id, status, final_score, landings, emergencies),
        )

    def log_reward(self, level_id: int, flight_id: str, event_type: str, reward_points: int):
        self.db.execute(
            """INSERT INTO reward_history (level_id, aircraft_id, event_type, reward_points)
               VALUES (%s, %s, %s, %s)""",
            (level_id, flight_id, event_type, reward_points),
        )

    # -------------------------------------------------------------------------
    # Read / Analytics Queries (For Main Menu, Level Select & AI & DB Stats)
    # -------------------------------------------------------------------------

    def get_global_counters(self) -> Dict[str, int]:
        """Returns global Aircraft Landed & Hi-Score for top HUD."""
        landed_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM aircraft WHERE aircraft_status = 'LANDED'")
        hi_row = self.db.fetchone("SELECT MAX(final_score) as best FROM level_history")
        return {
            "aircraft_landed": int((landed_row or {}).get("cnt") or 0),
            "hi_score": max(0, int((hi_row or {}).get("best") or 0)),
        }

    def get_level_progression(self) -> Dict[str, Any]:
        """Returns unlocked levels and per-level best stats from level_history."""
        rows = self.db.fetchall(
            """SELECT level_id, completion_status, final_score, total_landings, total_emergencies
               FROM level_history ORDER BY level_history_id ASC"""
        )
        completed_levels = set()
        best_by_level: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            lvl = int(row["level_id"])
            score = int(row["final_score"] or 0)
            emerg = int(row["total_emergencies"] or 0)
            if row["completion_status"] == "COMPLETED":
                completed_levels.add(lvl)
            prev = best_by_level.get(lvl)
            if prev is None or score > prev["best_score"]:
                best_by_level[lvl] = {
                    "best_score": score,
                    "emergencies": emerg,
                    "completed": lvl in completed_levels,
                }
            elif lvl in completed_levels:
                prev["completed"] = True

        max_unlocked = 1
        for lvl in range(1, 21):
            if lvl in completed_levels:
                max_unlocked = min(20, max(max_unlocked, lvl + 1))

        return {
            "completed_levels": sorted(completed_levels),
            "max_unlocked": max_unlocked,
            "best_by_level": best_by_level,
        }

    def get_stats_dashboard_data(self) -> Dict[str, Any]:
        """Aggregates all metrics for the AI & DB STATS screen."""
        total_req_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM missions_requests")
        landed_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM aircraft WHERE aircraft_status = 'LANDED'")
        emerg_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM aircraft WHERE emergency_status = 1 AND aircraft_status = 'LANDED'")
        reward_row = self.db.fetchone("SELECT SUM(reward_points) as pts FROM reward_history")

        total_dec_row = self.db.fetchone("SELECT COUNT(*) as cnt, AVG(decision_time_ms) as avg_ms FROM agent_decisions")
        val_rej_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM agent_decisions WHERE validation_status != 'VALID'")
        valid_ai_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM agent_decisions WHERE validation_status = 'VALID'")

        p_accept_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM player_decisions WHERE decision_type = 'ACCEPT_AI'")
        p_override_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM player_decisions WHERE decision_type = 'OVERRIDE'")
        p_timeout_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM player_decisions WHERE decision_type = 'TIMEOUT_AUTO_EXECUTE'")

        total_missions = int((total_req_row or {}).get("cnt") or 0)
        successful_landings = int((landed_row or {}).get("cnt") or 0)
        emergencies_handled = int((emerg_row or {}).get("cnt") or 0)
        accumulated_rewards = int((reward_row or {}).get("pts") or 0)

        total_decisions = int((total_dec_row or {}).get("cnt") or 0)
        avg_ms = float((total_dec_row or {}).get("avg_ms") or 0.0)
        val_rejections = int((val_rej_row or {}).get("cnt") or 0)
        valid_ai = int((valid_ai_row or {}).get("cnt") or 0)

        accepts = int((p_accept_row or {}).get("cnt") or 0)
        overrides = int((p_override_row or {}).get("cnt") or 0)
        timeouts = int((p_timeout_row or {}).get("cnt") or 0)

        landing_rate = round((successful_landings / total_missions) * 100.0, 1) if total_missions else 0.0
        ai_accuracy = round((valid_ai / total_decisions) * 100.0, 1) if total_decisions else 100.0
        player_total = accepts + overrides
        player_accuracy = round((accepts / player_total) * 100.0, 1) if player_total else 100.0
        rej_rate = round((val_rejections / total_decisions) * 100.0, 1) if total_decisions else 0.0

        # Recent detailed database logs (MySQL 8 ONLY_FULL_GROUP_BY & SQLite compatible)
        logs_rows = self.db.fetchall(
            """SELECT ad.decision_id, ad.request_id, ad.flight_id,
                      COALESCE(ac.emergency_type, 'NONE') as emerg_type,
                      ad.assigned_runway_id, ad.validation_status,
                      COALESCE((SELECT pd.decision_type FROM player_decisions pd
                                WHERE pd.decision_id = ad.decision_id
                                ORDER BY pd.player_decision_id DESC LIMIT 1), 'AUTO') as player_action,
                      COALESCE((SELECT SUM(rh.reward_points) FROM reward_history rh
                                WHERE rh.aircraft_id = ad.flight_id), 0) as flight_score
               FROM agent_decisions ad
               LEFT JOIN missions_requests mr ON ad.request_id = mr.request_id
               LEFT JOIN aircraft ac ON mr.aircraft_id = ac.aircraft_id
               ORDER BY ad.decision_id DESC
               LIMIT 40"""
        )

        recent_logs: List[Dict[str, Any]] = []
        for r in logs_rows:
            emerg = r.get("emerg_type", "NONE")
            ev_label = "Emergency Landing" if emerg == "CRITICAL_FUEL" else (emerg.replace("_", " ").title() if emerg != "NONE" else "Normal Landing")
            p_act = r.get("player_action", "AUTO")
            res_label = "Override" if p_act == "OVERRIDE" else ("Auto-Exec" if p_act == "TIMEOUT_AUTO_EXECUTE" else "Success")
            if r.get("validation_status") != "VALID":
                res_label = "Rejected"
            recent_logs.append({
                "req_id": f"{int(r.get('request_id') or r.get('decision_id') or 0):04d}",
                "flight_id": r.get("flight_id", "N/A"),
                "event_type": ev_label[:20],
                "ai_suggestion": r.get("assigned_runway_id") or "HOLD",
                "result": res_label,
                "score": int(r.get("flight_score") or 0),
            })

        prog = self.get_level_progression()
        highest_lvl = max(prog["completed_levels"]) if prog["completed_levels"] else 0

        return {
            "total_missions": total_missions,
            "emergencies_handled": emergencies_handled,
            "successful_landings": successful_landings,
            "landing_rate": landing_rate,
            "accumulated_rewards": accumulated_rewards,
            "ai_accuracy": ai_accuracy,
            "player_accuracy": player_accuracy,
            "avg_ai_decision_sec": round(avg_ms / 1000.0, 2) if avg_ms > 0 else 0.15,
            "avg_ai_decision_ms": round(avg_ms, 1) if avg_ms > 0 else 1.2,
            "validation_rejections": val_rejections,
            "validation_rejection_rate": rej_rate,
            "timeout_auto_executes": timeouts,
            "recent_logs": recent_logs,
            "levels_completed": len(prog["completed_levels"]),
            "highest_completed_level": highest_lvl,
        }

