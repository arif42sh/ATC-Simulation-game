"""
=============================================================================
SkyATC AI - An Intelligent Runway Management Agent (V2)
Course: CSE 3202 - Artificial Intelligence Sessional
Team Members: Md. Arif Shahriar, Ashikur Rahman
Main Application Entry Point
=============================================================================
"""

import argparse
from typing import Optional
from environment.airbase import Airbase
from environment.events import EventManager
from agent.agent import ATCAgent
from database.queries import DatabaseLogger


def run_gui_simulation(initial_level: Optional[int] = None):
    """Launches the interactive Pygame SkyATC AI V2 application."""
    import traceback
    try:
        from gui.game import SkyATCGame
        print("=" * 70)
        print(" SkyATC AI V2 - Intelligent Runway Management (CSE 3202)")
        print(" Controls: Drag Plane->Runway or [1]-[4] Override | [Space] Accept AI | [P] Pause")
        print("=" * 70)
        game = SkyATCGame(initial_level=initial_level)
        game.run()
    except Exception:
        print("\n[CRITICAL ERROR] Simulation stopped with exception:")
        traceback.print_exc()


