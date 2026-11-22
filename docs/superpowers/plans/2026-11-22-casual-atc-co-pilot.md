# Casual ATC Commander + AI Co-Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform SkyATC AI into a tactile, addictive, and satisfying casual air traffic control game with 1-click Spacebar clearance, glowing AI Co-Pilot guidance, minimal visual clutter, combo streaks, and 3-star level ratings while preserving the core Min-Heap and safety algorithms.

**Architecture:** Pacing and flight dynamics are adjusted for relaxing interactive control with holding orbits. The AI Agent transitions from an auto-takeover engine into an active Co-Pilot recommending the top actionable flight via a glowing visual guide. User controls (Spacebar, quick buttons, drag-and-drop) execute landing clearances with zero-penalty safety guardrails, triggering combo bonuses, audio-visual celebration, and star ratings.

**Tech Stack:** Python 3.10+, Pygame / Pygame-CE, Pygbag WebAssembly, SQLite (Memory/Disk), MySQL.

**Spec:** `docs/superpowers/specs/2026-11-22-casual-atc-co-pilot-design.md`

## Global Constraints
- Must maintain 100% compatibility with Pygbag WebAssembly (GitHub Pages) and desktop Pygame.
- Pure Python and Pygame only (no external numpy or compiled C extensions).
- All 13 existing unit tests (`tests/test_skyatc.py`) and 8 headless benchmark scenarios (`main.py --headless`) must pass without regression.
- Interactive mode must never auto-land aircraft without player confirmation unless headless mode is explicitly enabled.

## Review Focus
1. `CO_PILOT_TARGET` when all compatible runways are occupied: must gracefully display "WAITING FOR RUNWAY" and not crash or clear a blocked runway.
2. High-speed holding orbit transitions: an aircraft switching from `HOLD` to `APPROACH` must smoothly rotate heading towards the runway approach vector without teleportation.
3. Rapid Spacebar spamming: pressing Spacebar multiple times within a single second must only dispatch one clearance per frame without double-assigning runways.
4. Drag-and-drop safety guardrail: dragging a Heavy aircraft to a short runway must play an audible warning and show an on-screen toast without deducting penalty points.
5. Combo streak reset: landing aircraft after the 14-second window must cleanly reset the combo multiplier to 1x without memory leaks.

---

### Task 1: Pacing & Interactive Flight Dynamics

**Files:**
- Modify: `config.py:45-70`
- Modify: `environment/aircraft.py:160-230`
- Test: `tests/test_casual_dynamics.py`

**Interfaces:**
- Consumes: `Aircraft`, `FlightStatus`, `config.SIMULATION_SPEED_NORMAL`
- Produces: `Aircraft.update_orbit(dt)`, `config.INTERACTIVE_SPEED_FACTOR`, `config.COMBO_TIMEOUT_SECONDS`

- [ ] **Step 1: Write the failing test for holding orbit dynamics and pacing factor**

```python
# tests/test_casual_dynamics.py
import unittest
import math
from environment.aircraft import Aircraft, FlightStatus
import config

class TestCasualDynamics(unittest.TestCase):
    def test_holding_orbit_dynamics(self):
        ac = Aircraft(flight_id="BG-101", model="B737", x=500.0, y=100.0, heading=90.0)
        ac.status = FlightStatus.HOLD
        initial_dist = math.hypot(ac.x - ac.orbit_center_x, ac.y - ac.orbit_center_y)
        ac.update(1.0)
        new_dist = math.hypot(ac.x - ac.orbit_center_x, ac.y - ac.orbit_center_y)
        self.assertAlmostEqual(initial_dist, new_dist, delta=5.0)
        self.assertEqual(ac.status, FlightStatus.HOLD)

    def test_interactive_speed_factor_presence(self):
        self.assertTrue(hasattr(config, "INTERACTIVE_SPEED_FACTOR"))
        self.assertLessEqual(config.INTERACTIVE_SPEED_FACTOR, 0.85)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_casual_dynamics.py -v`  
Expected: FAIL with `AttributeError` or missing `orbit_center_x` / `INTERACTIVE_SPEED_FACTOR`.

- [ ] **Step 3: Implement holding orbit dynamics and config parameters**

