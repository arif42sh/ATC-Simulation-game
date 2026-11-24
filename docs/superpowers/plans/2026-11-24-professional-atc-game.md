# Professional Fullscreen Casual ATC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform SkyATC AI into a commercial-grade, clutter-free, professional air traffic control game by eliminating the 385px telemetry sidebar in favor of a 100% fullscreen radar scope, enabling intuitive two-way runway landings, natural wide holding patterns, visual SOS alerts (icons/beacons), an AI spotlight guide, live 3-star HUD progress bar, and authentic radio pilot comms bubbles.

**Architecture:**
- **Canvas & Screen Layout:** Expand gameplay canvas to full 1360x768. Remove sidebar from active simulation. Centered airbase geometry.
- **Two-Way Runway Mechanics:** Runways support bidirectional landing (Start->End or End->Start) selected automatically based on which runway threshold the player drags to.
- **Flight Dynamics:** Aircraft cruise naturally from sector boundaries and maintain a wide, spacious holding orbit instead of tight spinning clusters.
- **Visual Signals over Text:** Urgent aircraft display pulsing red SOS rings and emergency icons (⛽ Fuel, 🔥 Engine). AI Co-Pilot projects a golden spotlight beacon and glowing glide path to the best runway threshold.
- **Audio-Visual Feedback:** Radio transmission chatter bubbles (`🎙️ MAYDAY! BG-391 requesting RWY 1`), floating score badges (`+100 PERFECT TOUCHDOWN!`), and live top-bar 3-star meter.

**Tech Stack:** Python 3.10+, Pygame-CE, Pygbag WebAssembly, SQLite/MySQL.

**Spec:** Brainstorming consensus on 8 UX pillars (Fullscreen radar, Two-way runway landing, SOS beacons, Radio comms, Natural flight motion, Live star meter).

## Global Constraints
- Must maintain 100% compatibility with Pygbag WebAssembly (GitHub Pages) and desktop Pygame.
- Pure Python and Pygame only (no external numpy or compiled C extensions).
- All 22 existing unit tests and 8 headless benchmark scenarios (`main.py --headless`) must continue to pass without regression.
- Zero sidebar during active gameplay. All controls must be intuitive directly on the radar canvas.

## Review Focus
1. Runway two-way threshold selection: dropping near End must roll towards Start without reversing runway vectors or breaking rollout deceleration.
2. Fullscreen canvas boundary clamping: plane tags, radio comms bubbles, and floating score texts must never clip off the 1360x768 screen edges.
3. Airbase centering in 1360 width: runway layouts, tarmac polygons, and helipad must scale cleanly to the centered 1360 canvas.
4. Star progress calculation: star bar fill percentage must update smoothly in real time without exceeding 100%.
5. Headless benchmark preservation: headless scenarios rely on standard runway IDs (`RWY 1`, etc.); two-way threshold routing must remain transparent to headless automation.

---

### Task 1: Bidirectional Runway Threshold Geometry (Two-Way Landing)

**Files:**
- Modify: `environment/runway.py:40-95`
- Modify: `environment/airbase.py:170-220`
- Test: `tests/test_bidirectional_runway.py`

**Interfaces:**
- Consumes: `Runway`, `Airbase`, `Aircraft`
- Produces: `Runway.get_closest_threshold(px, py) -> Tuple[str, Tuple[float, float], Tuple[float, float], Tuple[float, float], float, float, float]`

- [ ] **Step 1: Write failing test for two-way runway threshold selection**

```python
# tests/test_bidirectional_runway.py
import unittest
from environment.runway import Runway
from environment.aircraft import Aircraft, FlightStatus

class TestBidirectionalRunway(unittest.TestCase):
    def test_runway_threshold_selection(self):
        rwy = Runway("RWY 1", "Runway 1", 3000, start=(300, 300), end=(700, 300), heading=90)
        # Point closer to Start (left end)
        thresh_start = rwy.get_closest_threshold(200, 300)
        self.assertEqual(thresh_start["direction"], "START_TO_END")
        self.assertAlmostEqual(thresh_start["start"][0], 300)
        self.assertAlmostEqual(thresh_start["end"][0], 700)

        # Point closer to End (right end)
        thresh_end = rwy.get_closest_threshold(800, 300)
        self.assertEqual(thresh_end["direction"], "END_TO_START")
        self.assertAlmostEqual(thresh_end["start"][0], 700)
        self.assertAlmostEqual(thresh_end["end"][0], 300)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_bidirectional_runway.py -v`  
Expected: FAIL with `AttributeError: 'Runway' object has no attribute 'get_closest_threshold'`.

- [ ] **Step 3: Implement bidirectional threshold geometry in `environment/runway.py` and `environment/airbase.py`**

