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


class SkyATCGame:
    """Interactive Pygame application for SkyATC AI V2."""

    def __init__(self, initial_level: Optional[int] = None):
        pygame.init()
        pygame.display.set_caption("SkyATC AI - Intelligent Runway Management (CSE 3202)")

        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True

        # Core modules
        self.db_logger = DatabaseLogger()
        self.airbase = Airbase(level_id=1)
        self.level_mgr = LevelManager(self.airbase)
        self.agent = ATCAgent(self.airbase, self.db_logger)
        self.renderer = DisplayRenderer(self.screen)
        self.sound = SoundManager()
        self.action_panel = ActionPanel()

        # Session & UI state
        self.current_state = GameState.MAIN_MENU
        self.has_active_session = False
        self.is_paused = False
        self.sim_speed = config.SIMULATION_SPEED_NORMAL
        self.selected_level = 1
        self.demo_unlock_all = False

        self.selected_aircraft: Optional[Aircraft] = None
        self.override_mode = False
        self.drag_state: Optional[Dict[str, Any]] = None
        self.modal_state: Optional[Dict[str, Any]] = None

        self._seen_emergency_ids: set = set()
        self._cached_global = self.db_logger.get_global_counters()
        self._cached_prog = self.db_logger.get_level_progression()
        self._cached_stats: Optional[Dict[str, Any]] = None
        self.log_scroll = 0
        self.export_toast = ""

        if initial_level is not None:
            self.start_level(initial_level)
        else:
            self._switch_state(GameState.MAIN_MENU)

    # -------------------------------------------------------------------------
    # State & Button Setup
    # -------------------------------------------------------------------------

