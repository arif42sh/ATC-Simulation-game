"""
=============================================================================
SkyATC AI - Intelligent Runway Management Agent
Central Configuration Module (V2 Specification)
Course: CSE 3202 - Artificial Intelligence Sessional
=============================================================================
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------------------------
# Base Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# Display & Layout Constants
# -----------------------------------------------------------------------------
WINDOW_WIDTH = 1360
WINDOW_HEIGHT = 768
FPS = int(os.getenv("SIMULATION_FPS", "60"))

TOP_BAR_HEIGHT = 50
SIDEBAR_WIDTH = 385
CANVAS_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH  # 975 px gameplay airbase canvas
SIDEBAR_X = CANVAS_WIDTH
CANVAS_HEIGHT = WINDOW_HEIGHT - TOP_BAR_HEIGHT

SIMULATION_SPEED_SLOW = 0.5
SIMULATION_SPEED_NORMAL = 1.0
SIMULATION_SPEED_FAST = 2.0

# 10-Second Human-in-the-Loop (HITL) Decision Window (Report Section 9)
HITL_TIMEOUT_SECONDS = float(os.getenv("HITL_TIMEOUT_SECONDS", "10.0"))

# -----------------------------------------------------------------------------
# Game States (4 Primary Screens)
# -----------------------------------------------------------------------------
class GameState:
    MAIN_MENU = "MAIN_MENU"
    LEVEL_SELECT = "LEVEL_SELECT"
    SIMULATION = "SIMULATION"
    AI_STATS = "AI_STATS"


# -----------------------------------------------------------------------------
# Runway States (Report Section 6.3)
# -----------------------------------------------------------------------------
class RunwayStatus:
    AVAILABLE = "Available"
    OCCUPIED = "Occupied"
    UNAVAILABLE = "Unavailable"
    UNDER_MAINTENANCE = "Under Maintenance"


# -----------------------------------------------------------------------------
# Aircraft Size & Runway Length Requirements (Game Improvement Sec 4)
# -----------------------------------------------------------------------------
class AircraftSize:
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"


AIRCRAFT_SPECS: Dict[str, Dict[str, Any]] = {
    "AT72": {"size": AircraftSize.SMALL, "min_runway_m": 1500, "speed_kts": 125.0},
    "C208": {"size": AircraftSize.SMALL, "min_runway_m": 1400, "speed_kts": 115.0},
    "B737": {"size": AircraftSize.MEDIUM, "min_runway_m": 2200, "speed_kts": 140.0},
    "A320": {"size": AircraftSize.MEDIUM, "min_runway_m": 2200, "speed_kts": 140.0},
    "B777": {"size": AircraftSize.HEAVY, "min_runway_m": 2800, "speed_kts": 155.0},
    "A350": {"size": AircraftSize.HEAVY, "min_runway_m": 2800, "speed_kts": 155.0},
    "C17":  {"size": AircraftSize.HEAVY, "min_runway_m": 2800, "speed_kts": 150.0},
}

# -----------------------------------------------------------------------------
# Visual Color Palette (Matching Airbase UI Mockups)
# -----------------------------------------------------------------------------
COLOR_GRASS_LIGHT = (67, 134, 42)
COLOR_GRASS_DARK = (57, 120, 35)
COLOR_CONTOUR = (43, 94, 26)

COLOR_TARMAC = (164, 150, 126)
COLOR_TARMAC_BORDER = (128, 116, 96)
COLOR_RUNWAY_ASPHALT = (68, 66, 62)
COLOR_RUNWAY_MARKING = (238, 240, 234)
COLOR_HELIPAD_RING = (212, 168, 56)

COLOR_TOPBAR_BG = (34, 62, 24)
COLOR_TOPBAR_BORDER = (58, 98, 44)
COLOR_SIDEBAR_BG = (15, 27, 45)
COLOR_CARD_BG = (24, 41, 66)
COLOR_CARD_DARK = (18, 32, 54)
COLOR_CARD_BORDER = (46, 76, 114)

COLOR_WHITE = (255, 255, 255)
COLOR_TEXT_MUTED = (186, 206, 228)
COLOR_TEXT_DIM = (128, 152, 180)

COLOR_CYAN = (46, 224, 255)
COLOR_PRIMARY_GREEN = (32, 205, 92)
COLOR_CRITICAL_RED = (216, 48, 56)
COLOR_WARN_AMBER = (216, 134, 28)
COLOR_NORMAL_SLATE = (78, 106, 136)
COLOR_PURPLE = (180, 125, 255)

