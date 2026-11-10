# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///
"""
=============================================================================
SkyATC AI - An Intelligent Runway Management Agent (V2)
Course: CSE 3202 - Artificial Intelligence Sessional
Team Members: Md. Arif Shahriar, Ashikur Rahman
Main Application Entry Point (Desktop + Browser WebAssembly via Pygbag)
=============================================================================
"""

import argparse
import asyncio
from typing import Optional
import config
from environment.airbase import Airbase
from environment.events import EventManager
from agent.agent import ATCAgent
from database.queries import DatabaseLogger


async def run_gui_simulation(initial_level: Optional[int] = None):
    """Launches the interactive Pygame SkyATC AI V2 application."""
    import traceback
    try:
        import pygame
        from gui.game import SkyATCGame

        pygame.init()
        print("=" * 70)
        print(" SkyATC AI V2 - Intelligent Runway Management (CSE 3202)")
        print(" Controls: Drag Plane->Runway or [1]-[4] Override | [Space] Accept AI | [P] Pause")
        print("=" * 70)
        game = SkyATCGame(initial_level=initial_level)
        await game.run_async()
    except Exception:
        print("\n[CRITICAL ERROR] Simulation stopped with exception:")
        traceback.print_exc()


def run_headless_evaluation():
    """Runs automated headless evaluation across all V2 scenarios."""
    print("=" * 70)
    print(" SkyATC AI V2 - Headless Automated Evaluation Benchmark")
    print("=" * 70)

    db_logger = DatabaseLogger()
    airbase = Airbase(level_id=1)
    event_mgr = EventManager(airbase)
    agent = ATCAgent(airbase, db_logger)

    scenarios = [
        "normal_landing",
        "simultaneous_requests",
        "critical_fuel_emergency",
        "engine_problem_emergency",
        "one_runway_occupied",
        "runway_maintenance_storm",
        "heavy_aircraft_runway_length",
        "expert_4_runways",
    ]

    total_score = 0
    print(f"{'Scenario':<48} | {'Runways':<7} | {'Score':<9} | {'Status'}")
    print("-" * 80)

    for key in scenarios:
        event_mgr.load_scenario(key)
        agent.reset_for_level(airbase.level_id)

        for _ in range(65):
            for ac in airbase.aircraft_fleet:
                if ac.hitl_pending:
                    ac.hitl_decision_timer = 0.0
            airbase.update(1.0)
            agent.step(1.0)

        lvl_score = agent.reward_system.cumulative_reward
        total_score += lvl_score
        status = "CRASH" if airbase.crashed_aircraft else "PASS"
        print(f"{event_mgr.active_scenario_name:<48} | {len(airbase.runways):<7} | {lvl_score:+6d}pts | {status}")

    print("=" * 80)
    print(f" TOTAL BENCHMARK SCORE: {total_score:+d} PTS")
    print(f" DB ENGINE: {'MySQL' if db_logger.is_mysql_connected() else 'SQLite Fallback'}")
    print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(description="SkyATC AI V2 - Intelligent Runway Management Agent")
    parser.add_argument("--headless", action="store_true", help="Run automated headless evaluation benchmark")
    parser.add_argument("--level", type=int, default=None, help="Start directly at level 1-20")
    args, _ = parser.parse_known_args()

    if args.headless and not config.IS_WEB:
        run_headless_evaluation()
    else:
        await run_gui_simulation(initial_level=args.level)


if __name__ == "__main__":
    asyncio.run(main())