In `config.py`, define:
```python
INTERACTIVE_SPEED_FACTOR = 0.70
COMBO_TIMEOUT_SECONDS = 14.0
AI_SYNERGY_BONUS_PTS = 30
TOUCHDOWN_PTS = 100
COMBO_STREAK_BONUS_PTS = 50
```
In `environment/aircraft.py`, initialize `self.orbit_center_x`, `self.orbit_center_y`, `self.orbit_angle`, `self.orbit_radius = 55.0` for aircraft in `FlightStatus.HOLD`. In `update(dt)`, when status is `HOLD`, advance `orbit_angle` smoothly along circular perimeter and update `(x, y)` and `heading`.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_casual_dynamics.py -v`  
Expected: PASS (2 tests ok).

- [ ] **Step 5: Commit**

```bash
git add config.py environment/aircraft.py tests/test_casual_dynamics.py
git commit -m "feat: add holding orbit dynamics and casual pacing factor"
```

---

### Task 2: AI Co-Pilot Recommendation Engine & Zero-Penalty Guardrail

**Files:**
- Modify: `config.py:115-135` (reward keys)
- Modify: `agent/reward.py:20-65`
- Modify: `agent/agent.py:100-180`
- Test: `tests/test_co_pilot.py`

**Interfaces:**
- Consumes: `ATCAgent`, `Airbase`, `RewardSystem`
- Produces: `ATCAgent.get_co_pilot_target() -> Optional[Tuple[Aircraft, Runway]]`, `ATCAgent.validate_guardrail(ac, rwy_id) -> Tuple[bool, str]`

- [ ] **Step 1: Write the failing test for actionable Co-Pilot recommendation and zero-penalty guardrail**

```python
# tests/test_co_pilot.py
import unittest
from environment.airbase import Airbase
from environment.aircraft import Aircraft, FlightStatus
from agent.agent import ATCAgent
from database.queries import DatabaseLogger

class TestCoPilot(unittest.TestCase):
    def setUp(self):
        self.airbase = Airbase(level_id=1)
        self.agent = ATCAgent(self.airbase, None)

    def test_co_pilot_finds_actionable_aircraft(self):
        ac1 = self.airbase.spawn_aircraft("BG-201", "B737", 500, 100, 90)
        ac1.status = FlightStatus.HOLD
        self.agent.step(0.1)
        target = self.agent.get_co_pilot_target()
        self.assertIsNotNone(target)
        ac, rwy = target
        self.assertEqual(ac.flight_id, "BG-201")
        self.assertIn("RWY", rwy.id)

    def test_guardrail_blocks_heavy_on_short_runway_without_penalty(self):
        ac = self.airbase.spawn_aircraft("BG-777", "B777", 500, 100, 90)
        rwy = self.airbase.runways["RWY 2"] # Assume short in layout
        rwy.length_m = 1800
        prev_score = self.agent.reward_system.cumulative_reward
        is_safe, msg = self.agent.validate_guardrail(ac, "RWY 2")
        self.assertFalse(is_safe)
        self.assertIn("short", msg.lower())
        self.assertEqual(self.agent.reward_system.cumulative_reward, prev_score)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_co_pilot.py -v`  
Expected: FAIL with `AttributeError: 'ATCAgent' object has no attribute 'get_co_pilot_target'`.

- [ ] **Step 3: Implement `get_co_pilot_target()` and `validate_guardrail()`**

In `agent/agent.py`:
- Implement `get_co_pilot_target() -> Optional[Tuple[Aircraft, Runway]]`: iterates ranked pending/holding aircraft; finds the highest-priority aircraft with an available, compatible runway; returns `(aircraft, runway)`.
- Implement `validate_guardrail(aircraft, runway_id) -> Tuple[bool, str]`: checks aircraft length requirement and runway occupancy. If invalid, returns `(False, reason_message)` without deducting points.
- In `step(dt)`: guard the 10-second auto-timeout execution with `if self.auto_takeover_enabled: ...` (defaults to `False` in interactive mode, `True` in headless mode).

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_co_pilot.py -v`  
Expected: PASS (2 tests ok).

- [ ] **Step 5: Commit**

```bash
git add config.py agent/reward.py agent/agent.py tests/test_co_pilot.py
git commit -m "feat: add actionable co-pilot recommendation and zero-penalty guardrail"
```

---

### Task 3: Visual Decluttering, Fuel Rings & Co-Pilot Glowing Guide

**Files:**
- Modify: `gui/display.py:220-410`
- Test: `tests/test_display_rendering.py`

**Interfaces:**
- Consumes: `DisplayRenderer`, `Aircraft`, `ATCAgent.get_co_pilot_target()`
- Produces: `DisplayRenderer._draw_aircraft_clean()`, `DisplayRenderer._draw_co_pilot_guide()`

- [ ] **Step 1: Write the failing test for clean aircraft tags and fuel ring**

```python
# tests/test_display_rendering.py
import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from environment.aircraft import Aircraft
from gui.display import DisplayRenderer

class TestDisplayRendering(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1360, 768))
        self.renderer = DisplayRenderer(self.screen)

    def test_fuel_color_thresholds(self):
        ac_green = Aircraft("BG-1", "B737", 100, 100, 90, fuel_level=80.0)
        ac_amber = Aircraft("BG-2", "B737", 100, 100, 90, fuel_level=35.0)
        ac_red = Aircraft("BG-3", "B737", 100, 100, 90, fuel_level=12.0)
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_green.fuel_level), (50, 220, 90))
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_amber.fuel_level), (255, 185, 35))
        self.assertEqual(self.renderer._get_fuel_ring_color(ac_red.fuel_level), (240, 50, 50))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_display_rendering.py -v`  
Expected: FAIL with `AttributeError: 'DisplayRenderer' object has no attribute '_get_fuel_ring_color'`.

- [ ] **Step 3: Implement clean aircraft tags, fuel ring and glowing co-pilot guide in `gui/display.py`**

