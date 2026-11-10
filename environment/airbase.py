"""
=============================================================================
SkyATC AI - Airbase Environment Manager (Module 3 + Data Structures)
Manages 2-4 dynamic runways, O(1) Flight ID Hash Map, FIFO queue, and collisions.
=============================================================================
"""

import random
from collections import deque
from typing import Dict, List, Optional, Any, Deque, Tuple
import config
from config import RunwayStatus
from .runway import Runway
from .aircraft import Aircraft, FlightStatus


class WeatherCondition:
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    FOG = "FOG"
    CROSSWIND = "CROSSWIND"
    STORM = "STORM"


class Airbase:
    """
    2D Airbase Simulation Environment supporting 2 to 4 runways depending on level,
    Hash Map O(1) aircraft lookup, FIFO arrival queue, and safety crash detection.
    """

