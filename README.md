# SkyATC AI (V2) — An Intelligent Runway Management Agent

**Course:** CSE 3202 - Artificial Intelligence Sessional  
**Team Members:** Md. Arif Shahriar, Ashikur Rahman

## Overview
**SkyATC AI** is a 2D simulation-based AI runway management game built with **Python**, **Pygame**, **Google Gemini (`gemini-2.5-flash` via `google-genai` SDK)**, and **MySQL** (with automatic SQLite fallback).

### Key V2 Features
- **Landing-Focused Gameplay & 20 Progressive Levels:**
  - Levels `01–05` (**Easy**): 2 Runways
  - Levels `06–10` (**Medium**): 2 Runways
  - Levels `11–15` (**Hard**): 3 Runways + Heavy aircraft runway-length constraints
  - Levels `16–20` (**Expert**): 4 Runways + Dynamic maintenance, wind & multi-emergency traffic
- **Utility-Based Agent + Goal-Based Planning:**
  - **Min-Heap Priority Queue (`heapq`)**, **$O(1)$ Flight ID Hash Map**, FIFO Arrival Queue, and sorted UI queue.
  - Event-driven async **Gemini 2.5 Flash** (`response_mime_type="application/json"`) with seamless deterministic Min-Heap fallback + Explainable AI reason badge.
- **9-Rule Python AI Plan Validator:** Prevents invalid runways, occupied/maintenance conflicts, duplicate aircraft assignments, emergency starvation, and aircraft-size/runway-length mismatches.
- **10-Second Human-in-the-Loop (HITL) Window:** Accept AI plan (`ACCEPT AI PLAN`), Drag-and-Draw aircraft directly onto a runway, or use quick `OVERRIDE` controls — with autonomous AI execution on timeout.
- **9-Table Persistence & Analytics:** MySQL + SQLite fallback storing `aircraft`, `runways`, `missions_requests`, `agent_decisions`, `player_decisions`, `feedback`, `simulation_events`, `level_history`, and `reward_history`, plus **CSV Report Export**.

## Quick Start
```bash
pip install -r requirements.txt
python main.py                # Interactive GUI
python main.py --level 16     # Jump directly to 4-runway Expert level
python main.py --headless     # Run headless evaluation benchmark
python -m unittest tests/test_skyatc.py
```
