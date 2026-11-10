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

    def compute_runway_utility(
        self,
        ac: Dict[str, Any],
        runway: Dict[str, Any],
        weather: Dict[str, Any],
    ) -> float:
        """Scores compatibility between a specific aircraft and an available runway."""
        base_u = self.compute_base_priority_utility(ac)
        rwy_len = int(runway.get("length_m", 2500))
        min_len = int(ac.get("min_runway_length_m", 2200))

        # Hard size check: reject incompatible short runways strongly
        if rwy_len < min_len:
            return -1000.0

        fit_bonus = 0.0
        is_emerg = ac.get("emergency_type", "NONE") != "NONE" or ac.get("fuel_level", 100.0) <= config.FUEL_CRITICAL_THRESHOLD
        size = ac.get("aircraft_size", "MEDIUM")

        # Reserve longest runways for Heavy/Emergency; put Small/Medium on shorter compatible runways
        if size == "HEAVY" or is_emerg:
            fit_bonus += (rwy_len - 1800) * 0.025
        else:
            # Slight preference for right-sizing shorter compatible runways to keep long runway free
            slack = rwy_len - min_len
            fit_bonus += max(5.0, 25.0 - slack * 0.015)

        # Wind alignment bonus
        wind_spd = float(weather.get("wind_speed_kts", 10.0))
        wind_dir = float(weather.get("wind_direction_deg", 90.0))
        rwy_hdg = float(runway.get("heading", 90.0))
        angle_diff = abs((wind_dir - rwy_hdg + 180.0) % 360.0 - 180.0)
        if wind_spd >= 25.0 and angle_diff > 60.0:
            fit_bonus -= 18.0

        return round(base_u + fit_bonus, 2)

    def generate_deterministic_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a complete, conflict-free landing plan using the Min-Heap Priority Queue
        plus Explainable AI human-readable rationale.
        """
        aircraft_list = state.get("aircraft", [])
        runways = state.get("runways", {})
        weather = state.get("weather", {})

        pending = [ac for ac in aircraft_list if ac.get("status") == "HOLDING"]
        if not pending:
            return {
                "reasoning": "Airspace nominal; no aircraft holding for landing clearance.",
                "assignments": [],
                "source": "LOCAL_UTILITY",
            }

        ordered_pending = self.pop_sorted_priorities(pending)
        available_rwys = [r for r in runways.values() if r.get("status") == RunwayStatus.AVAILABLE]
        busy_reasons = [
            f"{r_id} {r.get('status').lower()}"
            for r_id, r in runways.items()
            if r.get("status") != RunwayStatus.AVAILABLE
        ]

        if not available_rwys:
            top_ac = ordered_pending[0][1]
            reason = f"Holding {top_ac['flight_id']} (Fuel {int(top_ac['fuel_level'])}%); all runways busy/unavailable"
            return {
                "reasoning": reason,
                "assignments": [
                    {
                        "flight_id": ac["flight_id"],
                        "priority": idx,
                        "assigned_runway": None,
                        "action": "HOLD",
                        "rationale": "All runways currently occupied or unavailable; orbiting safely.",
                    }
                    for idx, (_, ac) in enumerate(ordered_pending, start=1)
                ],
                "source": "LOCAL_UTILITY",
            }

        used_runways = set()
        assignments: List[Dict[str, Any]] = []
        top_reason_parts: List[str] = []

        for priority_rank, (u_score, ac) in enumerate(ordered_pending, start=1):
            best_rwy: Optional[Dict[str, Any]] = None
            best_score = -9999.0

            for rwy in available_rwys:
                if rwy["id"] in used_runways:
                    continue
                score = self.compute_runway_utility(ac, rwy, weather)
                if score > best_score:
                    best_score = score
                    best_rwy = rwy

            if best_rwy is not None and best_score > -500.0:
                used_runways.add(best_rwy["id"])
                rationale = self._build_explainable_reason(ac, best_rwy, busy_reasons, u_score)
                if not top_reason_parts:
                    top_reason_parts.append(rationale)
                assignments.append({
                    "flight_id": ac["flight_id"],
                    "priority": priority_rank,
                    "assigned_runway": best_rwy["id"],
                    "action": "AUTHORIZE_LANDING",
                    "rationale": rationale,
                })
            else:
                reason = f"Hold {ac['flight_id']}; no compatible {ac.get('min_runway_length_m', 2200)}m+ runway free"
                if not top_reason_parts:
                    top_reason_parts.append(reason)
                assignments.append({
                    "flight_id": ac["flight_id"],
                    "priority": priority_rank,
                    "assigned_runway": None,
                    "action": "HOLD",
                    "rationale": reason,
                })

        return {
            "reasoning": top_reason_parts[0] if top_reason_parts else "Optimal Min-Heap utility runway plan.",
            "assignments": assignments,
            "source": "LOCAL_UTILITY",
        }

    @staticmethod
    def _build_explainable_reason(
        ac: Dict[str, Any],
        runway: Dict[str, Any],
        busy_reasons: List[str],
        utility_score: float,
    ) -> str:
        """Produces a crisp, human-readable 1-line Explainable AI reason badge."""
        del utility_score
        parts: List[str] = []
        emerg = ac.get("emergency_type", "NONE")
        fuel = int(ac.get("fuel_level", 100))
        wait_s = int(ac.get("waiting_time", 0))
        is_heavy = ac.get("aircraft_size") == "HEAVY"

        if emerg == "CRITICAL_FUEL" or fuel <= config.FUEL_CRITICAL_THRESHOLD:
            parts.append(f"CRITICAL FUEL ({fuel}%) -> {runway['id']}")
        elif emerg != "NONE":
            parts.append(f"{emerg.replace('_', ' ').title()}! Urgent {runway['id']}")
        elif fuel < 45:
            parts.append(f"Lowest fuel ({fuel}%) -> {runway['id']}")
        elif is_heavy:
            parts.append(f"Heavy {ac.get('model', 'jet')} needs {runway['length_m']}m {runway['id']}")
        elif wait_s >= 8:
            parts.append(f"Waiting {wait_s}s -> free {runway['id']}")
        else:
            parts.append(f"Nearest free {runway['id']} ({runway['length_m']}m)")

        if is_heavy and (emerg != "NONE" or fuel < 45):
            parts.append(f"Heavy {runway['length_m']}m fit")
        elif busy_reasons:
            parts.append(busy_reasons[0])

        return "; ".join(parts[:2])
