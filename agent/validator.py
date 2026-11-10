"""
=============================================================================
SkyATC AI - AI Plan Validation Module (Module 5)
Enforces all 9 safety & operational rules from Update_report_V2 Section 8.2.
=============================================================================
"""

from typing import Dict, Any, List, Tuple
import config
from config import RunwayStatus


class PlanValidator:
    """
    Independent Python safety & consistency layer between the AI/Player
    and the simulation environment.
    """

    def validate_plan(
        self,
        plan: Dict[str, Any],
        airbase_state: Dict[str, Any],
    ) -> Tuple[bool, List[str], List[Dict[str, Any]], str]:
        """
        Validates every assignment in an operational plan against the 9 rules.
        Returns:
            (is_valid, issues, valid_actions, validation_code)
        """
        issues: List[str] = []
        valid_actions: List[Dict[str, Any]] = []
        validation_code = "VALID"

        if not isinstance(plan, dict) or "assignments" not in plan:
            return False, ["MISSING_DATA: Plan missing required 'assignments' field."], [], "MISSING_DATA"

        assignments = plan.get("assignments")
        if not isinstance(assignments, list):
            return False, ["MISSING_DATA: 'assignments' must be a list."], [], "MISSING_DATA"

        if not assignments:
            return True, [], [], "VALID"

        runways_state = airbase_state.get("runways", {})
        aircraft_map = {ac["flight_id"]: ac for ac in airbase_state.get("aircraft", [])}

        # Emergency aircraft waiting for clearance (Rule 8 check)
        pending_emergencies = {
            ac["flight_id"]
            for ac in airbase_state.get("aircraft", [])
            if ac.get("status") == "HOLDING"
            and (ac.get("emergency_type", "NONE") != "NONE" or ac.get("fuel_level", 100.0) <= config.FUEL_CRITICAL_THRESHOLD)
        }

        assigned_runways_in_plan = set()
        seen_aircraft = set()

        for item in assignments:
            # Rule 7: Required fields check
            if not isinstance(item, dict) or "flight_id" not in item or "action" not in item:
                issues.append("MISSING_DATA: Assignment missing required flight_id or action.")
                validation_code = "MISSING_DATA"
                continue

            flight_id = item.get("flight_id")
            action = item.get("action")
            runway_id = item.get("assigned_runway")

            # Rule 5: Duplicate aircraft check
            if flight_id in seen_aircraft:
                issues.append(f"DUPLICATE_ASSIGNMENT: Aircraft {flight_id} assigned multiple times.")
                validation_code = "DUPLICATE_ASSIGNMENT"
                continue
            seen_aircraft.add(flight_id)

            # Rule 6: Aircraft exists and is eligible for landing clearance
            ac_info = aircraft_map.get(flight_id)
            if not ac_info:
                issues.append(f"INELIGIBLE_AIRCRAFT: Flight '{flight_id}' not found in active airspace.")
                if validation_code == "VALID":
                    validation_code = "INELIGIBLE_AIRCRAFT"
                continue

            if action == "HOLD":
                valid_actions.append(item)
                continue

            if ac_info.get("status") != "HOLDING":
                issues.append(f"INELIGIBLE_AIRCRAFT: {flight_id} is already {ac_info.get('status')}.")
                if validation_code == "VALID":
                    validation_code = "INELIGIBLE_AIRCRAFT"
                continue

            if not runway_id:
                issues.append(f"MISSING_DATA: Landing assignment for {flight_id} lacks assigned_runway.")
                validation_code = "MISSING_DATA"
                continue

            # Rule 1: Runway exists
            r_info = runways_state.get(runway_id)
            if not r_info:
                issues.append(f"INVALID_RUNWAY: Runway '{runway_id}' does not exist in this level.")
                validation_code = "INVALID_RUNWAY"
                continue

            # Rule 3: Runway not already occupied
            if r_info.get("status") == RunwayStatus.OCCUPIED:
                issues.append(f"RUNWAY_CONFLICT: {runway_id} is occupied by {r_info.get('current_aircraft')}.")
                validation_code = "RUNWAY_CONFLICT"
                continue

            # Rule 2: Runway currently available (reject Unavailable / Under Maintenance)
            if r_info.get("status") != RunwayStatus.AVAILABLE:
                issues.append(f"INVALID_RUNWAY: {runway_id} is {r_info.get('status')}.")
                validation_code = "INVALID_RUNWAY"
                continue

            # Rule 4: Conflicting landing operations on same runway in same plan
            if runway_id in assigned_runways_in_plan:
                issues.append(f"RUNWAY_CONFLICT: Multiple aircraft assigned to {runway_id}.")
                validation_code = "RUNWAY_CONFLICT"
                continue

            # Rule 9: Operational constraint (Aircraft Size vs Runway Length)
            min_len = int(ac_info.get("min_runway_length_m", 2200))
            rwy_len = int(r_info.get("length_m", 2500))
            if rwy_len < min_len:
                issues.append(
                    f"CONSTRAINT_VIOLATION: {flight_id} ({ac_info.get('model')}) requires >= {min_len}m; "
                    f"{runway_id} is only {rwy_len}m."
                )
                validation_code = "CONSTRAINT_VIOLATION"
                continue

            # Rule 8: Emergency priority consistency (preserve compatible runways for waiting emergencies)
            if pending_emergencies and flight_id not in pending_emergencies:
                rem_avail = [
                    r for r_id, r in runways_state.items()
                    if r.get("status") == RunwayStatus.AVAILABLE
                    and r_id != runway_id
                    and r_id not in assigned_runways_in_plan
                ]
                compat_unassigned = [
                    eid for eid in pending_emergencies
                    if eid not in seen_aircraft
                    and rwy_len >= int(aircraft_map[eid].get("min_runway_length_m", 2200))
                ]
                if compat_unassigned:
                    rem_compat_slots = sum(
                        1 for r in rem_avail
                        if any(
                            int(r.get("length_m", 2500)) >= int(aircraft_map[eid].get("min_runway_length_m", 2200))
                            for eid in compat_unassigned
                        )
                    )
                    if rem_compat_slots < len(compat_unassigned):
                        issues.append(
                            f"PRIORITY_VIOLATION: Emergency flight {compat_unassigned[0]} prioritized behind {flight_id}."
                        )
                        validation_code = "PRIORITY_VIOLATION"
                        continue

            assigned_runways_in_plan.add(runway_id)
            valid_actions.append(item)

        is_valid = len(issues) == 0
        return is_valid, issues, valid_actions, validation_code
