"""
=============================================================================
SkyATC AI - Utility-Based Decision Engine & Min-Heap Priority Queue
Implements Report Section 7.1, Section 11 (Min-Heap, Sorting) & Explainable AI.
=============================================================================
"""

import heapq
from typing import Dict, Any, List, Tuple, Optional
import config
from config import RunwayStatus


class DecisionEngine:
    """
    Deterministic Utility-Based reasoning engine powered by a Min-Heap Priority Queue.
    Used both for live priority sorting and as the smart fallback when LLM API is offline.
    """

    def __init__(self):
        self.w_emergency = 140.0
        self.w_fuel = 1.15
        self.w_waiting = 1.4
        self.w_distance = 0.8

    def build_priority_heap(self, pending_aircraft: List[Dict[str, Any]]) -> List[Tuple[float, int, str, Dict[str, Any]]]:
        """
        Constructs a Min-Heap (using negated utility score) for O(log n)
        extraction of the highest-priority landing request.
        """
        heap: List[Tuple[float, int, str, Dict[str, Any]]] = []
        for seq, ac in enumerate(pending_aircraft):
            u_score = self.compute_base_priority_utility(ac)
            tie_seq = int(ac.get("arrival_seq", seq))
            heapq.heappush(heap, (-u_score, tie_seq, ac["flight_id"], ac))
        return heap

    def pop_sorted_priorities(self, pending_aircraft: List[Dict[str, Any]]) -> List[Tuple[float, Dict[str, Any]]]:
        """Extracts all pending aircraft in descending priority order using the Min-Heap."""
        heap = self.build_priority_heap(pending_aircraft)
        ordered: List[Tuple[float, Dict[str, Any]]] = []
        while heap:
            neg_u, _, _, ac = heapq.heappop(heap)
            ordered.append((round(-neg_u, 2), ac))
        return ordered

    def compute_base_priority_utility(self, ac: Dict[str, Any]) -> float:
        """Calculates aircraft urgency independent of specific runway choice."""
        utility = 0.0
        emerg = ac.get("emergency_type", "NONE")
        fuel = float(ac.get("fuel_level", 100.0))

        if emerg == "ENGINE_PROBLEM":
            utility += self.w_emergency * 1.35
        elif emerg == "CRITICAL_FUEL" or fuel <= config.FUEL_CRITICAL_THRESHOLD:
            utility += self.w_emergency * 1.25
        elif emerg in ("BIRD_STRIKE", "MEDICAL"):
            utility += self.w_emergency * 1.05

        utility += max(0.0, 100.0 - fuel) * self.w_fuel
        utility += min(55.0, float(ac.get("waiting_time", 0.0)) * self.w_waiting)
        utility += max(0.0, 22.0 - float(ac.get("distance_nm", 12.0))) * self.w_distance
        return round(utility, 2)

