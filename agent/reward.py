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
        self.player_cumulative_reward: int = 0
        self.ai_cumulative_reward: int = 0
        self.system_cumulative_reward: int = 0
        self.ai_rescue_count: int = 0
        self.level_id: int = 1
        self.history: List[Dict[str, Any]] = []

    def reset(self, level_id: int = 1):
        self.level_id = level_id
        self.cumulative_reward = 0
        self.player_cumulative_reward = 0
        self.ai_cumulative_reward = 0
        self.system_cumulative_reward = 0
        self.ai_rescue_count = 0
        self.history.clear()

    def evaluate_action(
        self,
        event_key: str,
        flight_id: Optional[str] = None,
        note: str = "",
        actor: str = "PLAYER",
        points_override: Optional[int] = None,
    ) -> int:
        pts = int(points_override if points_override is not None else config.REWARDS.get(event_key, 0))
        self.cumulative_reward += pts
        actor = actor.upper() if actor else "SYSTEM"
        if actor == "PLAYER":
            self.player_cumulative_reward = getattr(self, "player_cumulative_reward", 0) + pts
        elif actor == "AI":
            self.ai_cumulative_reward += pts
        else:
            actor = "SYSTEM"
            self.system_cumulative_reward += pts

        self.history.append({
            "event_key": event_key,
            "flight_id": flight_id or "SYSTEM",
            "points": pts,
            "actor": actor,
            "cumulative": self.cumulative_reward,
            "note": note,
        })

        if self.db_logger:
            self.db_logger.log_reward(
                level_id=self.level_id,
                flight_id=flight_id or "SYSTEM",
                event_type=event_key,
                reward_points=pts,
                actor=actor,
            )

        return pts

    def get_breakdown(self) -> Dict[str, Any]:
        """Summarizes reward/penalty totals by event type for Level Summary / Crash Modal."""
        by_event: Dict[str, Dict[str, int]] = {}
        ai_by_event: Dict[str, Dict[str, int]] = {}
        for item in self.history:
            target = ai_by_event if item.get("actor") == "AI" else by_event
            if item.get("actor") == "SYSTEM":
                continue
            key = item["event_key"]
            if key not in target:
                target[key] = {"count": 0, "points": 0}
            target[key]["count"] += 1
            target[key]["points"] += item["points"]

        return {
            "total_score": self.cumulative_reward,
            "player_score": self.cumulative_reward,
            "ai_score": self.ai_cumulative_reward,
            "ai_rescues": self.ai_rescue_count,
            "total_events": len(self.history),
            "by_event": by_event,
            "ai_by_event": ai_by_event,
        }
