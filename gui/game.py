"""
=============================================================================
SkyATC AI - Main Simulation Controller & State Machine (Modules 1 & 6)
Coordinates Main Menu, 20-Level Select, Gameplay Loop, Drag-and-Draw Override,
Pause/0.5x-1x-2x Speed, Modals, Audio SFX, and AI & DB Stats Screen.
=============================================================================
"""

import sys
import math
from typing import Optional, List, Dict, Any
import pygame
import config
from config import GameState
from environment.airbase import Airbase
from environment.aircraft import Aircraft, FlightStatus
from environment.levels import LevelManager
from database.queries import DatabaseLogger
from agent.agent import ATCAgent
from .audio import SoundManager
from .buttons import Button, ActionPanel
from .display import DisplayRenderer


