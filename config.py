"""
=============================================================================
SkyATC AI - Intelligent Runway Management Agent
Central Configuration Module (V2 Specification)
Course: CSE 3202 - Artificial Intelligence Sessional
=============================================================================
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Detect Pygbag WebAssembly (Emscripten) browser runtime
IS_WEB = sys.platform == "emscripten"

# -----------------------------------------------------------------------------
# Base Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
for _runtime_dir in (DATA_DIR, EXPORT_DIR):
    try:
        _runtime_dir.mkdir(exist_ok=True)
    except OSError:
        pass

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

# -----------------------------------------------------------------------------
# Runway Geometry Layouts by Runway Count (2, 3, or 4 Runways)
# Coordinates inside Gameplay Canvas: X=0..975, Y=50..768
# -----------------------------------------------------------------------------
RUNWAY_LAYOUTS: Dict[int, List[Dict[str, Any]]] = {
    2: [
        {
            "id": "RWY 1",
            "name": "Runway 1 (Primary Heavy)",
            "length_m": 3000,
            "start": (235, 315),
            "end": (625, 315),
            "heading": 90,
        },
        {
            "id": "RWY 2",
            "name": "Runway 2 (Secondary)",
            "length_m": 2400,
            "start": (305, 535),
            "end": (585, 365),
            "heading": 59,
        },
    ],
    3: [
        {
            "id": "RWY 1",
            "name": "Runway 1 (Primary Heavy)",
            "length_m": 3200,
            "start": (225, 260),
            "end": (630, 260),
            "heading": 90,
        },
        {
            "id": "RWY 2",
            "name": "Runway 2 (Secondary Heavy)",
            "length_m": 2800,
            "start": (245, 395),
            "end": (605, 360),
            "heading": 84,
        },
        {
            "id": "RWY 3",
            "name": "Runway 3 (Regional Short)",
            "length_m": 1900,
            "start": (300, 545),
            "end": (575, 445),
            "heading": 70,
        },
    ],
    4: [
        {
            "id": "RWY 1",
            "name": "Runway 1 (Heavy North)",
            "length_m": 3400,
            "start": (220, 235),
            "end": (635, 235),
            "heading": 90,
        },
        {
            "id": "RWY 2",
            "name": "Runway 2 (Heavy Central)",
            "length_m": 2800,
            "start": (240, 330),
            "end": (615, 330),
            "heading": 90,
        },
        {
            "id": "RWY 3",
            "name": "Runway 3 (Medium South)",
            "length_m": 2300,
            "start": (260, 445),
            "end": (590, 410),
            "heading": 83,
        },
        {
            "id": "RWY 4",
            "name": "Runway 4 (Light Tactical)",
            "length_m": 1800,
            "start": (300, 555),
            "end": (560, 515),
            "heading": 81,
        },
    ],
}

# -----------------------------------------------------------------------------
# 20-Level Progressive Structure (Report Section 6.2 & 6.4)
# -----------------------------------------------------------------------------
def _build_level_configs() -> Dict[int, Dict[str, Any]]:
    levels: Dict[int, Dict[str, Any]] = {}
    for lvl in range(1, 21):
        if lvl <= 5:
            tier, runways = "EASY", 2
            idx = lvl - 1
            total_ac = 4 + idx
            spawn_int = 10.0 - idx * 0.5
            emerg_ch = 0.15 + idx * 0.04
            heavy_ch = 0.0
            maint_ch = 0.0 if lvl < 3 else 0.10
            wind_kts = 8.0 + idx * 1.5
            fuel_min, fuel_max = 52.0, 92.0
        elif lvl <= 10:
            tier, runways = "MEDIUM", 2
            idx = lvl - 6
            total_ac = 7 + idx
            spawn_int = 8.0 - idx * 0.4
            emerg_ch = 0.28 + idx * 0.04
            heavy_ch = 0.15
            maint_ch = 0.18 + idx * 0.03
            wind_kts = 14.0 + idx * 2.5
            fuel_min, fuel_max = 38.0, 82.0
        elif lvl <= 15:
            tier, runways = "HARD", 3
            idx = lvl - 11
            total_ac = 9 + idx
            spawn_int = 6.8 - idx * 0.3
            emerg_ch = 0.35 + idx * 0.04
            heavy_ch = 0.35 + idx * 0.03
            maint_ch = 0.28 + idx * 0.03
            wind_kts = 20.0 + idx * 3.0
            fuel_min, fuel_max = 30.0, 74.0
        else:
            tier, runways = "EXPERT", 4
            idx = lvl - 16
            total_ac = 12 + idx
            spawn_int = 5.6 - idx * 0.25
            emerg_ch = 0.45 + idx * 0.04
            heavy_ch = 0.40 + idx * 0.02
            maint_ch = 0.35 + idx * 0.04
            wind_kts = 26.0 + idx * 3.5
            fuel_min, fuel_max = 26.0, 70.0

        levels[lvl] = {
            "level_id": lvl,
            "difficulty": tier,
            "runway_count": runways,
            "total_aircraft": total_ac,
            "spawn_interval": round(max(2.8, spawn_int), 2),
            "emergency_chance": round(min(0.65, emerg_ch), 2),
            "heavy_chance": round(min(0.65, heavy_ch), 2),
            "maintenance_chance": round(min(0.55, maint_ch), 2),
            "wind_speed_kts": round(wind_kts, 1),
            "fuel_range": (fuel_min, fuel_max),
            "max_concurrent": min(6 + (lvl // 4), 10),
        }
    return levels


LEVEL_CONFIGS: Dict[int, Dict[str, Any]] = _build_level_configs()

# -----------------------------------------------------------------------------
# Aircraft & Physics Constants
# -----------------------------------------------------------------------------
FUEL_CONSUMPTION_RATE_HOLDING = 0.18   # %/sec while circling in holding pattern
FUEL_CONSUMPTION_RATE_APPROACH = 0.09  # %/sec while on cleared approach
FUEL_CRITICAL_THRESHOLD = 20.0         # Auto-declare CRITICAL_FUEL <= 20%
WAITING_REWARD_THRESHOLD = 12.0        # Bonus eligibility if cleared fast

# -----------------------------------------------------------------------------
# Official Reward & Penalty Matrix (Report Section 13)
# -----------------------------------------------------------------------------
REWARDS: Dict[str, int] = {
    "EMERGENCY_HANDLED": 30,
    "SUCCESSFUL_LANDING": 10,
    "CORRECT_RUNWAY_ASSIGNMENT": 15,
    "RUNWAY_CONFLICT_AVOIDED": 20,
    "EFFICIENT_UTILIZATION": 10,
    "REDUCED_WAITING_TIME": 10,
    "EMERGENCY_DELAYED": -25,
    "WRONG_RUNWAY_ASSIGNMENT": -20,
    "RUNWAY_CONFLICT": -25,
    "INVALID_AI_DECISION": -15,
    "UNSAFE_DECISION": -30,
}

# -----------------------------------------------------------------------------
# Database Configuration (MySQL + SQLite Fallback + Browser Memory on Web)
# -----------------------------------------------------------------------------
DB_TYPE = "memory" if IS_WEB else os.getenv("DB_TYPE", "mysql")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "SKYATC")
SQLITE_DB_PATH = BASE_DIR / os.getenv("SQLITE_PATH", "data/skyatc.db")

# -----------------------------------------------------------------------------
# AI / LLM Configuration (Google Gemini 2.5 Flash via google-genai SDK)
# -----------------------------------------------------------------------------
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_TIMEOUT_SECONDS = 5.0
USE_OFFLINE_FALLBACK = True
