"""
=============================================================================
SkyATC AI - Aircraft Management & Kinematics (Module 2)
Landing-focused aircraft physics, holding orbits, fuel burn & priority metrics.
=============================================================================
"""

import math
from typing import Dict, Any, Optional, Tuple, List
import config


class EmergencyType:
    NONE = "NONE"
    CRITICAL_FUEL = "CRITICAL_FUEL"
    ENGINE_PROBLEM = "ENGINE_PROBLEM"
    BIRD_STRIKE = "BIRD_STRIKE"
    MEDICAL = "MEDICAL"


class FlightStatus:
    HOLDING = "HOLDING"            # Orbiting in perimeter holding pattern
    INTERCEPT = "INTERCEPT"        # Turning to intercept assigned runway approach fix
    APPROACHING = "APPROACHING"    # Final approach glideslope toward runway threshold
    ROLLING_LAND = "ROLLING_LAND"  # Touchdown & deceleration along runway centerline
    LANDED = "LANDED"              # Safely landed and vacated runway
    CRASHED = "CRASHED"            # Fuel exhausted or runway collision