- Implement `_get_fuel_ring_color(fuel: float) -> Tuple[int, int, int]`.
- In `_draw_aircraft()`:
  - Render an anti-aliased circular fuel gauge arc around the aircraft sprite.
  - Show minimal callsign pill `BG-386` (omit the verbose `38% [LAND] [HVY]` telemetry string unless aircraft is selected or hovered).
- Implement `_draw_co_pilot_guide(co_pilot_target)`:
  - Draws an animated glowing dotted bezier/line from the target aircraft to the runway entry point with a subtle arrow head.
  - Draws a soft pulsing halo on the target runway.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_display_rendering.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gui/display.py tests/test_display_rendering.py
git commit -m "feat: add clean aircraft tags, circular fuel gauge and co-pilot glowing guide"
```

---

### Task 4: Interactive 1-Click Controls, Spacebar Clearance, Combos & 3-Star Victory

**Files:**
- Modify: `gui/game.py:180-520`
- Test: `tests/test_gameplay_controls.py`

**Interfaces:**
- Consumes: `ATCAgent.get_co_pilot_target()`, `DisplayRenderer`, `SoundManager`
- Produces: `SkyATCGame._on_clear_landing_space()`, `SkyATCGame.combo_streak`, `SkyATCGame._calculate_stars()`

- [ ] **Step 1: Write the failing test for Spacebar clearance and combo multiplier**

```python
# tests/test_gameplay_controls.py
import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
from gui.game import SkyATCGame
from environment.aircraft import FlightStatus

class TestGameplayControls(unittest.TestCase):
    def setUp(self):
        self.game = SkyATCGame(initial_level=1)

    def test_spacebar_clearance_executes_target(self):
        ac = self.game.airbase.spawn_aircraft("BG-999", "B737", 500, 100, 90)
        ac.status = FlightStatus.HOLD
        self.game.agent.step(0.1)
        executed = self.game._on_clear_landing_space()
        self.assertTrue(executed)
        self.assertEqual(ac.status, FlightStatus.APPROACH)

    def test_star_rating_calculation(self):
        self.assertEqual(self.game._calculate_stars(crashed=True, score=200, max_score=200), 0)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=180, max_score=200), 3)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=110, max_score=200), 2)
        self.assertEqual(self.game._calculate_stars(crashed=False, score=40, max_score=200), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_gameplay_controls.py -v`  
Expected: FAIL with `AttributeError: 'SkyATCGame' object has no attribute '_on_clear_landing_space'`.

- [ ] **Step 3: Implement Spacebar clearance, button, combo tracking, and 3-star modal in `gui/game.py`**

- In `_handle_events()`:
  - Add `pygame.K_SPACE`: calls `self._on_clear_landing_space()`.
  - Add keys `pygame.K_1` through `K_4`: manual assign to Runway 1..4.
  - Add key `pygame.K_h`: send to Hold.
- In `_rebuild_buttons()`:
  - Replace confusing buttons with prominent `[CLEAR LANDING (SPACE)]` button.
- In `_on_clear_landing_space()`:
  - Fetches `target = self.agent.get_co_pilot_target()`. If valid, clears aircraft to approach, plays radio clearance sound, adds `+30 AI SYNERGY` bonus.
- In `update()`:
  - Check combo timer: if plane lands within `COMBO_TIMEOUT_SECONDS` of last landing, increment `combo_streak`, award `COMBO_STREAK_BONUS_PTS`, show floating combo text `COMBO x2!`.
- In `_trigger_complete_modal()`:
  - Calculate stars (⭐⭐⭐), render animated stars on victory dialog, and persist to level history.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_gameplay_controls.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gui/game.py tests/test_gameplay_controls.py
git commit -m "feat: add 1-click spacebar clearance, combo streaks and 3-star victory modal"
```

---

### Task 5: End-to-End Regression Verification & Pygbag WASM Deployment

**Files:**
- Test: `tests/test_skyatc.py`
- Test: `main.py --headless`
- Pygbag: `pygbag --build .`

- [ ] **Step 1: Run complete unit test suite**

Run: `$env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; & "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest discover tests -v`  
Expected: ALL tests pass (13 original + 4 new test suites).

- [ ] **Step 2: Run headless evaluation benchmark**

Run: `$env:DB_TYPE="sqlite"; $env:SQLITE_PATH="data/_verify_headless.db"; & "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py --headless; Remove-Item "data/_verify_headless.db" -ErrorAction SilentlyContinue`  
Expected: 8/8 scenarios PASS, total score >= +840 PTS.

- [ ] **Step 3: Verify local Pygbag build**

Run: `& "C:\Users\HP\.gemini\antigravity\brain\9709020b-2051-449b-9deb-0228e304ace6\scratch\pygbag_venv\Scripts\python.exe" -m pygbag --build --width 1360 --height 768 --app_name "SkyATC AI" --title "SkyATC AI" --ume_block 0 .`  
Expected: Pygbag build completes cleanly with exit code 0.

- [ ] **Step 4: Push to GitHub for automatic live deployment**

```bash
git push origin main
```
Verify GitHub Actions starts deploying updated game to `https://arif42sh.github.io/ATC-Simulation-game/`.

