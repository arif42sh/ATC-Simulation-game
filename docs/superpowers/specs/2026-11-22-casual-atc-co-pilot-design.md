# SkyATC AI: Casual ATC Commander + AI Co-Pilot Design

**Date:** 2026-11-22  
**Status:** Approved for Implementation Planning  
**Topic:** Transforming SkyATC AI into an Addictive Casual Game with AI Co-Pilot  

---

## 1. Intent & The Why

### 1.1 Problem Statement
The current SkyATC AI simulation functions like an academic engineering telemetry dashboard:
- **Zero Player Agency:** The AI automatically lands aircraft when the 10-second HITL window expires, making the player feel like a passive spectator.
- **Sensory Overload:** The radar screen is cluttered with dense brackets, status codes (`BG-386 38% [LAND] [HVY]`), dotted trajectories, and warning boxes.
- **Rushed Pacing:** Aircraft cruise and spawn too quickly for a casual player to strategize or enjoy.
- **No Dopamine / Reward Loop:** Score values tick up silently in a corner; there are no clear combo streaks, visual celebrations, or satisfying feedback for good air traffic control.

### 1.2 Vision & Goals
Transform SkyATC AI into a fun, tactile, and addictive casual air traffic control game (reminiscent of casual classics like *Flight Control* and *Airport Madness*) where:
1. **The Player is the Commander:** Air traffic decisions are initiated and confirmed by the human player.
2. **The AI Agent is the Intelligent Co-Pilot:** The AI (Min-Heap priority scheduler, safety validator, and LLM explainable reasoner) guides the player with real-time landing recommendations, optimal runway allocation, and safety alerts.
3. **Pacing is Relaxing yet Tense:** Aircraft enter into smooth holding patterns at a manageable speed (~35% slower baseline in interactive play), giving players time to observe and direct traffic.
4. **Clean, Minimalist Aesthetics:** Clean aircraft icons with glowing circular fuel rings and sleek callsign labels; dense telemetry is tucked away.
5. **Addictive Dopamine Loop:** Immediate visual/audio feedback for smooth landings, "AI Synergy Combos" (`COMBO x2!`, `PERFECT TOUCHDOWN! +100`), and a clear 3-Star (⭐⭐⭐) rating at level completion.

### 1.3 Non-Goals & Anti-Goals
- **Non-Goal:** Stripping away the core AI algorithms (Min-Heap, Priority Queue, Safety Rule Engine, SQLite/MySQL logging, LLM reasoning). These remain 100% active and power the Co-Pilot.
- **Anti-Goal:** An "idle game" that plays itself without player participation.
- **Anti-Goal:** Punishing players with sudden unexplained crashes; any safety violation must be proactively warned by the AI Co-Pilot.

---

## 2. Technical & Platform Constraints
- Must maintain **100% compatibility with Pygbag WebAssembly (GitHub Pages)** and desktop Pygame.
- Pure Python and Pygame only (no external heavy libraries like numpy/scipy).
- All existing unit tests (`tests/test_skyatc.py`) and headless benchmark (`main.py --headless`) must continue to pass 100%.

---

## 3. Approaches Considered

### Approach A: ATC Commander + AI Co-Pilot (Chosen)
- The player directly clears landings using intuitive 1-click controls (Spacebar / Click to accept AI recommendation) or manual drag-and-drop.
- Aircraft hold in orbit until cleared; no auto-landing timeout in interactive mode.
- The AI Co-Pilot continuously calculates the optimal runway using Min-Heap and displays a clean visual guide (glowing trajectory arrow) to that runway.
- **Why chosen:** Preserves all backend algorithms, elevates the player's agency, and provides instant addictive satisfaction.

### Approach B: Crisis Commander / Time-Attack
- Focuses on fast timer clicks with a "Panic AI Bomb" superpower button.
- *Rejected:* Shifts the game too much into a pure reaction test rather than strategic ATC control.

### Approach C: Line-Drawing Flight Control
- The player draws arbitrary spline paths on the radar.
- *Rejected:* Requires massive refactoring of aircraft physics and breaks the structured runway approach constraints.

---

## 4. Detailed Specification

