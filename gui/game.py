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

    def _switch_state(self, new_state: str):
        self.current_state = new_state
        self.drag_state = None
        self._cached_global = self.db_logger.get_global_counters()
        self._cached_prog = self.db_logger.get_level_progression()

        if new_state == GameState.AI_STATS:
            self._cached_stats = self.db_logger.get_stats_dashboard_data()
            self.log_scroll = 0
            self.export_toast = ""

        self._rebuild_buttons()

    def _rebuild_buttons(self):
        cx = config.WINDOW_WIDTH // 2
        buttons: List[Button] = []

        if self.current_state == GameState.MAIN_MENU:
            bw, bh = 260, 48
            bx = cx - bw // 2
            buttons.extend([
                Button(bx, 305, bw, bh, "START GAME", self._on_start_game,
                       bg_color=(28, 150, 64), hover_color=(38, 185, 82), border_color=config.COLOR_PRIMARY_GREEN, font_size=16),
                Button(bx, 365, bw, bh, "RESUME GAME", self._on_resume_game,
                       bg_color=(56, 86, 118), hover_color=(76, 114, 152), border_color=config.COLOR_CYAN,
                       font_size=15, enabled=self.has_active_session),
                Button(bx, 425, bw, bh, "SELECT LEVEL", lambda: self._switch_state(GameState.LEVEL_SELECT),
                       bg_color=(36, 92, 168), hover_color=(52, 122, 212), border_color=config.COLOR_CYAN, font_size=15),
                Button(bx, 485, bw, bh, "AI & DB STATS", lambda: self._switch_state(GameState.AI_STATS),
                       bg_color=(165, 96, 28), hover_color=(205, 122, 38), border_color=config.COLOR_WARN_AMBER, font_size=15),
                Button(bx, 545, bw, bh, "EXIT", self._on_exit,
                       bg_color=(92, 42, 46), hover_color=(135, 56, 60), border_color=config.COLOR_CRITICAL_RED, font_size=15),
            ])

        elif self.current_state == GameState.LEVEL_SELECT:
            completed = set(self._cached_prog.get("completed_levels", []))
            max_unlocked = self._cached_prog.get("max_unlocked", 1)
            row_ys = [194, 284, 374, 464]

            for lvl in range(1, 21):
                row_idx = (lvl - 1) // 5
                col_idx = (lvl - 1) % 5
                tx = 372 + col_idx * 84
                ty = row_ys[row_idx]
                is_unlocked = self.demo_unlock_all or (lvl <= max_unlocked)
                is_done = lvl in completed
                is_sel = (lvl == self.selected_level)

                if is_done:
                    bg, hv, brd = (28, 138, 66), (40, 175, 86), config.COLOR_PRIMARY_GREEN
                    icon = "CHECK"
                elif is_unlocked:
                    bg, hv, brd = (44, 72, 108), (64, 102, 148), config.COLOR_CYAN
                    icon = None
                else:
                    bg, hv, brd = (48, 60, 76), (58, 72, 92), (82, 98, 120)
                    icon = "LOCK"

                buttons.append(Button(
                    tx, ty, 70, 56, f"{lvl:02d}",
                    callback=(lambda n=lvl: self._select_level_tile(n)),
                    bg_color=bg, hover_color=hv, border_color=brd,
                    font_size=18, enabled=True, selected=is_sel, tag_icon=icon
                ))

            can_start = self.demo_unlock_all or (self.selected_level <= max_unlocked)
            demo_lbl = f"DEMO UNLOCK: {'ON' if self.demo_unlock_all else 'OFF'}"
            buttons.extend([
                Button(290, 615, 240, 50, "BACK TO MAIN MENU", lambda: self._switch_state(GameState.MAIN_MENU),
                       bg_color=(130, 78, 36), hover_color=(165, 98, 46), border_color=config.COLOR_WARN_AMBER, font_size=14),
                Button(550, 615, 220, 50, demo_lbl, self._toggle_demo_unlock,
                       bg_color=(42, 64, 96), hover_color=(58, 88, 130), border_color=config.COLOR_CYAN, font_size=13),
                Button(790, 615, 260, 50, f"START LEVEL {self.selected_level:02d}", lambda: self.start_level(self.selected_level),
                       bg_color=(28, 152, 68), hover_color=(38, 188, 86), border_color=config.COLOR_PRIMARY_GREEN,
                       font_size=15, enabled=can_start),
            ])

        elif self.current_state == GameState.SIMULATION:
            if self.modal_state:
                mw, mh = 620, 440
                mx, my = (config.WINDOW_WIDTH - mw) // 2, (config.WINDOW_HEIGHT - mh) // 2
                by = my + mh - 70
                if self.modal_state["type"] == "COMPLETE" and self.level_mgr.current_level < 20:
                    buttons.append(Button(mx + 42, by, 170, 44, "NEXT LEVEL",
                                          lambda: self.start_level(self.level_mgr.current_level + 1),
                                          bg_color=(28, 150, 64), hover_color=(38, 188, 82), border_color=config.COLOR_PRIMARY_GREEN, font_size=14))
                    buttons.append(Button(mx + 226, by, 168, 44, "REPLAY LEVEL",
                                          lambda: self.start_level(self.level_mgr.current_level),
                                          bg_color=(36, 86, 152), hover_color=(52, 114, 196), border_color=config.COLOR_CYAN, font_size=14))
                    buttons.append(Button(mx + 408, by, 168, 44, "MAIN MENU",
                                          self._exit_modal_to_menu,
                                          bg_color=(82, 54, 42), hover_color=(118, 76, 58), font_size=14))
                else:
                    buttons.append(Button(mx + 95, by, 200, 44, "RETRY LEVEL",
                                          lambda: self.start_level(self.level_mgr.current_level),
                                          bg_color=(28, 150, 64), hover_color=(38, 188, 82), border_color=config.COLOR_PRIMARY_GREEN, font_size=14))
                    buttons.append(Button(mx + 325, by, 200, 44, "MAIN MENU",
                                          self._exit_modal_to_menu,
                                          bg_color=(110, 48, 52), hover_color=(148, 64, 68), border_color=config.COLOR_CRITICAL_RED, font_size=14))
            else:
                # Top bar controls: Pause (||), Speed (0.5x/1x/2x), SFX Mute, Menu
                p_lbl = "RESUME" if self.is_paused else "PAUSE ||"
                speed_lbl = "0.5x" if self.sim_speed < 0.9 else f"{int(self.sim_speed)}x"
                speed_bg = (28, 92, 96) if self.sim_speed < 0.9 else ((145, 96, 26) if self.sim_speed > 1.1 else (38, 64, 92))
                speed_hv = (40, 128, 134) if self.sim_speed < 0.9 else ((180, 120, 36) if self.sim_speed > 1.1 else (54, 92, 130))
                speed_brd = config.COLOR_PRIMARY_GREEN if self.sim_speed < 0.9 else (config.COLOR_WARN_AMBER if self.sim_speed > 1.1 else config.COLOR_CYAN)
                buttons.extend([
                    Button(764, 9, 82, 32, p_lbl, self._toggle_pause,
                           bg_color=(160, 88, 28) if self.is_paused else (38, 64, 92),
                           hover_color=(195, 110, 38) if self.is_paused else (54, 92, 130),
                           border_color=config.COLOR_CYAN, font_size=12),
                    Button(852, 9, 54, 32, speed_lbl, self._toggle_speed,
                           bg_color=speed_bg, hover_color=speed_hv, border_color=speed_brd, font_size=12),
                    Button(912, 9, 54, 32, "MUTE" if self.sound.muted else "SFX", self._toggle_mute,
                           bg_color=(42, 56, 74), hover_color=(62, 82, 108), font_size=11),
                    Button(1274, 9, 72, 32, "MENU", self._return_to_menu_paused,
                           bg_color=(52, 62, 82), hover_color=(76, 92, 118), font_size=12),
                ])

                # Sidebar HITL primary actions
                active_ctl = not self.is_paused
                buttons.extend([
                    Button(992, 586, 170, 48, "ACCEPT AI PLAN", self._on_accept_ai_plan,
                           bg_color=(26, 148, 64), hover_color=(38, 185, 84), border_color=config.COLOR_PRIMARY_GREEN,
                           font_size=13, enabled=active_ctl),
                    Button(1172, 586, 171, 48, "OVERRIDE", self._toggle_override_mode,
                           bg_color=(195, 96, 32) if self.override_mode else (155, 64, 32),
                           hover_color=(225, 115, 42), border_color=config.COLOR_WARN_AMBER,
                           font_size=13, enabled=active_ctl, selected=self.override_mode),
                ])

                # Quick manual runway override buttons (RWY 1..N + HOLD)
                rwy_ids = list(self.airbase.runways.keys())
                slot_count = len(rwy_ids) + 1
                total_w = 351
                gap = 6
                bw = (total_w - gap * (slot_count - 1)) // slot_count
                rx = 992
                for idx, r_id in enumerate(rwy_ids):
                    short_lbl = f"R{idx + 1}"
                    buttons.append(Button(
                        rx, 668, bw, 42, short_lbl,
                        callback=(lambda rid=r_id: self._manual_assign_selected(rid)),
                        bg_color=(28, 68, 108), hover_color=(42, 96, 152),
                        border_color=config.COLOR_CYAN, font_size=13, enabled=active_ctl,
                    ))
                    rx += bw + gap
                buttons.append(Button(
                    rx, 668, bw, 42, "HOLD",
                    callback=lambda: self._manual_assign_selected("HOLD"),
                    bg_color=(96, 72, 26), hover_color=(135, 100, 38),
                    border_color=config.COLOR_WARN_AMBER, font_size=12, enabled=active_ctl,
                ))

        elif self.current_state == GameState.AI_STATS:
            buttons.extend([
                Button(884, 405, 28, 28, "^", lambda: self._scroll_logs(-1), bg_color=(38, 58, 86), hover_color=(56, 86, 126), font_size=12),
                Button(884, 616, 28, 28, "v", lambda: self._scroll_logs(1), bg_color=(38, 58, 86), hover_color=(56, 86, 126), font_size=12),
                Button(360, 684, 280, 50, "BACK TO MAIN MENU", lambda: self._switch_state(GameState.MAIN_MENU),
                       bg_color=(132, 78, 34), hover_color=(168, 100, 44), border_color=config.COLOR_WARN_AMBER, font_size=14),
                Button(680, 684, 300, 50, "EXPORT REPORT (CSV)", self._on_export_csv,
                       bg_color=(28, 148, 64), hover_color=(38, 185, 84), border_color=config.COLOR_PRIMARY_GREEN, font_size=14),
            ])

        self.action_panel.set_buttons(buttons)

    # -------------------------------------------------------------------------
    # Button Callbacks
    # -------------------------------------------------------------------------

    def _on_start_game(self):
        self.sound.play("click")
        next_lvl = self._cached_prog.get("max_unlocked", 1)
        self.start_level(next_lvl)

    def _on_resume_game(self):
        if self.has_active_session:
            self.sound.play("click")
            self.is_paused = False
            self._switch_state(GameState.SIMULATION)

    def _on_exit(self):
        self.is_running = False

    def _select_level_tile(self, level_id: int):
        self.sound.play("click")
        self.selected_level = level_id
        self._rebuild_buttons()

    def _toggle_demo_unlock(self):
        self.sound.play("click")
        self.demo_unlock_all = not self.demo_unlock_all
        self._rebuild_buttons()

    def start_level(self, level_id: int):
        self.selected_level = max(1, min(20, int(level_id)))
        self.level_mgr.start_level(self.selected_level)
        self.agent.reset_for_level(self.selected_level)
        self.selected_aircraft = None
        self.override_mode = False
        self.drag_state = None
        self.modal_state = None
        self.is_paused = False
        self.sim_speed = config.SIMULATION_SPEED_NORMAL
        self.has_active_session = True
        self._seen_emergency_ids.clear()
        self.renderer.floating_texts.clear()
        self.renderer.particles.clear()
        self.db_logger.log_event(self.selected_level, "LEVEL_START", f"Started Level {self.selected_level:02d}")
        self._switch_state(GameState.SIMULATION)

    def _return_to_menu_paused(self):
        self.sound.play("click")
        self.is_paused = True
        self._switch_state(GameState.MAIN_MENU)

    def _exit_modal_to_menu(self):
        self.sound.play("click")
        self.modal_state = None
        self.has_active_session = False
        self._switch_state(GameState.MAIN_MENU)

    def _toggle_pause(self):
        self.sound.play("click")
        self.is_paused = not self.is_paused
        self._rebuild_buttons()

    def _toggle_speed(self):
        self.sound.play("click")
        if self.sim_speed < 0.9:
            self.sim_speed = config.SIMULATION_SPEED_NORMAL
        elif self.sim_speed > 1.1:
            self.sim_speed = config.SIMULATION_SPEED_SLOW
        else:
            self.sim_speed = config.SIMULATION_SPEED_FAST
        self._rebuild_buttons()

    def _toggle_mute(self):
        self.sound.toggle_mute()
        self._rebuild_buttons()

    def _toggle_override_mode(self):
        self.sound.play("click")
        self.override_mode = not self.override_mode
        if self.override_mode and not self.selected_aircraft:
            pending = self.airbase.get_ranked_pending_aircraft()
            if pending:
                self.selected_aircraft = pending[0]
        self._rebuild_buttons()

    def _on_accept_ai_plan(self):
        if self.agent.accept_ai_plan():
            self.sound.play("click")
            self.override_mode = False
            self.renderer.add_floating_text("AI PLAN ACCEPTED!", 480, 120, config.COLOR_PRIMARY_GREEN)
            self._rebuild_buttons()
        else:
            self.sound.play("warning")

    def _manual_assign_selected(self, runway_id: str):
        target = self.selected_aircraft
        if not target or target.status != FlightStatus.HOLDING:
            pending = self.airbase.get_ranked_pending_aircraft()
            target = pending[0] if pending else None

        if not target:
            return

        ok, msg = self.agent.override_assignment(target.flight_id, runway_id)
        if ok:
            self.sound.play("click")
            self.override_mode = False
            self.selected_aircraft = None
            self.renderer.add_floating_text(msg, target.x, target.y - 24, config.COLOR_CYAN)
        else:
            self.sound.play("warning")
            self.renderer.add_floating_text(msg, target.x, target.y - 24, config.COLOR_CRITICAL_RED)
        self._rebuild_buttons()

    def _scroll_logs(self, delta: int):
        logs = (self._cached_stats or {}).get("recent_logs", [])
        max_scroll = max(0, len(logs) - 8)
        self.log_scroll = max(0, min(max_scroll, self.log_scroll + delta))

    def _on_export_csv(self):
        self.sound.play("click")
        out_path = self.db_logger.export_logs_to_csv()
        self.export_toast = f"Report exported successfully: exports/{out_path.name}"

    # -------------------------------------------------------------------------
    # Main Simulation Loop & Event Dispatch
    # -------------------------------------------------------------------------

    def run(self):
        while self.is_running:
            raw_dt = min(self.clock.tick(config.FPS) / 1000.0, 0.08)
            dt = raw_dt * self.sim_speed

            self._handle_events()
            self.renderer.update_vfx(raw_dt)

            if self.current_state == GameState.SIMULATION and not self.is_paused and not self.modal_state:
                crashed_ac = self.airbase.update(dt)
                self.agent.step(dt)
                self.level_mgr.update(dt)

                # Trigger audio, notifications & smoke on events
                while self.agent.notifications:
                    note = self.agent.notifications.pop(0)
                    self.renderer.add_floating_text(note, 480, 120, config.COLOR_CYAN)

                for ac in self.airbase.aircraft_fleet:
                    if ac.is_emergency() and ac.flight_id not in self._seen_emergency_ids:
                        self._seen_emergency_ids.add(ac.flight_id)
                        self.sound.play("emergency")
                    if ac.touchdown_occurred and not ac.touchdown_sound_played:
                        ac.touchdown_sound_played = True
                        self.sound.play("landing")
                        self.renderer.add_touchdown_smoke(ac.x, ac.y)
                        self.renderer.add_floating_text(f"{ac.flight_id} LANDED!", ac.x, ac.y - 22, config.COLOR_PRIMARY_GREEN)

                if crashed_ac:
                    self._trigger_crash_modal(crashed_ac)
                elif self.level_mgr.is_level_complete():
                    self._trigger_complete_modal()

            self._render_current_screen()
            self.action_panel.draw(self.screen)
            pygame.display.flip()

        self.db_logger.db.close()
        pygame.quit()
        sys.exit()

    def _trigger_crash_modal(self, crashed_ac: Aircraft):
        self.sound.play("warning")
        self.has_active_session = False
        self.agent.reward_system.evaluate_action("UNSAFE_DECISION", crashed_ac.flight_id, crashed_ac.crash_reason)
        score = self.agent.reward_system.cumulative_reward
        self.db_logger.log_level_history(
            self.level_mgr.current_level, "CRASHED", score,
            len(self.airbase.flight_history), self.agent.stats["emergencies_handled"],
        )
        self.db_logger.log_event(self.level_mgr.current_level, "CRASH", crashed_ac.crash_reason, aircraft_id=crashed_ac.flight_id)

        self.modal_state = {
            "type": "CRASH",
            "title": f"LEVEL {self.level_mgr.current_level:02d} FAILED — CRASH ALERT",
            "subtitle": crashed_ac.crash_reason,
            "score": score,
            "landings": len(self.airbase.flight_history),
            "emergencies": self.agent.stats["emergencies_handled"],
            "breakdown": self.agent.reward_system.get_breakdown(),
        }
        self._rebuild_buttons()

    def _trigger_complete_modal(self):
        self.sound.play("victory")
        self.has_active_session = False
        score = self.agent.reward_system.cumulative_reward
        landed = len(self.airbase.flight_history)
        emerg = self.agent.stats["emergencies_handled"]
        self.db_logger.log_level_history(self.level_mgr.current_level, "COMPLETED", score, landed, emerg)
        self.db_logger.log_event(self.level_mgr.current_level, "LEVEL_COMPLETE", f"Completed Level {self.level_mgr.current_level} with {score} pts")

        self.modal_state = {
            "type": "COMPLETE",
            "title": f"LEVEL {self.level_mgr.current_level:02d} COMPLETE!",
            "subtitle": f"All {landed} incoming aircraft landed safely ({self.level_mgr.level_cfg['difficulty']}).",
            "score": score,
            "landings": landed,
            "emergencies": emerg,
            "breakdown": self.agent.reward_system.get_breakdown(),
        }
        self._rebuild_buttons()

    def _render_current_screen(self):
        mysql_ok = self.db_logger.is_mysql_connected()
        ai_ready = self.agent.llm_client.is_api_configured()

        if self.current_state == GameState.MAIN_MENU:
            self.renderer.render_main_menu(self.airbase, self._cached_global, mysql_ok, ai_ready)
        elif self.current_state == GameState.LEVEL_SELECT:
            self.renderer.render_level_select(
                self.airbase, self._cached_global, self._cached_prog,
                self.selected_level, self.demo_unlock_all, mysql_ok, ai_ready,
            )
        elif self.current_state == GameState.SIMULATION:
            self.renderer.render_simulation(
                self.airbase, self.agent, self.level_mgr,
                self.selected_aircraft, self.override_mode, self.drag_state,
                self.is_paused, self.sim_speed, self.modal_state, self.sound.muted,
            )
        elif self.current_state == GameState.AI_STATS:
            self.renderer.render_ai_stats(
                self.airbase, self._cached_global,
                self._cached_stats or self.db_logger.get_stats_dashboard_data(),
                self.log_scroll, self.export_toast, mysql_ok, ai_ready,
            )

    def _find_hovered_runway(self, mx: int, my: int) -> Optional[str]:
        for r_id, rwy in self.airbase.runways.items():
            if rwy.distance_to_point(mx, my) <= 30.0:
                return r_id
        return None

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
                return

            if self.action_panel.handle_event(event):
                continue

            if self.current_state == GameState.AI_STATS:
                if event.type == pygame.MOUSEWHEEL:
                    self._scroll_logs(-event.y)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._switch_state(GameState.MAIN_MENU)

            elif self.current_state == GameState.LEVEL_SELECT:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._switch_state(GameState.MAIN_MENU)

            elif self.current_state == GameState.SIMULATION and not self.modal_state:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self._toggle_pause()
                        continue
                    if event.key == pygame.K_ESCAPE:
                        self._return_to_menu_paused()
                        continue

                if self.is_paused:
                    self.drag_state = None
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    # 1. Check click on holding aircraft on canvas -> select & start Drag-and-Draw
                    clicked_ac = None
                    for ac in self.airbase.aircraft_fleet:
                        if ac.status == FlightStatus.HOLDING and math.hypot(ac.x - mx, ac.y - my) <= 28.0:
                            clicked_ac = ac
                            break
                    if clicked_ac:
                        self.selected_aircraft = clicked_ac
                        self.drag_state = {"aircraft": clicked_ac, "mouse_pos": (mx, my), "hovered_runway": None, "is_valid": True, "reason": ""}
                        continue

                    # 2. Check click on INCOMING PRIORITY QUEUE sidebar card -> select aircraft
                    if config.SIDEBAR_X + 20 <= mx <= config.WINDOW_WIDTH - 20 and 148 <= my <= 370:
                        pending_ranked = self.airbase.get_ranked_pending_aircraft()
                        card_idx = (my - 148) // 54
                        if 0 <= card_idx < len(pending_ranked[:4]):
                            self.selected_aircraft = pending_ranked[card_idx]
                            self.sound.play("click")
                        continue

                    # 3. Click-Plane-Then-Click-Runway support on radar canvas
                    if mx < config.SIDEBAR_X and self.selected_aircraft and self.selected_aircraft.status == FlightStatus.HOLDING:
                        r_id = self._find_hovered_runway(mx, my)
                        if r_id:
                            sel_ac = self.selected_aircraft
                            ok, msg = self.agent.override_assignment(sel_ac.flight_id, r_id)
                            if ok:
                                self.sound.play("click")
                                self.selected_aircraft = None
                                self.override_mode = False
                                self.renderer.add_floating_text(msg, sel_ac.x, sel_ac.y - 24, config.COLOR_CYAN)
                            else:
                                self.sound.play("warning")
                                self.renderer.add_floating_text(msg, sel_ac.x, sel_ac.y - 24, config.COLOR_CRITICAL_RED)
                            self._rebuild_buttons()
                        else:
                            self.selected_aircraft = None

                elif event.type == pygame.MOUSEMOTION and self.drag_state:
                    mx, my = event.pos
                    r_id = self._find_hovered_runway(mx, my)
                    is_valid, reason = True, ""
                    if r_id:
                        ac = self.drag_state["aircraft"]
                        test_plan = {"assignments": [{"flight_id": ac.flight_id, "priority": 1, "assigned_runway": r_id, "action": "AUTHORIZE_LANDING"}]}
                        ok, issues, _, val_code = self.agent.validator.validate_plan(test_plan, self.agent.observer.observe())
                        is_valid = ok
                        if ok:
                            reason = f"Assign -> {r_id}"
                        elif val_code == "CONSTRAINT_VIOLATION":
                            rwy_len = self.airbase.runways[r_id].length_m
                            reason = f"{r_id} too short ({rwy_len}m < {ac.min_runway_length_m}m)"
                        elif val_code == "RUNWAY_CONFLICT":
                            reason = f"{r_id} occupied"
                        elif val_code == "PRIORITY_VIOLATION":
                            reason = "Clear emergency flight first!"
                        elif val_code == "INVALID_RUNWAY":
                            reason = f"{r_id} unavailable"
                        else:
                            reason = issues[0].split(":")[-1].strip()[:36] if issues else "Invalid"
                    self.drag_state["mouse_pos"] = (mx, my)
                    self.drag_state["hovered_runway"] = r_id
                    self.drag_state["is_valid"] = is_valid
                    self.drag_state["reason"] = reason

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag_state:
                    mx, my = event.pos
                    r_id = self._find_hovered_runway(mx, my)
                    ac = self.drag_state["aircraft"]
                    self.drag_state = None
                    if r_id:
                        ok, msg = self.agent.override_assignment(ac.flight_id, r_id)
                        if ok:
                            self.sound.play("click")
                            self.selected_aircraft = None
                            self.override_mode = False
                            self.renderer.add_floating_text(msg, ac.x, ac.y - 24, config.COLOR_CYAN)
                        else:
                            self.sound.play("warning")
                            self.renderer.add_floating_text(msg, ac.x, ac.y - 24, config.COLOR_CRITICAL_RED)
                        self._rebuild_buttons()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self._on_accept_ai_plan()
                    elif event.key == pygame.K_h:
                        self._manual_assign_selected("HOLD")
                    elif event.key in (pygame.K_1, pygame.K_KP1):
                        self._manual_assign_selected("RWY 1")
                    elif event.key in (pygame.K_2, pygame.K_KP2) and "RWY 2" in self.airbase.runways:
                        self._manual_assign_selected("RWY 2")
                    elif event.key in (pygame.K_3, pygame.K_KP3) and "RWY 3" in self.airbase.runways:
                        self._manual_assign_selected("RWY 3")
                    elif event.key in (pygame.K_4, pygame.K_KP4) and "RWY 4" in self.airbase.runways:
                        self._manual_assign_selected("RWY 4")