In `environment/runway.py`:
Implement `get_closest_threshold(px, py) -> Dict[str, Any]` which calculates distance to `start` vs `end`.
- If closer to `start`: returns approach fix outside `start`, rollout toward `end`, unit vector `(ux, uy)`, angle `screen_angle_deg`.
- If closer to `end`: returns approach fix outside `end`, rollout toward `start`, unit vector `(-ux, -uy)`, angle `(screen_angle_deg + 180) % 360`.

In `environment/airbase.py`:
Update `authorize_landing(flight_id, runway_id, target_point=None)` to use `runway.get_closest_threshold(target_point)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_bidirectional_runway.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add environment/runway.py environment/airbase.py tests/test_bidirectional_runway.py
git commit -m "feat: add bidirectional runway landing threshold geometry"
```

---

### Task 2: Fullscreen 1360px Airbase Layout & Wide Holding Pattern

**Files:**
- Modify: `config.py:40-60, 135-215`
- Modify: `environment/aircraft.py:75-105, 185-215`
- Modify: `gui/display.py:180-240`
- Test: `tests/test_fullscreen_layout.py`

**Interfaces:**
- Consumes: `config.CANVAS_WIDTH = 1360`, `config.RUNWAY_LAYOUTS`
- Produces: Centered runway coordinates, wide perimeter holding orbits

- [ ] **Step 1: Write failing test for 1360px centered canvas and holding orbits**

```python
# tests/test_fullscreen_layout.py
import unittest
import config
from environment.aircraft import Aircraft, FlightStatus

class TestFullscreenLayout(unittest.TestCase):
    def test_fullscreen_canvas_width(self):
        self.assertEqual(config.CANVAS_WIDTH, config.WINDOW_WIDTH)
        self.assertEqual(config.CANVAS_WIDTH, 1360)

    def test_runway_centering_in_canvas(self):
        # Runway centers in 2-runway layout should be centered around X=680
        rwy1 = config.RUNWAY_LAYOUTS[2][0]
        mid_x = (rwy1["start"][0] + rwy1["end"][0]) / 2.0
        self.assertGreater(mid_x, 550)
        self.assertLess(mid_x, 800)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_fullscreen_layout.py -v`  
Expected: FAIL with `AssertionError: 975 != 1360`.

- [ ] **Step 3: Update `config.py` canvas size, centered runway geometry, and smooth aircraft holding paths**

In `config.py`:
- Set `SIDEBAR_WIDTH = 0` during simulation, `CANVAS_WIDTH = WINDOW_WIDTH` (1360).
- Offset runway start/end X-coordinates by `+190px` to perfectly center them in the 1360px screen.
- Offset tarmac polygon points by `+190px` in `gui/display.py`.

In `environment/aircraft.py`:
- Initialize holding aircraft along outer screen perimeter with wide orbit radius (`orbit_radius = 65.0` to `80.0`).
- Ensure aircraft rotate smoothly along wide flight paths without tight unnatural spinning.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_fullscreen_layout.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py environment/aircraft.py gui/display.py tests/test_fullscreen_layout.py
git commit -m "feat: center airbase geometry in 1360px fullscreen canvas with wide holding patterns"
```

---

### Task 3: Visual SOS Alerts, AI Spotlight Guide & Radio Pilot Comms

**Files:**
- Modify: `gui/display.py:560-720`
- Modify: `agent/agent.py:330-360`
- Test: `tests/test_visual_alerts.py`

**Interfaces:**
- Consumes: `Aircraft`, `ATCAgent.get_co_pilot_target()`, `DisplayRenderer`
- Produces: `DisplayRenderer._draw_radio_comms_bubble()`, `DisplayRenderer._draw_sos_beacon()`, `DisplayRenderer._draw_ai_spotlight()`

- [ ] **Step 1: Write failing test for SOS beacons and radio comms structure**

```python
# tests/test_visual_alerts.py
import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from gui.display import DisplayRenderer
from environment.aircraft import Aircraft, EmergencyType

