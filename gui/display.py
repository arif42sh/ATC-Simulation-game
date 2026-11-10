"""
=============================================================================
SkyATC AI - 2D Airbase & Multi-Screen Pygame Renderer (Module 1)
Implements Main Menu, 20-Level Select, Gameplay HUD, AI & DB Stats,
Drag-and-Draw Path Preview, and Pause / Level Complete / Crash Modals.
=============================================================================
"""

import math
import random
from typing import Dict, Any, List, Optional, Tuple
import pygame
import config
from config import RunwayStatus
from environment.airbase import Airbase
from environment.aircraft import Aircraft, FlightStatus
from environment.levels import LevelManager
from agent.agent import ATCAgent


class FloatingText:
    """Short-lived score or feedback toast floating above the airbase."""

    def __init__(self, text: str, x: float, y: float, color: Tuple[int, int, int], lifetime: float = 2.0):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        self.y -= 24.0 * dt
        return self.lifetime > 0.0

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        alpha = max(0, min(255, int(255 * (self.lifetime / self.max_lifetime))))
        shadow = font.render(self.text, True, (10, 15, 20))
        shadow.set_alpha(alpha)
        surface.blit(shadow, (int(self.x - shadow.get_width() // 2 + 1), int(self.y + 1)))
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x - surf.get_width() // 2), int(self.y)))


class SmokeParticle:
    """Subtle tyre touchdown puff on runway landing."""

    def __init__(self, x: float, y: float):
        self.x = x + random.uniform(-4, 4)
        self.y = y + random.uniform(-4, 4)
        self.vx = random.uniform(-18, 18)
        self.vy = random.uniform(-18, 18)
        self.r = random.uniform(3, 6)
        self.life = random.uniform(0.45, 0.85)
        self.max_life = self.life

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.r += 10.0 * dt
        return self.life > 0.0

    def draw(self, surface: pygame.Surface):
        alpha = max(0, min(255, int(200 * (self.life / self.max_life))))
        s = pygame.Surface((int(self.r * 2 + 2), int(self.r * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (235, 238, 240, alpha), (int(self.r + 1), int(self.r + 1)), int(self.r))
        surface.blit(s, (int(self.x - self.r), int(self.y - self.r)))


class DisplayRenderer:
    """Clean 2D renderer matching SkyATC AI V2 UI mockups and improvements."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.pulse_phase: float = 0.0
        self.floating_texts: List[FloatingText] = []
        self.particles: List[SmokeParticle] = []
        self._terrain_cache: Optional[pygame.Surface] = None

        # Preload crisp system typography
        pygame.font.init()
        self.font_hero = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 54, bold=True)
        self.font_title = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 34, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 15, bold=True)
        self.font_header = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 14, bold=True)
        self.font_body_bold = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 13, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 13)
        self.font_small = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 12, bold=True)
        self.font_tiny = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 11, bold=True)
        self.font_mono = pygame.font.SysFont("Consolas, Courier New, monospace", 14, bold=True)
        self.font_mono_sm = pygame.font.SysFont("Consolas, Courier New, monospace", 12, bold=True)
        self.font_big_stat = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 24, bold=True)

        self._menu_demo_angle = 0.0
        self._build_terrain_cache()

    def _build_terrain_cache(self):
        """Pre-renders checkered green grass & topographic contour curves for 60 FPS performance."""
        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        tile = 48
        for gx in range(0, config.WINDOW_WIDTH, tile):
            for gy in range(0, config.WINDOW_HEIGHT, tile):
                even = ((gx // tile) + (gy // tile)) % 2 == 0
                col = config.COLOR_GRASS_LIGHT if even else config.COLOR_GRASS_DARK
                pygame.draw.rect(surf, col, (gx, gy, tile, tile))

        # Topographic contour curves (subtle ambient hills)
        for idx in range(5):
            offset = idx * 14
            pygame.draw.arc(surf, config.COLOR_CONTOUR, (-140 - offset, -90 - offset, 430 + offset * 2, 340 + offset * 2), 4.4, 6.28, 2)
            pygame.draw.arc(surf, config.COLOR_CONTOUR, (-110 - offset, 520 - offset, 460 + offset * 2, 360 + offset * 2), 0.1, 1.9, 2)
            pygame.draw.arc(surf, config.COLOR_CONTOUR, (640 - offset, 500 - offset, 460 + offset * 2, 380 + offset * 2), 1.6, 3.6, 2)
            pygame.draw.arc(surf, config.COLOR_CONTOUR, (760 - offset, -80 - offset, 420 + offset * 2, 320 + offset * 2), 2.5, 4.7, 2)

        self._terrain_cache = surf

    def add_floating_text(self, text: str, x: float, y: float, color: Tuple[int, int, int]):
        self.floating_texts.append(FloatingText(text, x, y, color))

    def add_touchdown_smoke(self, x: float, y: float):
        for _ in range(10):
            self.particles.append(SmokeParticle(x, y))

    def update_vfx(self, dt: float):
        self.pulse_phase = (self.pulse_phase + dt * 4.5) % (2.0 * math.pi)
        self._menu_demo_angle = (self._menu_demo_angle + dt * 0.45) % (2.0 * math.pi)
        self.floating_texts = [f for f in self.floating_texts if f.update(dt)]
        self.particles = [p for p in self.particles if p.update(dt)]

    # =========================================================================
    # SHARED TOP STATUS & AIRBASE CANVAS HELPERS
    # =========================================================================

    def _draw_top_hud_bar(
        self,
        landed_count: int,
        score_label: str,
        score_val: int,
        mysql_ok: bool,
        ai_ready: bool,
        extra_text: str = "",
        show_status_box: bool = True,
    ):
        pygame.draw.rect(self.screen, config.COLOR_TOPBAR_BG, (0, 0, config.WINDOW_WIDTH, config.TOP_BAR_HEIGHT))
        pygame.draw.line(self.screen, config.COLOR_TOPBAR_BORDER, (0, config.TOP_BAR_HEIGHT), (config.WINDOW_WIDTH, config.TOP_BAR_HEIGHT), 2)

        l_surf = self.font_mono.render(f"AIRCRAFT LANDED: {landed_count:05d}", True, (228, 240, 212))
        self.screen.blit(l_surf, (22, 16))

        s_col = config.COLOR_WHITE if score_val >= 0 else config.COLOR_CRITICAL_RED
        s_surf = self.font_mono.render(f"{score_label}: {score_val:05d}", True, s_col)
        self.screen.blit(s_surf, (268, 16))

        if extra_text:
            e_surf = self.font_mono_sm.render(extra_text, True, config.COLOR_CYAN)
            self.screen.blit(e_surf, (430, 18))

        if show_status_box:
            box = pygame.Rect(config.WINDOW_WIDTH - 235, 10, 215, 62)
            pygame.draw.rect(self.screen, (20, 34, 52), box, border_radius=8)
            pygame.draw.rect(self.screen, config.COLOR_CYAN, box, 1, border_radius=8)

            db_txt = "MYSQL CONNECTED" if mysql_ok else "SQLITE FALLBACK"
            db_col = config.COLOR_PRIMARY_GREEN if mysql_ok else config.COLOR_WARN_AMBER
            self.screen.blit(self.font_tiny.render(db_txt, True, db_col), (box.x + 14, box.y + 11))

            ai_txt = "AI AGENT READY" if ai_ready else "UTILITY AGENT READY"
            ai_col = config.COLOR_PRIMARY_GREEN if ai_ready else config.COLOR_CYAN
            self.screen.blit(self.font_tiny.render(ai_txt, True, ai_col), (box.x + 14, box.y + 34))

    def _draw_airbase_tarmac_and_runways(
        self,
        airbase: Airbase,
        hovered_rwy: Optional[str] = None,
        drag_valid: bool = True,
        active_ac: Optional[Aircraft] = None,
    ):
        """Draws the concrete airbase pad, Helipad (H), and 2-4 active runways."""
        is_multi_runway = len(airbase.runways) >= 3
        if is_multi_runway:
            tarmac_pts = [
                (165, 180), (675, 180), (695, 215), (695, 490),
                (595, 605), (205, 605), (165, 510),
            ]
            hx, hy, hr, h_ring, h_font = 202, 470, 24, 19, self.font_big_stat
        else:
            tarmac_pts = [
                (175, 195), (655, 195), (680, 225), (680, 420),
                (375, 600), (205, 580), (175, 490),
            ]
            hx, hy, hr, h_ring, h_font = 235, 455, 32, 26, self.font_title

        pygame.draw.polygon(self.screen, config.COLOR_TARMAC_BORDER, [(x + 4, y + 5) for x, y in tarmac_pts])
        pygame.draw.polygon(self.screen, config.COLOR_TARMAC, tarmac_pts)
        pygame.draw.polygon(self.screen, config.COLOR_TARMAC_BORDER, tarmac_pts, 2)

        # Helipad (H)
        pygame.draw.circle(self.screen, (72, 70, 66), (hx, hy), hr)
        pygame.draw.circle(self.screen, config.COLOR_HELIPAD_RING, (hx, hy), h_ring, 3)
        h_lbl = h_font.render("H", True, config.COLOR_HELIPAD_RING)
        self.screen.blit(h_lbl, h_lbl.get_rect(center=(hx, hy)))

        # Draw each runway cleanly along its angle
        for rwy in airbase.runways.values():
            self._draw_single_runway(
                rwy,
                is_hovered=(hovered_rwy == rwy.id),
                drag_valid=drag_valid,
                active_ac=active_ac,
            )

    def _draw_single_runway(
        self,
        rwy,
        is_hovered: bool = False,
        drag_valid: bool = True,
        active_ac: Optional[Aircraft] = None,
    ):
        """Draws an asphalt runway strip with markings, threshold keys, and status badge."""
        half_w = 18.0
        nx, ny = -rwy.uy * half_w, rwy.ux * half_w
        corners = [
            (rwy.start_x + nx, rwy.start_y + ny),
            (rwy.end_x + nx, rwy.end_y + ny),
            (rwy.end_x - nx, rwy.end_y - ny),
            (rwy.start_x - nx, rwy.start_y - ny),
        ]

        compat_state: Optional[bool] = None
        if active_ac is not None and rwy.status == RunwayStatus.AVAILABLE:
            compat_state = rwy.supports_aircraft(active_ac.min_runway_length_m)

        # Highlight glow if hovering during drag, or compatibility ring when an aircraft is selected
        if is_hovered or compat_state is not None:
            if is_hovered:
                glow_col = config.COLOR_PRIMARY_GREEN if drag_valid else config.COLOR_CRITICAL_RED
                border_w, pad = 3, 5.0
            elif compat_state:
                glow_col = config.COLOR_PRIMARY_GREEN
                border_w, pad = 2, 4.0
            else:
                glow_col = config.COLOR_WARN_AMBER
                border_w, pad = 2, 4.0

            g_nx, g_ny = -rwy.uy * (half_w + pad), rwy.ux * (half_w + pad)
            g_corners = [
                (rwy.start_x + g_nx, rwy.start_y + g_ny),
                (rwy.end_x + g_nx, rwy.end_y + g_ny),
                (rwy.end_x - g_nx, rwy.end_y - g_ny),
                (rwy.start_x - g_nx, rwy.start_y - g_ny),
            ]
            pygame.draw.polygon(self.screen, glow_col, g_corners, border_w)

        pygame.draw.polygon(self.screen, config.COLOR_RUNWAY_ASPHALT, corners)
        pygame.draw.polygon(self.screen, (210, 210, 200), corners, 1)

        # Threshold piano keys (both ends)
        for end_t in (8.0, rwy.pixel_length - 18.0):
            for offset in (-10.0, -4.0, 2.0, 8.0):
                px = rwy.start_x + rwy.ux * end_t - rwy.uy * offset
                py = rwy.start_y + rwy.uy * end_t + rwy.ux * offset
                qx = px + rwy.ux * 10.0
                qy = py + rwy.uy * 10.0
                pygame.draw.line(self.screen, config.COLOR_RUNWAY_MARKING, (px, py), (qx, qy), 2)

        # Centerline dashes
        t = 28.0
        while t < rwy.pixel_length - 28.0:
            p1 = (rwy.start_x + rwy.ux * t, rwy.start_y + rwy.uy * t)
            p2 = (rwy.start_x + rwy.ux * (t + 14.0), rwy.start_y + rwy.uy * (t + 14.0))
            pygame.draw.line(self.screen, config.COLOR_RUNWAY_MARKING, p1, p2, 2)
            t += 26.0

        # If Unavailable / Maintenance, draw hazard stripes across runway
        if rwy.status in (RunwayStatus.UNAVAILABLE, RunwayStatus.UNDER_MAINTENANCE):
            s_t = 32.0
            while s_t < rwy.pixel_length - 32.0:
                cx = rwy.start_x + rwy.ux * s_t
                cy = rwy.start_y + rwy.uy * s_t
                pygame.draw.line(
                    self.screen, config.COLOR_WARN_AMBER,
                    (cx - rwy.uy * 14, cy + rwy.ux * 14),
                    (cx + rwy.uy * 14, cy - rwy.ux * 14), 3
                )
                s_t += 28.0

        # Status badge pill above runway start/mid
        if rwy.status == RunwayStatus.AVAILABLE:
            if compat_state is False:
                st_col = config.COLOR_WARN_AMBER
                st_txt = f"{rwy.id} ({rwy.length_m}m) TOO SHORT"
            else:
                st_col = config.COLOR_PRIMARY_GREEN
                st_txt = f"{rwy.id} ({rwy.length_m}m) FREE"
        elif rwy.status == RunwayStatus.OCCUPIED:
            st_col = config.COLOR_CRITICAL_RED
            st_txt = f"{rwy.id} OCCUPIED [{rwy.current_aircraft}]"
        else:
            st_col = config.COLOR_WARN_AMBER
            st_txt = f"{rwy.id} {rwy.status.upper()}"

        lbl = self.font_tiny.render(st_txt, True, st_col)
        bx = int(rwy.center_x - lbl.get_width() // 2 - 6)
        by = int(rwy.center_y - 34)
        pill = pygame.Rect(bx, by, lbl.get_width() + 12, 18)
        pygame.draw.rect(self.screen, (14, 24, 38), pill, border_radius=4)
        pygame.draw.rect(self.screen, st_col, pill, 1, border_radius=4)
        self.screen.blit(lbl, (bx + 6, by + 2))

    def _draw_plane_sprite(
        self,
        x: float,
        y: float,
        heading_deg: float,
        color: Tuple[int, int, int],
        scale: float = 1.0,
    ):
        """Draws crisp top-down aircraft silhouette matching mockup style."""
        rad = math.radians(heading_deg)
        c, s = math.cos(rad), math.sin(rad)

        def pt(fx: float, fy: float) -> Tuple[int, int]:
            fx *= scale
            fy *= scale
            return (int(x + fx * c - fy * s), int(y + fx * s + fy * c))

        pts = [
            pt(13, 0), pt(5, 3), pt(-1, 14), pt(-4, 13), pt(-5, 3),
            pt(-11, 6), pt(-13, 0), pt(-11, -6), pt(-5, -3),
            pt(-4, -13), pt(-1, -14), pt(5, -3),
        ]
        pygame.draw.polygon(self.screen, color, pts)
        pygame.draw.polygon(self.screen, (22, 30, 40), pts, 2)

    def _draw_dotted_line(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        color: Tuple[int, int, int],
        spacing: int = 9,
        radius: int = 2,
    ):
        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist < 6:
            return
        steps = max(1, int(dist // spacing))
        for i in range(0, steps + 1, 2):
            t = i / float(steps)
            px = int(x1 + t * (x2 - x1))
            py = int(y1 + t * (y2 - y1))
            pygame.draw.circle(self.screen, color, (px, py), radius)

    # =========================================================================
    # SCREEN 1: MAIN MENU
    # =========================================================================

    def render_main_menu(self, airbase: Airbase, global_stats: Dict[str, int], mysql_ok: bool, ai_ready: bool):
        self.screen.blit(self._terrain_cache, (0, 0))
        self._draw_airbase_tarmac_and_runways(airbase)

        # Ambient decorative orbiting aircraft on Main Menu (matching Mockup 1)
        demo_planes = [
            (460 + 170 * math.cos(self._menu_demo_angle), 185 + 35 * math.sin(self._menu_demo_angle), (205, 45, 50), True, "BG-101 12%"),
            (215, 290, (225, 175, 40), False, ""),
            (175, 445, (215, 222, 232), False, ""),
            (250, 565, (205, 215, 225), False, ""),
            (415, 470, (68, 128, 225), False, ""),
            (785, 360, (195, 75, 165), False, ""),
        ]
        for px, py, col, is_em, label in demo_planes:
            if is_em:
                pulse_r = int(26 + 5 * math.sin(self.pulse_phase))
                pygame.draw.circle(self.screen, (225, 50, 56), (int(px), int(py)), pulse_r, 3)
                pygame.draw.circle(self.screen, (225, 50, 56), (int(px), int(py)), pulse_r - 9, 2)
                lbl_s = self.font_small.render(label, True, (255, 110, 110))
                self.screen.blit(lbl_s, (int(px + 28), int(py - 20)))
            self._draw_plane_sprite(px, py, 20.0 if not is_em else 0.0, col, scale=1.1)

        # Soft dark vignette overlay behind center menu
        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (10, 20, 30, 105), (0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.screen.blit(overlay, (0, 0))

        self._draw_top_hud_bar(
            landed_count=global_stats.get("aircraft_landed", 0),
            score_label="HI-SCORE",
            score_val=global_stats.get("hi_score", 0),
            mysql_ok=mysql_ok,
            ai_ready=ai_ready,
        )

        # Hero Title: SKYATC (white) + AI (cyan)
        cx = config.WINDOW_WIDTH // 2
        t1 = self.font_hero.render("SKYATC ", True, config.COLOR_WHITE)
        t2 = self.font_hero.render("AI", True, config.COLOR_CYAN)
        total_w = t1.get_width() + t2.get_width()
        tx = cx - total_w // 2
        self.screen.blit(t1, (tx, 175))
        self.screen.blit(t2, (tx + t1.get_width(), 175))

        sub = self.font_sub.render("INTELLIGENT RUNWAY MANAGEMENT", True, config.COLOR_WHITE)
        self.screen.blit(sub, sub.get_rect(center=(cx, 250)))

        footer = self.font_tiny.render(
            "CSE 3202 AI Sessional  |  Md. Arif Shahriar & Ashikur Rahman  |  Gemini 2.5 Flash + Utility Agent",
            True, config.COLOR_TEXT_MUTED,
        )
        self.screen.blit(footer, footer.get_rect(center=(cx, config.WINDOW_HEIGHT - 28)))

    # =========================================================================
    # SCREEN 2: SELECT LEVEL (01 - 20 SEQUENTIAL)
    # =========================================================================

    def render_level_select(
        self,
        airbase: Airbase,
        global_stats: Dict[str, int],
        progression: Dict[str, Any],
        selected_level: int,
        demo_unlock_all: bool,
        mysql_ok: bool,
        ai_ready: bool,
    ):
        self.screen.blit(self._terrain_cache, (0, 0))
        self._draw_airbase_tarmac_and_runways(airbase)

        dim = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 18, 28, 170))
        self.screen.blit(dim, (0, 0))

        self._draw_top_hud_bar(
            landed_count=global_stats.get("aircraft_landed", 0),
            score_label="HI-SCORE",
            score_val=global_stats.get("hi_score", 0),
            mysql_ok=mysql_ok,
            ai_ready=ai_ready,
        )

        cx = config.WINDOW_WIDTH // 2
        t_surf = self.font_title.render("SELECT LEVEL", True, config.COLOR_CYAN)
        self.screen.blit(t_surf, t_surf.get_rect(center=(cx, 92)))
        s_surf = self.font_sub.render("CHOOSE YOUR AIRBASE CHALLENGE", True, config.COLOR_WHITE)
        self.screen.blit(s_surf, s_surf.get_rect(center=(cx, 128)))

        # Tier Row Labels (left of 5-column level grid)
        tiers = [
            ("EASY", "(2 RUNWAYS)", config.COLOR_PRIMARY_GREEN, 190),
            ("MEDIUM", "(2 RUNWAYS)", (245, 220, 90), 280),
            ("HARD", "(3 RUNWAYS)", config.COLOR_WARN_AMBER, 370),
            ("EXPERT", "(4 RUNWAYS)", config.COLOR_CRITICAL_RED, 460),
        ]
        for label, sub_lbl, col, ry in tiers:
            row_bg = pygame.Rect(185, ry - 8, 625, 80)
            pygame.draw.rect(self.screen, (18, 30, 44, 210), row_bg, border_radius=10)
            pygame.draw.rect(self.screen, (48, 72, 98), row_bg, 1, border_radius=10)

            l_surf = self.font_header.render(label, True, col)
            self.screen.blit(l_surf, (205, ry + 10))
            sub_s = self.font_tiny.render(sub_lbl, True, config.COLOR_TEXT_MUTED)
            self.screen.blit(sub_s, (205, ry + 32))

        # Right-side LEVEL STATUS details panel
        panel = pygame.Rect(840, 220, 355, 235)
        pygame.draw.rect(self.screen, (20, 34, 52), panel, border_radius=10)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, panel, 2, border_radius=10)

        lvl_cfg = config.LEVEL_CONFIGS[selected_level]
        lvl_best = progression.get("best_by_level", {}).get(selected_level, {})
        best_score = lvl_best.get("best_score", 0)
        emerg_cnt = lvl_best.get("emergencies", 0)
        is_unlocked = demo_unlock_all or (selected_level <= progression.get("max_unlocked", 1))

        self.screen.blit(self.font_header.render(f"LEVEL {selected_level:02d} STATUS:", True, config.COLOR_PRIMARY_GREEN), (panel.x + 20, panel.y + 18))
        rows = [
            (f"DIFFICULTY: {lvl_cfg['difficulty']} ({lvl_cfg['runway_count']} RUNWAYS)", config.COLOR_WHITE),
            (f"TARGET LANDINGS: {lvl_cfg['total_aircraft']} AIRCRAFT", config.COLOR_CYAN),
            (f"CURRENT BEST: {best_score} PTS", (245, 215, 65)),
            (f"EMERGENCIES HANDLED: {emerg_cnt}", config.COLOR_WHITE),
            (f"WIND: {int(lvl_cfg['wind_speed_kts'])} KTS | HEAVY JETS: {int(lvl_cfg['heavy_chance']*100)}%", config.COLOR_TEXT_MUTED),
            (f"ACCESS: {'UNLOCKED' if is_unlocked else 'LOCKED (Complete prev level)'}", config.COLOR_PRIMARY_GREEN if is_unlocked else config.COLOR_CRITICAL_RED),
        ]
        ry = panel.y + 52
        for txt, col in rows:
            self.screen.blit(self.font_small.render(txt, True, col), (panel.x + 20, ry))
            ry += 28

    # =========================================================================
    # SCREEN 3: GAMEPLAY SIMULATION
    # =========================================================================

    def render_simulation(
        self,
        airbase: Airbase,
        agent: ATCAgent,
        level_mgr: LevelManager,
        selected_ac: Optional[Aircraft],
        override_mode: bool,
        drag_state: Optional[Dict[str, Any]],
        is_paused: bool,
        sim_speed: float,
        modal_state: Optional[Dict[str, Any]],
        muted: bool,
    ):
        self.screen.blit(self._terrain_cache, (0, 0))

        # Highlight hovered runway if player is dragging, or compatible runways when holding plane selected
        hovered_rwy = drag_state.get("hovered_runway") if drag_state else None
        drag_valid = drag_state.get("is_valid", True) if drag_state else True
        active_ac = (
            drag_state.get("aircraft")
            if drag_state
            else (selected_ac if selected_ac and selected_ac.status == FlightStatus.HOLDING else None)
        )
        self._draw_airbase_tarmac_and_runways(
            airbase,
            hovered_rwy=hovered_rwy,
            drag_valid=drag_valid,
            active_ac=active_ac,
        )

        # Draw perimeter holding orbit circles when any aircraft is holding
        drawn_orbits = set()
        for ac in airbase.aircraft_fleet:
            if ac.status == FlightStatus.HOLDING:
                okey = (int(ac.orbit_x), int(ac.orbit_y), int(ac.orbit_radius))
                if okey not in drawn_orbits:
                    drawn_orbits.add(okey)
                    ring_w = 2 if selected_ac is ac else 1
                    pygame.draw.circle(self.screen, (135, 215, 165), (okey[0], okey[1]), okey[2], ring_w)
                    h_tag = self.font_tiny.render("HOLD", True, (150, 226, 178))
                    self.screen.blit(h_tag, (okey[0] + okey[2] - 10, okey[1] - okey[2] - 8))

        # Draw subtle AI-recommended route preview lines while planes await clearance
        plan = agent.ui_state.get("current_plan")
        if plan and not drag_state:
            for item in plan.get("assignments", [])[:3]:
                if item.get("action") != "AUTHORIZE_LANDING" or not item.get("assigned_runway"):
                    continue
                pac = airbase.get_aircraft(item["flight_id"])
                rwy = airbase.runways.get(item["assigned_runway"])
                if pac and pac.status == FlightStatus.HOLDING and rwy and rwy.is_available():
                    p_col = (240, 120, 125) if pac.is_emergency() else (110, 210, 235)
                    self._draw_dotted_line((pac.x, pac.y), (rwy.approach_x, rwy.approach_y), p_col, spacing=18, radius=1)
                    pygame.draw.circle(self.screen, p_col, (int(rwy.approach_x), int(rwy.approach_y)), 5, 1)

        # Draw aircraft trails & approach paths
        for ac in airbase.aircraft_fleet:
            if not ac.is_active_in_airspace():
                continue
            if len(ac.trail) >= 2:
                for idx in range(len(ac.trail) - 1):
                    self._draw_dotted_line(ac.trail[idx], ac.trail[idx + 1], (210, 228, 208), spacing=10)

            if ac.status in (FlightStatus.INTERCEPT, FlightStatus.APPROACHING) and ac.assigned_runway:
                rwy = airbase.runways.get(ac.assigned_runway)
                if rwy:
                    path_col = config.COLOR_CRITICAL_RED if ac.is_emergency() else config.COLOR_CYAN
                    target = (rwy.approach_x, rwy.approach_y) if ac.status == FlightStatus.INTERCEPT else (rwy.start_x, rwy.start_y)
                    self._draw_dotted_line((ac.x, ac.y), target, path_col, spacing=8)

        # Draw Drag-and-Draw Manual Override Preview Path
        if drag_state and drag_state.get("aircraft"):
            src_ac = drag_state["aircraft"]
            mx, my = drag_state["mouse_pos"]
            line_col = config.COLOR_PRIMARY_GREEN if drag_valid else config.COLOR_CRITICAL_RED
            self._draw_dotted_line((src_ac.x, src_ac.y), (mx, my), line_col, spacing=7)
            pygame.draw.circle(self.screen, line_col, (mx, my), 7, 2)
            if drag_state.get("reason"):
                tip = self.font_tiny.render(drag_state["reason"], True, line_col)
                tip_w = tip.get_width() + 10
                tx = mx + 12
                if tx + tip_w > config.CANVAS_WIDTH - 6:
                    tx = max(6, mx - 12 - tip_w)
                ty = max(config.TOP_BAR_HEIGHT + 4, min(config.WINDOW_HEIGHT - 54, my - 13))
                tip_rect = pygame.Rect(tx, ty, tip_w, 19)
                pygame.draw.rect(self.screen, (14, 24, 38), tip_rect, border_radius=4)
                pygame.draw.rect(self.screen, line_col, tip_rect, 1, border_radius=4)
                self.screen.blit(tip, (tip_rect.x + 5, tip_rect.y + 2))

        # Touchdown smoke particles
        for p in self.particles:
            p.draw(self.screen)

        # Aircraft sprites + emergency circles + fuel % badges
        for ac in airbase.aircraft_fleet:
            if not ac.is_active_in_airspace():
                continue
            self._draw_gameplay_aircraft(ac, is_selected=(selected_ac is ac))

        # Floating score popups
        for f in self.floating_texts:
            f.draw(self.screen, self.font_body_bold)

        # Top HUD Bar
        lvl_cfg = level_mgr.level_cfg
        wind_txt = f"LVL {level_mgr.current_level:02d} ({lvl_cfg['difficulty']}) | WIND {int(airbase.wind_speed_kts)}KT | {airbase.weather}"
        self._draw_top_hud_bar(
            landed_count=len(airbase.flight_history),
            score_label="SCORE",
            score_val=agent.reward_system.cumulative_reward,
            mysql_ok=True,
            ai_ready=True,
            extra_text=wind_txt,
            show_status_box=False,
        )

        # Event Alert Toast Banner inside Left Canvas
        if level_mgr.active_banner:
            self._draw_event_banner(level_mgr.active_banner)

        # Compact bottom controls legend bar inside radar canvas
        ctrl_rect = pygame.Rect(14, config.WINDOW_HEIGHT - 30, config.CANVAS_WIDTH - 28, 24)
        pygame.draw.rect(self.screen, (14, 24, 38), ctrl_rect, border_radius=5)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, ctrl_rect, 1, border_radius=5)
        ctrl_prefix = self.font_tiny.render("CONTROLS:", True, config.COLOR_CYAN)
        ctrl_body = self.font_tiny.render(
            "Drag Plane -> Runway  |  Click Plane -> Click Runway  |  [SPACE] Accept AI  |  [P] Pause  |  [1-4] Runway  |  [H] Hold",
            True, config.COLOR_TEXT_MUTED,
        )
        self.screen.blit(ctrl_prefix, (ctrl_rect.x + 12, ctrl_rect.y + 4))
        self.screen.blit(ctrl_body, (ctrl_rect.x + 84, ctrl_rect.y + 4))

        # Right Sidebar (SKYATC AI Panel)
        self._render_gameplay_sidebar(airbase, agent, level_mgr, selected_ac, override_mode)

        # Optional Modal Overlay (Pause / Level Complete / Crash)
        if modal_state:
            self._render_modal_overlay(modal_state)
        elif is_paused:
            self._render_pause_overlay()

    def _draw_gameplay_aircraft(self, ac: Aircraft, is_selected: bool):
        ax, ay = int(ac.x), int(ac.y)
        is_em = ac.is_emergency()

        if is_em:
            pulse_r = int(23 + 4 * math.sin(self.pulse_phase * 1.4))
            pygame.draw.circle(self.screen, config.COLOR_CRITICAL_RED, (ax, ay), pulse_r, 3)
            pygame.draw.circle(self.screen, config.COLOR_CRITICAL_RED, (ax, ay), pulse_r - 8, 1)
            # Exclamation markers matching mockup
            for ex, ey in ((ax - 24, ay - 20), (ax + 22, ay + 18)):
                pygame.draw.circle(self.screen, config.COLOR_CRITICAL_RED, (ex, ey), 7)
                self.screen.blit(self.font_tiny.render("!", True, config.COLOR_WHITE), (ex - 2, ey - 7))
            plane_col = (218, 45, 52)
        elif ac.fuel_level < 40.0:
            plane_col = (232, 178, 38)
        elif ac.aircraft_size == "HEAVY":
            plane_col = (72, 138, 228)
        else:
            plane_col = (224, 232, 240)

        if is_selected:
            pygame.draw.circle(self.screen, config.COLOR_CYAN, (ax, ay), 26, 2)

        scale = 1.25 if ac.aircraft_size == "HEAVY" else (0.95 if ac.aircraft_size == "SMALL" else 1.1)
        self._draw_plane_sprite(ac.x, ac.y, ac.heading, plane_col, scale=scale)

        # Crisp compact flight tag (clamped inside left radar canvas)
        tag_col = (255, 115, 115) if is_em else config.COLOR_WHITE
        stage_lbl = "HOLD" if ac.status == FlightStatus.HOLDING else ("LAND" if ac.status == FlightStatus.ROLLING_LAND else "APP")
        tag_txt = f"{ac.flight_id} {int(ac.fuel_level)}% [{stage_lbl}]"
        if ac.aircraft_size == "HEAVY":
            tag_txt += " [HVY]"
        lbl = self.font_tiny.render(tag_txt, True, tag_col)
        bg_w = lbl.get_width() + 8
        tag_x = ax + 16
        if tag_x + bg_w > config.CANVAS_WIDTH - 6:
            tag_x = max(6, ax - 16 - bg_w)
        tag_y = max(config.TOP_BAR_HEIGHT + 4, min(config.WINDOW_HEIGHT - 54, ay - 22))
        bg = pygame.Rect(tag_x, tag_y, bg_w, 16)
        pygame.draw.rect(self.screen, (14, 24, 38), bg, border_radius=3)
        self.screen.blit(lbl, (bg.x + 4, bg.y + 1))

    def _draw_event_banner(self, banner: Dict[str, Any]):
        bw, bh = 480, 44
        bx = (config.CANVAS_WIDTH - bw) // 2
        by = 62
        b_type = banner.get("type", "NORMAL")
        border = config.COLOR_CRITICAL_RED if b_type == "EMERGENCY" else config.COLOR_CYAN
        bg = (64, 18, 24) if b_type == "EMERGENCY" else (16, 30, 48)
        pygame.draw.rect(self.screen, bg, (bx, by, bw, bh), border_radius=6)
        pygame.draw.rect(self.screen, border, (bx, by, bw, bh), 2, border_radius=6)
        self.screen.blit(self.font_small.render(banner["title"], True, border), (bx + 14, by + 5))
        self.screen.blit(self.font_tiny.render(banner["message"], True, config.COLOR_WHITE), (bx + 14, by + 23))

    def _render_gameplay_sidebar(
        self,
        airbase: Airbase,
        agent: ATCAgent,
        level_mgr: LevelManager,
        selected_ac: Optional[Aircraft],
        override_mode: bool,
    ):
        sx = config.SIDEBAR_X
        sy = config.TOP_BAR_HEIGHT
        sw = config.SIDEBAR_WIDTH
        sh = config.WINDOW_HEIGHT - sy

        pygame.draw.rect(self.screen, config.COLOR_SIDEBAR_BG, (sx, sy, sw, sh))
        pygame.draw.line(self.screen, config.COLOR_CARD_BORDER, (sx, sy), (sx, config.WINDOW_HEIGHT), 2)

        # Header: SKYATC AI + Active Mode Badge
        t1 = self.font_title.render("SKYATC ", True, config.COLOR_WHITE)
        t2 = self.font_title.render("AI", True, config.COLOR_CYAN)
        self.screen.blit(t1, (sx + 20, sy + 8))
        self.screen.blit(t2, (sx + 20 + t1.get_width(), sy + 8))

        mode_str = f"Mode: {agent.ui_state.get('mode_label', 'Local Utility Fallback')}"
        is_api = "LLM API" in mode_str
        m_col = config.COLOR_PRIMARY_GREEN if is_api else config.COLOR_CYAN
        self.screen.blit(self.font_tiny.render(mode_str, True, m_col), (sx + 22, sy + 48))

        prog_str = f"Progress: {len(airbase.flight_history)}/{level_mgr.target_aircraft} Landed"
        self.screen.blit(self.font_tiny.render(prog_str, True, config.COLOR_TEXT_MUTED), (sx + 225, sy + 48))

        # 1. INCOMING PRIORITY QUEUE
        self.screen.blit(self.font_header.render("INCOMING PRIORITY QUEUE", True, config.COLOR_WHITE), (sx + 20, sy + 68))
        queue_box = pygame.Rect(sx + 16, sy + 90, sw - 32, 232)
        pygame.draw.rect(self.screen, config.COLOR_CARD_DARK, queue_box, border_radius=8)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, queue_box, 1, border_radius=8)

        pending_ranked = airbase.get_ranked_pending_aircraft()
        if not pending_ranked:
            self.screen.blit(self.font_body.render("Queue clear — monitoring sector...", True, config.COLOR_TEXT_DIM), (queue_box.x + 14, queue_box.y + 18))
        else:
            cy = queue_box.y + 8
            for ac in pending_ranked[:4]:
                bd = ac.get_priority_breakdown()
                is_em = ac.is_emergency()
                if is_em:
                    c_bg, c_border = (145, 34, 42), (245, 76, 82)
                elif ac.fuel_level < 42.0:
                    c_bg, c_border = (158, 96, 18), (240, 165, 45)
                else:
                    c_bg, c_border = (62, 86, 112), (96, 128, 162)

                card_rect = pygame.Rect(queue_box.x + 8, cy, queue_box.w - 16, 48)
                pygame.draw.rect(self.screen, c_bg, card_rect, border_radius=6)
                is_sel = selected_ac is ac
                pygame.draw.rect(self.screen, config.COLOR_WHITE if is_sel else c_border, card_rect, 2 if is_sel else 1, border_radius=6)

                line1 = f"{ac.flight_id} | {int(ac.fuel_level)}% | {ac.model} ({ac.aircraft_size[0]})"
                self.screen.blit(self.font_body_bold.render(line1, True, config.COLOR_WHITE), (card_rect.x + 10, card_rect.y + 5))
                line2 = f"{bd['status_tag']}  •  Dist: {ac.distance_nm} NM"
                self.screen.blit(self.font_tiny.render(line2, True, (240, 240, 240)), (card_rect.x + 10, card_rect.y + 25))
                cy += 54

        # 2. AI RECOMMENDED PLAN + 1-line Explainable AI Reason Badge
        plan_box = pygame.Rect(sx + 16, sy + 334, sw - 32, 114)
        pygame.draw.rect(self.screen, config.COLOR_CARD_DARK, plan_box, border_radius=8)
        pygame.draw.rect(self.screen, config.COLOR_CYAN, plan_box, 1, border_radius=8)
        self.screen.blit(self.font_header.render("AI RECOMMENDED PLAN", True, config.COLOR_WHITE), (plan_box.x + 14, plan_box.y + 8))

        plan_lines = agent.ui_state.get("plan_lines", [])
        py = plan_box.y + 30
        if not plan_lines:
            self.screen.blit(self.font_body.render("Awaiting next arrival request...", True, config.COLOR_TEXT_DIM), (plan_box.x + 14, py))
        else:
            for idx, line in enumerate(plan_lines[:2]):
                col = config.COLOR_CYAN if idx == 0 else config.COLOR_PRIMARY_GREEN
                self.screen.blit(self.font_body_bold.render(line, True, col), (plan_box.x + 14, py))
                py += 21

        # Explainable AI Reason Badge
        reason_txt = agent.ui_state.get("reason_badge", "")
        badge_rect = pygame.Rect(plan_box.x + 10, plan_box.bottom - 30, plan_box.w - 20, 22)
        pygame.draw.rect(self.screen, (26, 46, 72), badge_rect, border_radius=4)
        short_reason = (reason_txt[:46] + "...") if len(reason_txt) > 49 else reason_txt
        self.screen.blit(self.font_tiny.render(f"Reason: {short_reason}", True, (245, 225, 130)), (badge_rect.x + 8, badge_rect.y + 4))

        # 3. 10s DECISION TIMER
        timer_box = pygame.Rect(sx + 16, sy + 458, sw - 32, 62)
        pygame.draw.rect(self.screen, config.COLOR_CARD_DARK, timer_box, border_radius=8)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, timer_box, 1, border_radius=8)

        top_pending = pending_ranked[0] if pending_ranked else None
        t_rem = top_pending.hitl_decision_timer if top_pending else config.HITL_TIMEOUT_SECONDS
        t_max = top_pending.hitl_initial_timer if top_pending else config.HITL_TIMEOUT_SECONDS
        pct = max(0.0, min(1.0, t_rem / max(0.1, t_max)))

        self.screen.blit(self.font_header.render("10s DECISION TIMER", True, config.COLOR_WHITE), (timer_box.x + 95, timer_box.y + 7))
        bar_rect = pygame.Rect(timer_box.x + 14, timer_box.y + 32, timer_box.w - 72, 20)
        pygame.draw.rect(self.screen, (34, 48, 68), bar_rect, border_radius=5)
        bar_col = config.COLOR_PRIMARY_GREEN if pct > 0.5 else (config.COLOR_WARN_AMBER if pct > 0.25 else config.COLOR_CRITICAL_RED)
        pygame.draw.rect(self.screen, bar_col, (bar_rect.x, bar_rect.y, int(bar_rect.w * pct), bar_rect.h), border_radius=5)
        self.screen.blit(self.font_mono_sm.render(f"{int(math.ceil(t_rem)):02d}s", True, config.COLOR_WHITE), (bar_rect.x + 8, bar_rect.y + 3))
        self.screen.blit(self.font_mono_sm.render(f"{int(pct * 100)}%", True, config.COLOR_WHITE), (bar_rect.right + 10, bar_rect.y + 3))

        # Quick Manual Override hint at bottom of sidebar
        target_fid = selected_ac.flight_id if selected_ac else (top_pending.flight_id if top_pending else "None")
        ov_title = f"OVERRIDE ({target_fid}) — Drag plane or pick runway:" if override_mode else f"QUICK ASSIGN ({target_fid}) / Drag-and-Draw:"
        ov_col = config.COLOR_WARN_AMBER if override_mode else config.COLOR_TEXT_MUTED
        self.screen.blit(self.font_tiny.render(ov_title, True, ov_col), (sx + 18, sy + 596))

