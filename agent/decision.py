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