class TestVisualAlerts(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1360, 768))
        self.renderer = DisplayRenderer(self.screen)

    def test_emergency_icon_helper(self):
        ac_fuel = Aircraft("BG-1", fuel_level=8.0)
        ac_eng = Aircraft("BG-2", emergency_type=EmergencyType.ENGINE_PROBLEM)
        self.assertEqual(self.renderer._get_emergency_symbol(ac_fuel), "FUEL")
        self.assertEqual(self.renderer._get_emergency_symbol(ac_eng), "ENGINE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_visual_alerts.py -v`  
Expected: FAIL with `AttributeError: 'DisplayRenderer' object has no attribute '_get_emergency_symbol'`.

- [ ] **Step 3: Implement SOS beacons, icons, AI spotlight, and radio comms bubble in `gui/display.py`**

- Implement `_get_emergency_symbol(ac: Aircraft) -> Optional[str]`: returns `"FUEL"`, `"ENGINE"`, `"MEDICAL"`, or `None`.
- In `_draw_gameplay_aircraft()`:
  - Render pulsing red SOS beacon with clean badge `[ ⛽ LOW FUEL ]` or `[ 🔥 ENGINE ]` above plane when in emergency.
  - Normal planes render clean callsign tag `BG-386` and circular fuel ring.
- In `_draw_ai_spotlight()`:
  - Draw golden beacon around the AI's top target aircraft.
  - Draw animated glowing dotted glide path from target plane to the recommended runway entry threshold.
  - Draw a pulsing green landing bracket on that specific runway end with `[PRESS SPACE TO LAND]`.
- Implement `_draw_radio_comms_bubble()`:
  - A sleek, translucent tactical radio box at top center:
    `🎙️ TOWER COMM: "MAYDAY! BG-391 requesting RWY 1 [PRESS SPACE]"`

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_visual_alerts.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gui/display.py agent/agent.py tests/test_visual_alerts.py
git commit -m "feat: add visual SOS beacons, AI spotlight guide and pilot radio comms"
```

---

### Task 4: Fullscreen HUD, Live 3-Star Meter & Two-Way Drag Controls

**Files:**
- Modify: `gui/game.py:195-235, 470-650`
- Modify: `gui/display.py:130-180` (top bar)
- Test: `tests/test_fullscreen_controls.py`

**Interfaces:**
- Consumes: `SkyATCGame`, `Airbase`, `DisplayRenderer`
- Produces: Fullscreen interactive drag-to-threshold, live 3-star bar render, spacebar clearance

- [ ] **Step 1: Write failing test for live star progress and drag-to-threshold**

```python
# tests/test_fullscreen_controls.py
import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
from gui.game import SkyATCGame

class TestFullscreenControls(unittest.TestCase):
    def setUp(self):
        self.game = SkyATCGame(initial_level=1)

    def test_live_star_progress_ratio(self):
        ratio = self.game.get_star_progress_ratio()
        self.assertGreaterEqual(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_fullscreen_controls.py -v`  
Expected: FAIL with `AttributeError: 'SkyATCGame' object has no attribute 'get_star_progress_ratio'`.

- [ ] **Step 3: Implement live star progress in top HUD and two-way drag controls in `gui/game.py`**

- In `gui/game.py`:
  - Implement `get_star_progress_ratio() -> float`.
  - Remove sidebar buttons from active simulation screen; replace with clean floating HUD controls (Pause, Speed, Audio, Menu) at the top corners and bottom legend.
  - In `_find_hovered_runway_threshold(mx, my)`: checks which runway and which end (threshold) is hovered.
  - In mouse drag drop: passes target drop point `(mx, my)` to `airbase.authorize_landing(flight_id, runway_id, target_point=(mx, my))` for instant two-way landing!
- In `gui/display.py`:
  - Render the sleek Live 3-Star progress bar in the center of the top HUD bar with golden stars (⭐ ⭐ ⭐) that light up as score reaches 1-star, 2-star, and 3-star thresholds.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest tests/test_fullscreen_controls.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gui/game.py gui/display.py tests/test_fullscreen_controls.py
git commit -m "feat: add live 3-star HUD progress bar and two-way drag-to-threshold controls"
```

---

### Task 5: End-to-End Regression Verification & Pygbag WASM Deployment

**Files:**
- Test: `tests/test_skyatc.py`
- Test: `main.py --headless`
- Pygbag: `pygbag --build .`

- [ ] **Step 1: Run complete unit test suite**

Run: `$env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; & "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m unittest discover tests -v`  
Expected: ALL tests pass (22 existing + 4 new test suites).

- [ ] **Step 2: Run headless evaluation benchmark**

Run: `$env:DB_TYPE="sqlite"; $env:SQLITE_PATH="data/_verify_headless.db"; & "C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py --headless; Remove-Item "data/_verify_headless.db" -ErrorAction SilentlyContinue`  
Expected: 8/8 scenarios PASS, total score >= +840 PTS.

- [ ] **Step 3: Verify local Pygbag build**

Run: `& "C:\Users\HP\.gemini\antigravity\brain\9709020b-2051-449b-9deb-0228e304ace6\scratch\pygbag_venv\Scripts\python.exe" -m pygbag --build --width 1360 --height 768 --app_name "SkyATC AI" --title "SkyATC AI" --ume_block 0 .`  
Expected: Build completes cleanly with exit code 0.

- [ ] **Step 4: Push to GitHub for automatic live deployment**

```bash
git push origin main
```
Verify GitHub Actions starts deploying updated game to `https://arif42sh.github.io/ATC-Simulation-game/`.