### 4.1 Aircraft Dynamics & Pacing
- **Cruising Speed:** Scaled to a relaxing, strategizable speed in interactive GUI gameplay (`sim_speed = 0.70x` baseline, adjustable via speed buttons).
- **Holding Pattern:** When an aircraft enters the sector, its initial state is `HOLD`. It maintains a gentle circular orbit at the sector boundary until assigned a runway by the player or Co-Pilot. Fuel burn rate scales proportionately with `dt` so holding is sustainable.
- **Fuel Ring:** Fuel is displayed as a clean circular gauge around the aircraft sprite:
  - Green (> 50%)
  - Amber (20% – 50%)
  - Pulsing Red (< 20%, Critical Emergency)

### 4.2 AI Co-Pilot Mechanic & Controls
- **Co-Pilot Recommendation:** The AI evaluates the fleet via Min-Heap priority and identifies the highest-priority aircraft that currently has an available, compatible runway (`CO_PILOT_TARGET`).
- **Visual Guide:** A soft glowing dotted trajectory connects the target aircraft to its recommended runway entry threshold.
- **1-Click Execution:**
  - Pressing `SPACEBAR` or clicking the prominent **`[CLEAR LANDING (SPACE)]`** button immediately clears the `CO_PILOT_TARGET` to approach and land on the AI's suggested runway.
  - Quick keyboard shortcuts: Keys `1`, `2`, `3`, `4` assign selected aircraft to Runway 1, 2, 3, or 4; `H` sends it to Hold orbit.
- **Drag & Drop:** Players can click/drag an aircraft directly to any runway for intuitive tactile control.
- **Safety Intercept (Zero-Penalty Guardrail):** If the player tries to route a Heavy aircraft to a short runway or an occupied runway, the AI Co-Pilot immediately chirps a warning audio cue and displays an on-screen toast: *"HOLD! RWY 3 is too short for B777!"*, preventing an unfair crash with zero score deduction.

### 4.3 Visual Decluttering
- **Default Aircraft Tag:** Simply displays the callsign (e.g. `BG-386`) and size icon.
- **Hidden Telemetry:** Speed, heading, and altitude data are hidden by default and only display when the aircraft is hovered or selected.
- **Runway Status:** Clean, discreet status pills that never occlude the runway strip.

### 4.4 Dopamine, Scoring & Audio Feedback
- **Landing Satisfaction:** On touchdown, play smooth tire-smoke particles, play landing SFX, and flash a green floating badge.
- **Combo System:**
  - Landing planes within 14 seconds of each other triggers combo multipliers (`COMBO x2! +50`, `COMBO x3! +100`).
  - Following the AI Co-Pilot recommendation grants an **`AI SYNERGY BONUS (+30)`**.
- **Level Completion Modal:**
  - Displays a clean victory banner with 1 to 3 golden stars (⭐⭐⭐) based on score and safe landings:
    - ⭐⭐⭐ (3 Stars): All aircraft landed safely, zero crashes, score >= 80% potential.
    - ⭐⭐ (2 Stars): All aircraft landed safely, zero crashes, score >= 50%.
    - ⭐ (1 Star): Level complete with no crashes.
  - Confetti/star particle bursts.

---

## 5. Builder Check & Edge Case Resolutions

1. **Interactive vs Headless Speed & Fuel:**
   - The comfortable pacing multiplier applies to interactive GUI gameplay, while headless benchmark (`main.py --headless`) and unit tests execute unthrottled. Fuel burn scales with simulation delta time `dt`, maintaining full safety margins.
2. **Actionable Runway Targeting:**
   - If the Min-Heap queue leader requires a runway currently in rollout, the Co-Pilot highlights the highest-priority aircraft with an open compatible runway for immediate Spacebar clearance, ensuring continuous fluid action.
3. **Reward System Harmonization:**
   - Touchdown scoring (`+100`), combos (`+50`/`+100`), and AI synergy (`+30`) are added to `config.REWARDS` and logged through `RewardSystem.evaluate_action()`, keeping the HUD, DB stats, and CSV exports unified.
4. **Forgiving Safety Guardrail:**
   - Invalid drag-drops or manual assignments are intercepted before crashing with a warning toast and zero score penalty, making the Co-Pilot feel like a protective ally.
5. **Star Rating Persistence:**
   - Stars are calculated formulaically upon level completion and saved to `level_history`, decorating the Level Select screen tiles.
