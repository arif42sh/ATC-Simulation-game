"""
=============================================================================
SkyATC AI - Reward and Scoring System (Module 7)
Implements exact Report Section 13 reward/penalty matrix and breakdown.
=============================================================================
"""

from typing import Dict, Any, List, Optional
import config
from database.queries import DatabaseLogger


class RewardSystem:
    """Calculates rewards, penalties, and level summary breakdowns."""

    def __init__(self, db_logger: Optional[DatabaseLogger] = None):
        self.db_logger = db_logger
        self.cumulative_reward: int = 0
        self.level_id: int = 1
        self.history: List[Dict[str, Any]] = []

    def reset(self, level_id: int = 1):
        self.level_id = level_id
        self.cumulative_reward = 0
        self.history.clear()

    def evaluate_action(
        self,
        event_key: str,
        flight_id: Optional[str] = None,
        note: str = "",
    ) -> int:
        pts = config.REWARDS.get(event_key, 0)
        self.cumulative_reward += pts

        self.history.append({
            "event_key": event_key,
            "flight_id": flight_id or "SYSTEM",
            "points": pts,
            "cumulative": self.cumulative_reward,
            "note": note,
        })

        if self.db_logger:
            self.db_logger.log_reward(
                level_id=self.level_id,
                flight_id=flight_id or "SYSTEM",
                event_type=event_key,
                reward_points=pts,
            )

        return pts

    def get_breakdown(self) -> Dict[str, Any]:
        """Summarizes reward/penalty totals by event type for Level Summary / Crash Modal."""
        by_event: Dict[str, Dict[str, int]] = {}
        for item in self.history:
            key = item["event_key"]
            if key not in by_event:
                by_event[key] = {"count": 0, "points": 0}
            by_event[key]["count"] += 1
            by_event[key]["points"] += item["points"]

        return {
            "total_score": self.cumulative_reward,
            "total_events": len(self.history),
            "by_event": by_event,
        }
