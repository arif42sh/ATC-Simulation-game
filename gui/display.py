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

