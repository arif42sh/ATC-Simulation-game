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

