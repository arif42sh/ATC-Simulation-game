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
from environment.aircraft import Aircraft, FlightStatus, EmergencyType
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
        self.show_trajectory: bool = True

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
        """Build a subdued radar-map background that keeps aircraft and runways prominent."""
        surf = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        surf.fill((49, 82, 48))
        tile = 96
        for gx in range(0, config.WINDOW_WIDTH, tile):
            for gy in range(0, config.WINDOW_HEIGHT, tile):
                if ((gx // tile) + (gy // tile)) % 2 == 0:
                    pygame.draw.rect(surf, (51, 85, 50), (gx, gy, tile, tile))

        # Fine, low-contrast map grid instead of a high-contrast checkerboard.
        grid = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        for gx in range(0, config.WINDOW_WIDTH, 96):
            pygame.draw.line(grid, (190, 218, 174, 13), (gx, config.TOP_BAR_HEIGHT), (gx, config.WINDOW_HEIGHT), 1)
        for gy in range(config.TOP_BAR_HEIGHT, config.WINDOW_HEIGHT, 96):
            pygame.draw.line(grid, (190, 218, 174, 13), (0, gy), (config.WINDOW_WIDTH, gy), 1)
        surf.blit(grid, (0, 0))
        self._terrain_cache = surf

    def _draw_vector_star(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        radius: float,
        fill_col: Tuple[int, int, int],
        outline_col: Optional[Tuple[int, int, int]] = None,
    ):
        pts = []
        for i in range(10):
            r = radius if (i % 2 == 0) else (radius * 0.42)
            ang = math.radians(i * 36 - 90)
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        pygame.draw.polygon(surface, fill_col, pts)
        if outline_col:
            pygame.draw.polygon(surface, outline_col, pts, 1)

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
        show_debug_box: bool = False,
        star_ratio: float = 0.0,
        decision_remaining: float = 20.0,
        decision_initial: float = 20.0,
        decision_active: bool = True,
        level_id: int = 1,
    ):
        pygame.draw.rect(self.screen, config.COLOR_TOPBAR_BG, (0, 0, config.WINDOW_WIDTH, config.TOP_BAR_HEIGHT))
        pygame.draw.line(self.screen, config.COLOR_TOPBAR_BORDER, (0, config.TOP_BAR_HEIGHT), (config.WINDOW_WIDTH, config.TOP_BAR_HEIGHT), 2)

        if not show_status_box:
            # 1. Level Badge (X=16)
            lvl_rect = pygame.Rect(16, 9, 82, 30)
            pygame.draw.rect(self.screen, (20, 38, 60), lvl_rect, border_radius=5)
            pygame.draw.rect(self.screen, config.COLOR_CYAN, lvl_rect, 1, border_radius=5)
            lvl_surf = self.font_small.render(f"LVL {level_id:02d}", True, config.COLOR_CYAN)
            self.screen.blit(lvl_surf, (lvl_rect.x + (lvl_rect.w - lvl_surf.get_width()) // 2, lvl_rect.y + 7))

            # 2. Landed Count (X=110)
            l_surf = self.font_mono.render(f"LANDED: {landed_count:02d}", True, (228, 240, 212))
            self.screen.blit(l_surf, (110, 16))

            # 3. Score (X=215)
            s_col = config.COLOR_WHITE if score_val >= 0 else config.COLOR_CRITICAL_RED
            s_surf = self.font_mono.render(f"{score_label}: {score_val:05d}", True, s_col)
            self.screen.blit(s_surf, (215, 16))

            # 4. Live 3-Star Rating Progress Bar (X=325)
            r_lbl = self.font_tiny.render("RATING", True, config.COLOR_TEXT_MUTED)
            self.screen.blit(r_lbl, (325, 18))

            bx, by, bw, bh = 370, 18, 70, 13
            pygame.draw.rect(self.screen, (16, 26, 36), (bx, by, bw, bh), border_radius=4)
            pygame.draw.rect(self.screen, (48, 86, 62), (bx, by, bw, bh), 1, border_radius=4)

            fill_w = int(bw * max(0.0, min(1.0, star_ratio)))
            if fill_w > 0:
                pygame.draw.rect(self.screen, (245, 205, 55), (bx + 1, by + 1, fill_w - 2, bh - 2), border_radius=3)

            # Draw vector stars (no unicode tofu)
            star_gold = (255, 220, 50)
            star_gold_hi = (255, 245, 140)
            star_dim = (24, 38, 34)
            star_dim_out = (60, 95, 78)

            col1 = star_gold if star_ratio >= 0.35 else star_dim
            out1 = star_gold_hi if star_ratio >= 0.35 else star_dim_out
            self._draw_vector_star(self.screen, bx + bw + 10, by + 6, 5.5, col1, out1)

            col2 = star_gold if star_ratio >= 0.70 else star_dim
            out2 = star_gold_hi if star_ratio >= 0.70 else star_dim_out
            self._draw_vector_star(self.screen, bx + bw + 23, by + 6, 5.5, col2, out2)

            col3 = star_gold if star_ratio >= 0.95 else star_dim
            out3 = star_gold_hi if star_ratio >= 0.95 else star_dim_out
            self._draw_vector_star(self.screen, bx + bw + 38, by + 6, 7.0, col3, out3)

            # 5. 20s Decision Countdown Timer Badge (X=515)
            tw, th = 160, 32
            tx, ty = 515, 8
            rem_s = max(0.0, decision_remaining)
            timer_pct = min(1.0, rem_s / max(1.0, decision_initial))

            if not decision_active:
                t_accent = (150, 168, 158)
                t_bg = (24, 34, 29)
            elif rem_s > 10.0:
                t_accent = (45, 215, 160)
                t_bg = (16, 32, 28)
            elif rem_s > 5.0:
                t_accent = (245, 185, 45)
                t_bg = (36, 30, 16)
            else:
                pulse_val = 0.5 + 0.5 * math.sin(self.pulse_phase * 5.0)
                t_accent = (255, int(60 + 60 * pulse_val), int(60 + 60 * pulse_val))
                t_bg = (42, 16, 18)

            pygame.draw.rect(self.screen, t_bg, (tx, ty, tw, th), border_radius=6)
            pygame.draw.rect(self.screen, t_accent, (tx, ty, tw, th), 1, border_radius=6)

            t_text = f"20s TIMER: {int(rem_s):02d}s" if decision_active else "NO ACTIVE CLEARANCE"
            t_surf = self.font_small.render(t_text, True, t_accent)
            self.screen.blit(t_surf, (tx + (tw - t_surf.get_width()) // 2, ty + 5))

            mini_w = int((tw - 16) * timer_pct) if decision_active else 0
            if mini_w > 0:
                pygame.draw.rect(self.screen, t_accent, (tx + 8, ty + 24, mini_w, 3), border_radius=2)

            # 6. Wind & Weather (X=705)
            if extra_text:
                e_surf = self.font_mono_sm.render(extra_text, True, config.COLOR_CYAN)
                self.screen.blit(e_surf, (705, 17))

        else:
            l_surf = self.font_mono.render(f"AIRCRAFT LANDED: {landed_count:05d}", True, (228, 240, 212))
            self.screen.blit(l_surf, (22, 16))

            s_col = config.COLOR_WHITE if score_val >= 0 else config.COLOR_CRITICAL_RED
            s_surf = self.font_mono.render(f"{score_label}: {score_val:05d}", True, s_col)
            self.screen.blit(s_surf, (268, 16))

            if extra_text:
                e_surf = self.font_mono_sm.render(extra_text, True, config.COLOR_CYAN)
                self.screen.blit(e_surf, (430, 18))

            if show_debug_box:
                box = pygame.Rect(config.WINDOW_WIDTH - 235, 10, 215, 62)
                pygame.draw.rect(self.screen, (20, 34, 52), box, border_radius=8)
                pygame.draw.rect(self.screen, config.COLOR_CYAN, box, 1, border_radius=8)

                if mysql_ok:
                    db_txt, db_col = "MYSQL CONNECTED", config.COLOR_PRIMARY_GREEN
                elif config.IS_WEB or config.DB_TYPE.lower() == "memory":
                    db_txt, db_col = "BROWSER STORAGE", config.COLOR_CYAN
                else:
                    db_txt, db_col = "SQLITE FALLBACK", config.COLOR_WARN_AMBER
                self.screen.blit(self.font_tiny.render(db_txt, True, db_col), (box.x + 14, box.y + 11))

                ai_txt = "AI AGENT READY" if ai_ready else "UTILITY AGENT READY"
                ai_col = config.COLOR_PRIMARY_GREEN if ai_ready else config.COLOR_CYAN
                self.screen.blit(self.font_tiny.render(ai_txt, True, ai_col), (box.x + 14, box.y + 34))

    def _draw_airfield_scenery(self, airbase: Airbase):
        """Draws realistic airport landscape: water reservoirs, perimeter roads, and tree clusters (matching Image 1 & 2)."""
        # 1. West Water Retention Canal / Pond (as seen in Image 1)
        w_pond_shore = [
            (130, 270), (190, 250), (250, 275), (265, 345), (245, 425),
            (195, 455), (135, 420), (115, 340),
        ]
        pygame.draw.polygon(self.screen, (182, 168, 134), w_pond_shore)
        w_pond_water = [
            (135, 274), (188, 255), (245, 280), (258, 343), (240, 419),
            (193, 449), (139, 416), (120, 342),
        ]
        pygame.draw.polygon(self.screen, (55, 145, 195), w_pond_water)
        w_pond_deep = [
            (145, 286), (184, 269), (232, 291), (244, 337), (229, 403),
            (187, 433), (149, 406), (133, 348),
        ]
        pygame.draw.polygon(self.screen, (34, 100, 155), w_pond_deep)

        # 2. Southeast Retention Basin (as seen in Image 1)
        se_pond_shore = [
            (1000, 520), (1070, 510), (1120, 540), (1140, 600), (1100, 650),
            (1030, 660), (980, 610), (970, 560),
        ]
        pygame.draw.polygon(self.screen, (182, 168, 134), se_pond_shore)
        se_pond_water = [
            (1005, 525), (1068, 515), (1114, 544), (1133, 598), (1095, 644),
            (1032, 653), (986, 606), (976, 563),
        ]
        pygame.draw.polygon(self.screen, (55, 145, 195), se_pond_water)
        se_pond_deep = [
            (1016, 536), (1062, 528), (1100, 552), (1116, 594), (1082, 632),
            (1036, 640), (998, 600), (990, 568),
        ]
        pygame.draw.polygon(self.screen, (34, 100, 155), se_pond_deep)

        # 3. Airport Perimeter Service Access Road (as seen in Image 1)
        road_x = 1180
        pygame.draw.rect(self.screen, (42, 46, 54), (road_x - 7, 54, 14, 690))
        pygame.draw.rect(self.screen, (30, 34, 40), (road_x - 7, 54, 14, 690), 1)
        pygame.draw.rect(self.screen, (42, 46, 54), (940, 120, 240, 12))
        ry = 60
        while ry < 740:
            pygame.draw.line(self.screen, (225, 185, 45), (road_x, ry), (road_x, ry + 12), 1)
            ry += 24

        # 4. Perimeter Tree Clusters (as seen in Image 1 & 2)
        tree_spots = [
            (115, 230, 13), (145, 215, 11), (275, 240, 14), (290, 260, 12),
            (110, 440, 13), (135, 465, 12), (250, 455, 14), (275, 475, 12),
            (970, 495, 13), (990, 475, 11), (1145, 515, 14), (1120, 665, 13),
            (1202, 175, 14), (1202, 255, 13), (1202, 335, 15), (1202, 415, 13), (1202, 495, 14),
        ]
        for tx, ty, tr in tree_spots:
            pygame.draw.circle(self.screen, (20, 34, 24), (tx + 3, ty + 4), tr)
            pygame.draw.circle(self.screen, (34, 110, 55), (tx, ty), tr)
            pygame.draw.circle(self.screen, (46, 138, 70), (tx - 2, ty - 2), int(tr * 0.72))
            pygame.draw.circle(self.screen, (60, 165, 86), (tx - 4, ty - 4), int(tr * 0.38))

    def _draw_taxiway_network(self, airbase: Airbase):
        """Draws a complete, interconnected commercial taxiway network matching Image 3."""
        if not airbase.runways:
            return

        sorted_rwys = sorted(airbase.runways.values(), key=lambda r: r.start_y)
        rwy_top = sorted_rwys[0]
        rwy_bot = sorted_rwys[-1]

        tax_w = 14
        tax_alpha_y = int(rwy_top.start_y - 42)
        west_loop_x = 350
        east_loop_x = 920
        bot_tax_y = int(rwy_bot.start_y + 40)
        cx = int(rwy_top.center_x)

        wig_left = math.sin(self.pulse_phase * 6.5) > 0.0

        def draw_seg(p1, p2):
            pygame.draw.line(self.screen, (178, 164, 130), p1, p2, tax_w + 6)
            pygame.draw.line(self.screen, (38, 42, 50), p1, p2, tax_w)
            pygame.draw.line(self.screen, (235, 185, 45), p1, p2, 2)

        def draw_holding_bar(x, y, is_vertical=True):
            if is_vertical:
                pygame.draw.line(self.screen, (245, 200, 50), (x - 2, y - 7), (x - 2, y + 7), 2)
                pygame.draw.line(self.screen, (245, 200, 50), (x + 2, y - 7), (x + 2, y + 7), 2)
                # Alternating yellow runway guard wig-wag lights
                c1 = (255, 220, 55) if wig_left else (110, 85, 18)
                c2 = (110, 85, 18) if wig_left else (255, 220, 55)
                pygame.draw.circle(self.screen, c1, (x, y - 10), 2)
                pygame.draw.circle(self.screen, c2, (x, y + 10), 2)
            else:
                pygame.draw.line(self.screen, (245, 200, 50), (x - 7, y - 2), (x + 7, y - 2), 2)
                pygame.draw.line(self.screen, (245, 200, 50), (x - 7, y + 2), (x + 7, y + 2), 2)
                c1 = (255, 220, 55) if wig_left else (110, 85, 18)
                c2 = (110, 85, 18) if wig_left else (255, 220, 55)
                pygame.draw.circle(self.screen, c1, (x - 10, y), 2)
                pygame.draw.circle(self.screen, c2, (x + 10, y), 2)

        # 1. Parallel Taxiway Alpha (North of RWY 1)
        draw_seg((west_loop_x, tax_alpha_y), (east_loop_x, tax_alpha_y))

        # 2. Parallel Taxiway Omega (South of Lowest Runway)
        draw_seg((west_loop_x, bot_tax_y), (east_loop_x, bot_tax_y))

        # 3. West End-Around Loop Taxiway (Full vertical link connecting all runways)
        draw_seg((west_loop_x, tax_alpha_y), (west_loop_x, bot_tax_y))

        # 4. East End-Around Loop Taxiway (Full vertical link connecting all runways)
        draw_seg((east_loop_x, tax_alpha_y), (east_loop_x, bot_tax_y))

        # 5. Connect every runway's threshold to West Loop and East Loop
        for r in sorted_rwys:
            # West threshold connection
            draw_seg((west_loop_x, int(r.start_y)), (int(r.start_x), int(r.start_y)))
            draw_holding_bar(int(r.start_x - 14), int(r.start_y), is_vertical=True)
            # East threshold connection
            draw_seg((int(r.end_x), int(r.end_y)), (east_loop_x, int(r.end_y)))
            draw_holding_bar(int(r.end_x + 14), int(r.end_y), is_vertical=True)

        # 6. Inter-runway intermediate parallel taxiways & high-speed angled turnouts (RETs)
        for i in range(len(sorted_rwys) - 1):
            r_upper = sorted_rwys[i]
            r_lower = sorted_rwys[i + 1]
            mid_y = int((r_upper.start_y + r_lower.start_y) / 2)

            # Midfield parallel taxiway between these two runways
            draw_seg((west_loop_x, mid_y), (east_loop_x, mid_y))

            # 30° / 45° angled high-speed rapid exit turnouts (RETs)
            # Upper runway exits down to mid_y:
            draw_seg((int(r_upper.start_x + 90), int(r_upper.start_y)), (int(r_upper.start_x + 35), mid_y))
            draw_seg((int(r_upper.end_x - 90), int(r_upper.start_y)), (int(r_upper.end_x - 35), mid_y))
            draw_holding_bar(int(r_upper.start_x + 65), int(r_upper.start_y * 0.6 + mid_y * 0.4), is_vertical=False)
            draw_holding_bar(int(r_upper.end_x - 65), int(r_upper.start_y * 0.6 + mid_y * 0.4), is_vertical=False)

            # Lower runway exits up to mid_y:
            draw_seg((int(r_lower.start_x + 90), int(r_lower.start_y)), (int(r_lower.start_x + 35), mid_y))
            draw_seg((int(r_lower.end_x - 90), int(r_lower.start_y)), (int(r_lower.end_x - 35), mid_y))
            draw_holding_bar(int(r_lower.start_x + 65), int(r_lower.start_y * 0.6 + mid_y * 0.4), is_vertical=False)
            draw_holding_bar(int(r_lower.end_x - 65), int(r_lower.start_y * 0.6 + mid_y * 0.4), is_vertical=False)

            # Diagonal cross-runway links (as prominently featured in Image 3!)
            draw_seg((int(r_upper.center_x - 70), int(r_upper.start_y)), (int(r_upper.center_x + 70), mid_y))
            draw_seg((int(r_lower.center_x - 70), int(r_lower.start_y)), (int(r_lower.center_x + 70), mid_y))

        # 7. High-speed exits from RWY 1 up to Taxiway Alpha
        draw_seg((int(rwy_top.start_x + 90), int(rwy_top.start_y)), (int(rwy_top.start_x + 35), tax_alpha_y))
        draw_seg((int(rwy_top.end_x - 90), int(rwy_top.start_y)), (int(rwy_top.end_x - 35), tax_alpha_y))
        draw_holding_bar(int(rwy_top.start_x + 65), int(rwy_top.start_y * 0.6 + tax_alpha_y * 0.4), is_vertical=False)
        draw_holding_bar(int(rwy_top.end_x - 65), int(rwy_top.start_y * 0.6 + tax_alpha_y * 0.4), is_vertical=False)

        # 8. High-speed exits from Lowest Runway down to Taxiway Omega
        draw_seg((int(rwy_bot.start_x + 90), int(rwy_bot.start_y)), (int(rwy_bot.start_x + 35), bot_tax_y))
        draw_seg((int(rwy_bot.end_x - 90), int(rwy_bot.start_y)), (int(rwy_bot.end_x - 35), bot_tax_y))

        # 9. Midfield Central Spine Taxiway (Connects all parallel taxiways vertically)
        draw_seg((cx, tax_alpha_y), (cx, bot_tax_y))

    def _draw_terminal_complex(self, airbase: Airbase):
        """Draws passenger terminal building, boarding jet bridges, and docked airliners (matching Image 1 & 3)."""
        tx, ty, tw, th = 445, 96, 460, 44

        # Concrete Apron Pad for gates
        apron_rect = pygame.Rect(tx - 30, ty + th - 6, tw + 60, 52)
        pygame.draw.rect(self.screen, (178, 164, 130), (apron_rect.x - 3, apron_rect.y - 3, apron_rect.w + 6, apron_rect.h + 6), border_radius=4)
        pygame.draw.rect(self.screen, (76, 84, 96), apron_rect, border_radius=3)
        pygame.draw.rect(self.screen, (60, 68, 78), apron_rect, 1, border_radius=3)

        # Terminal Building drop shadow & roof
        pygame.draw.rect(self.screen, (20, 26, 34), (tx + 4, ty + 5, tw, th), border_radius=8)
        pygame.draw.rect(self.screen, (118, 142, 164), (tx, ty, tw, th), border_radius=8)
        pygame.draw.rect(self.screen, (68, 88, 108), (tx, ty, tw, th), 2, border_radius=8)

        # Glass Skylights / Solar Panel grid (as in Image 3)
        for sx in range(tx + 20, tx + tw - 24, 42):
            panel = pygame.Rect(sx, ty + 8, 34, 26)
            pygame.draw.rect(self.screen, (32, 65, 96), panel, border_radius=3)
            pygame.draw.rect(self.screen, (72, 128, 175), panel, 1, border_radius=3)
            pygame.draw.line(self.screen, (72, 128, 175), (panel.centerx, panel.y), (panel.centerx, panel.bottom), 1)

        # Concourse Title text
        term_txt = self.font_tiny.render("TERMINAL 1 • PASSENGER CONCOURSE", True, (225, 238, 250))
        self.screen.blit(term_txt, (tx + (tw - term_txt.get_width()) // 2, ty + 2))

        # 5 Passenger Boarding Gates & Jet Bridges (Jetways, exactly as in Image 3)
        gates = [
            (tx + 45, "G1"),
            (tx + 130, "G2"),
            (tx + 215, "G3"),
            (tx + 300, "G4"),
            (tx + 385, "G5"),
        ]
        rwy1 = airbase.runways.get("RWY 1")
        tax_alpha_y = int(rwy1.start_y - 42) if rwy1 else 178

        for gx, g_name in gates:
            # Jet bridge fixed rotunda
            pygame.draw.circle(self.screen, (195, 202, 212), (gx, ty + th), 5)
            # Telescopic corridor extending to aircraft door
            pygame.draw.line(self.screen, (215, 220, 228), (gx, ty + th), (gx + 5, ty + th + 14), 4)
            pygame.draw.line(self.screen, (50, 56, 66), (gx, ty + th), (gx + 5, ty + th + 14), 1)
            # Accordion bellows cab head
            pygame.draw.rect(self.screen, (54, 60, 70), (gx + 2, ty + th + 12, 6, 5), border_radius=1)

            # Aircraft parking box & stand label
            stand_box = pygame.Rect(gx - 22, ty + th + 8, 44, 40)
            pygame.draw.rect(self.screen, (190, 165, 45), stand_box, 1, border_radius=2)
            pygame.draw.line(self.screen, (235, 185, 45), (gx, ty + th + 8), (gx, ty + th + 32), 2)
            pygame.draw.line(self.screen, (235, 185, 45), (gx - 8, ty + th + 26), (gx + 8, ty + th + 26), 2)

            # Yellow lead-out guide line connecting gate to Taxiway Alpha!
            pygame.draw.line(self.screen, (235, 185, 45), (gx, ty + th + 32), (gx, tax_alpha_y), 2)

            lbl = self.font_tiny.render(g_name, True, (235, 205, 75))
            self.screen.blit(lbl, (gx - lbl.get_width() // 2, ty + th + 36))

            # Docked Airliner parked at gate (facing South, 180 degrees)
            self._draw_plane_sprite(gx, ty + th + 22, heading_deg=180.0, color=(240, 246, 252), scale=0.74)

    def _draw_control_tower(self, cx: float, cy: float):
        """Draws authentic airport observation control tower with radar dome (matching Image 2)."""
        pygame.draw.circle(self.screen, (18, 24, 32), (int(cx + 4), int(cy + 5)), 14)
        pygame.draw.circle(self.screen, (225, 230, 238), (int(cx), int(cy)), 12)
        pygame.draw.circle(self.screen, (165, 175, 188), (int(cx), int(cy)), 12, 1)
        pygame.draw.circle(self.screen, (34, 68, 98), (int(cx), int(cy)), 8)
        pygame.draw.circle(self.screen, (75, 145, 195), (int(cx), int(cy)), 8, 1)
        pygame.draw.circle(self.screen, (248, 250, 252), (int(cx), int(cy)), 4)
        if math.sin(self.pulse_phase * 3.0) > 0.3:
            pygame.draw.circle(self.screen, (255, 60, 60), (int(cx), int(cy)), 2)
        lbl = self.font_tiny.render("TWR", True, (210, 225, 240))
        self.screen.blit(lbl, (int(cx - lbl.get_width() // 2), int(cy + 15)))

    def _draw_airbase_tarmac_and_runways(
        self,
        airbase: Airbase,
        hovered_rwy: Optional[str] = None,
        drag_valid: bool = True,
        active_ac: Optional[Aircraft] = None,
    ):
        """Draws the complete commercial airport layout: ponds, roads, taxiways, terminal, tower, and runways."""
        # 1. Natural airfield landscape (water reservoirs, access road, perimeter trees)
        self._draw_airfield_scenery(airbase)

        if not airbase.runways:
            return

        # 2. Main concrete airbase apron encompassing all runways & taxiways
        min_rwy_y = min(r.start_y for r in airbase.runways.values())
        max_rwy_y = max(r.start_y for r in airbase.runways.values())
        top_y = min_rwy_y - 128  # encompasses terminal concourse & apron
        bot_y = max_rwy_y + 65   # encompasses south perimeter taxiway

        tarmac_pts = [
            (420, top_y - 12),
            (880, top_y - 12),
            (960, top_y + 40),
            (960, bot_y - 25),
            (925, bot_y + 12),
            (365, bot_y + 12),
            (310, bot_y - 25),
            (310, top_y + 40),
        ]
        # Sand safety perimeter
        pygame.draw.polygon(self.screen, (184, 170, 134), [(x, y + 4) for x, y in tarmac_pts])
        pygame.draw.polygon(self.screen, (184, 170, 134), tarmac_pts)
        # Main asphalt apron
        pygame.draw.polygon(self.screen, (74, 82, 94), tarmac_pts)
        pygame.draw.polygon(self.screen, (58, 66, 76), tarmac_pts, 2)

        # 3. Complete High-Speed Exit Taxiway Network
        self._draw_taxiway_network(airbase)

        # 4. Modern Passenger Terminal Complex with Jetways & Docked Airliners
        self._draw_terminal_complex(airbase)

        # 5. Air Traffic Control Tower (West side of airfield)
        self._draw_control_tower(310, 240)

        # 6. Draw each runway cleanly along its angle with shoulders, skid marks & markings
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
        """Draws a commercial asphalt runway strip with sandy shoulders, tire skid marks, ICAO markings, and status badge."""
        half_w = 18.0
        nx, ny = -rwy.uy * half_w, rwy.ux * half_w
        corners = [
            (rwy.start_x + nx, rwy.start_y + ny),
            (rwy.end_x + nx, rwy.end_y + ny),
            (rwy.end_x - nx, rwy.end_y - ny),
            (rwy.start_x - nx, rwy.start_y - ny),
        ]

        # 1. Sandy / Gravel Runway Shoulder (Runway Safety Area - RSA, as in Image 1, 2, 3)
        sh_pad = 8.0
        sh_nx, sh_ny = -rwy.uy * (half_w + sh_pad), rwy.ux * (half_w + sh_pad)
        sh_corners = [
            (rwy.start_x - rwy.ux * 12.0 + sh_nx, rwy.start_y - rwy.uy * 12.0 + sh_ny),
            (rwy.end_x + rwy.ux * 12.0 + sh_nx, rwy.end_y + rwy.uy * 12.0 + sh_ny),
            (rwy.end_x + rwy.ux * 12.0 - sh_nx, rwy.end_y + rwy.uy * 12.0 - sh_ny),
            (rwy.start_x - rwy.ux * 12.0 - sh_nx, rwy.start_y - rwy.uy * 12.0 - sh_ny),
        ]
        pygame.draw.polygon(self.screen, (184, 170, 134), sh_corners)
        pygame.draw.polygon(self.screen, (158, 144, 110), sh_corners, 1)

        compat_state: Optional[bool] = None
        if active_ac is not None and rwy.status == RunwayStatus.AVAILABLE:
            compat_state = rwy.supports_aircraft(active_ac.min_runway_length_m)

        # Highlight glow if hovering during drag, or compatibility ring when an aircraft is selected
        if is_hovered or compat_state is not None:
            if is_hovered:
                glow_col = config.COLOR_PRIMARY_GREEN if drag_valid else config.COLOR_CRITICAL_RED
                border_w, pad = 3, 4.0
            elif compat_state:
                glow_col = config.COLOR_PRIMARY_GREEN
                border_w, pad = 2, 3.0
            else:
                glow_col = config.COLOR_WARN_AMBER
                border_w, pad = 2, 3.0

            g_nx, g_ny = -rwy.uy * (half_w + sh_pad + pad), rwy.ux * (half_w + sh_pad + pad)
            g_corners = [
                (rwy.start_x - rwy.ux * 14.0 + g_nx, rwy.start_y - rwy.uy * 14.0 + g_ny),
                (rwy.end_x + rwy.ux * 14.0 + g_nx, rwy.end_y + rwy.uy * 14.0 + g_ny),
                (rwy.end_x + rwy.ux * 14.0 - g_nx, rwy.end_y + rwy.uy * 14.0 - g_ny),
                (rwy.start_x - rwy.ux * 14.0 - g_nx, rwy.start_y - rwy.uy * 14.0 - g_ny),
            ]
            pygame.draw.polygon(self.screen, glow_col, g_corners, border_w)

        # 2. Main Asphalt Runway Pavement
        pygame.draw.polygon(self.screen, (28, 32, 38), corners)
        pygame.draw.polygon(self.screen, (210, 210, 200), corners, 1)

        # 3. Touchdown Zone Rubber Tire Skid Marks (crucial feature from Image 2 & 3)
        for base_t, dir_sign in ((28.0, 1.0), (rwy.pixel_length - 28.0, -1.0)):
            for lateral_offset in (-3.6, -1.8, 0.0, 1.8, 3.6):
                skid_len = 85.0
                p1_x = rwy.start_x + rwy.ux * base_t - rwy.uy * lateral_offset
                p1_y = rwy.start_y + rwy.uy * base_t + rwy.ux * lateral_offset
                p2_x = p1_x + rwy.ux * (skid_len * dir_sign)
                p2_y = p1_y + rwy.uy * (skid_len * dir_sign)
                pygame.draw.line(self.screen, (16, 20, 26), (p1_x, p1_y), (p2_x, p2_y), 2)
            p1_cx = rwy.start_x + rwy.ux * (base_t + 15.0 * dir_sign)
            p1_cy = rwy.start_y + rwy.uy * (base_t + 15.0 * dir_sign)
            p2_cx = p1_cx + rwy.ux * (50.0 * dir_sign)
            p2_cy = p1_cy + rwy.uy * (50.0 * dir_sign)
            pygame.draw.line(self.screen, (12, 15, 20), (p1_cx, p1_cy), (p2_cx, p2_cy), 3)

        # 4. Threshold piano keys (both ends, 8 keys each as in Image 1 & 2)
        for end_t in (8.0, rwy.pixel_length - 18.0):
            for offset in (-12.0, -9.0, -6.0, -3.0, 3.0, 6.0, 9.0, 12.0):
                px = rwy.start_x + rwy.ux * end_t - rwy.uy * offset
                py = rwy.start_y + rwy.uy * end_t + rwy.ux * offset
                qx = px + rwy.ux * 10.0
                qy = py + rwy.uy * 10.0
                pygame.draw.line(self.screen, config.COLOR_RUNWAY_MARKING, (px, py), (qx, qy), 2)

        # 5. Runway Designation Numbers on asphalt
        rwy_num = rwy.id.replace("RWY ", "").strip()
        num_str = f"0{rwy_num}" if len(rwy_num) == 1 else rwy_num
        num_surf = self.font_mono_sm.render(num_str, True, config.COLOR_RUNWAY_MARKING)
        angle_deg = math.degrees(math.atan2(-rwy.uy, rwy.ux))
        rot_surf = pygame.transform.rotate(num_surf, angle_deg)
        nx_pos = rwy.start_x + rwy.ux * 26.0
        ny_pos = rwy.start_y + rwy.uy * 26.0
        self.screen.blit(rot_surf, rot_surf.get_rect(center=(int(nx_pos), int(ny_pos))))

        # 6. Thick White Aiming Point Blocks (ICAO standard, as in Image 1 & 2)
        for aim_t in (68.0, rwy.pixel_length - 68.0):
            for aim_offset in (-7.0, 7.0):
                ax = rwy.start_x + rwy.ux * aim_t - rwy.uy * aim_offset
                ay = rwy.start_y + rwy.uy * aim_t + rwy.ux * aim_offset
                bx = ax + rwy.ux * 24.0
                by = ay + rwy.uy * 24.0
                pygame.draw.line(self.screen, config.COLOR_RUNWAY_MARKING, (ax, ay), (bx, by), 4)

        # 7. Touchdown Zone Distance Bars (Pairs of stripes)
        for tdz_t in (46.0, rwy.pixel_length - 46.0):
            for tdz_off in (-9.0, -5.0, 5.0, 9.0):
                tx = rwy.start_x + rwy.ux * tdz_t - rwy.uy * tdz_off
                ty = rwy.start_y + rwy.uy * tdz_t + rwy.ux * tdz_off
                pygame.draw.line(self.screen, config.COLOR_RUNWAY_MARKING, (tx, ty), (tx + rwy.ux * 12.0, ty + rwy.uy * 12.0), 2)

        # 8. Centerline dashes (between touchdown zones)
        t = 118.0
        while t < rwy.pixel_length - 118.0:
            p1 = (rwy.start_x + rwy.ux * t, rwy.start_y + rwy.uy * t)
            p2 = (rwy.start_x + rwy.ux * (t + 16.0), rwy.start_y + rwy.uy * (t + 16.0))
            pygame.draw.line(self.screen, config.COLOR_RUNWAY_MARKING, p1, p2, 2)
            t += 28.0

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

        # 9. ICAO Standard Runway Lighting System
        # A. High-Intensity Runway Edge Lights (HIRL):
        # White along main zone, alternating amber/yellow in final 28% rollout caution zone
        caution_t = rwy.pixel_length * 0.72
        strobe_on = math.sin(self.pulse_phase * 6.0) > 0.15

        lt = 10.0
        while lt <= rwy.pixel_length - 10.0:
            is_caution = (lt >= caution_t)
            edge_col = (255, 205, 75) if is_caution else (255, 252, 235)
            halo_col = (140, 110, 35) if is_caution else (120, 135, 160)

            for side_sign in (-1.0, 1.0):
                lx = rwy.start_x + rwy.ux * lt - rwy.uy * (half_w - 1.2) * side_sign
                ly = rwy.start_y + rwy.uy * lt + rwy.ux * (half_w - 1.2) * side_sign
                pygame.draw.circle(self.screen, halo_col, (int(lx), int(ly)), 3)
                pygame.draw.circle(self.screen, edge_col, (int(lx), int(ly)), 1)

            lt += 24.0

        # B. Bidirectional Runway Threshold (Green) & End (Red) Lights:
        for end_t, is_start in ((4.0, True), (rwy.pixel_length - 4.0, False)):
            # Transverse Green Threshold Light Bar
            for off in range(-14, 15, 3):
                tx = rwy.start_x + rwy.ux * end_t - rwy.uy * float(off)
                ty = rwy.start_y + rwy.uy * end_t + rwy.ux * float(off)
                pygame.draw.circle(self.screen, (20, 100, 45), (int(tx), int(ty)), 3)
                pygame.draw.circle(self.screen, (60, 255, 130), (int(tx), int(ty)), 1)

            # Outboard Wing-Bar Green Lights
            for wing_off in (-22.0, -18.0, 18.0, 22.0):
                wx = rwy.start_x + rwy.ux * end_t - rwy.uy * wing_off
                wy = rwy.start_y + rwy.uy * end_t + rwy.ux * wing_off
                pygame.draw.circle(self.screen, (20, 100, 45), (int(wx), int(wy)), 3)
                pygame.draw.circle(self.screen, (80, 255, 150), (int(wx), int(wy)), 1)

            # Ruby Red Runway End Stop Bar
            for roff in range(-12, 13, 4):
                rx = rwy.start_x + rwy.ux * end_t - rwy.uy * float(roff)
                ry = rwy.start_y + rwy.uy * end_t + rwy.ux * float(roff)
                pygame.draw.circle(self.screen, (255, 50, 50), (int(rx + (1.5 if is_start else -1.5)), int(ry)), 1)

            # REIL (Runway End Identifier Lights - Flashing white strobes)
            if strobe_on:
                for reil_off in (-26.0, 26.0):
                    reil_x = rwy.start_x + rwy.ux * end_t - rwy.uy * reil_off
                    reil_y = rwy.start_y + rwy.uy * end_t + rwy.ux * reil_off
                    pygame.draw.circle(self.screen, (160, 200, 255), (int(reil_x), int(reil_y)), 5)
                    pygame.draw.circle(self.screen, (255, 255, 255), (int(reil_x), int(reil_y)), 2)

        # C. Precision Approach Path Indicator (PAPI - 4 light units: 2 White, 2 Red)
        papi_t = 68.0
        papi_lateral = half_w + 12.0
        for i, p_col in enumerate([(255, 255, 255), (255, 255, 255), (255, 55, 55), (255, 55, 55)]):
            px = rwy.start_x + rwy.ux * (papi_t + (i - 1.5) * 5.0) - rwy.uy * papi_lateral
            py = rwy.start_y + rwy.uy * (papi_t + (i - 1.5) * 5.0) + rwy.ux * papi_lateral
            h_col = (120, 130, 150) if p_col[1] > 100 else (130, 30, 30)
            pygame.draw.circle(self.screen, h_col, (int(px), int(py)), 3)
            pygame.draw.circle(self.screen, p_col, (int(px), int(py)), 1)

        # Status badge pill above runway start/mid
        if rwy.status == RunwayStatus.AVAILABLE:
            if compat_state is False:
                st_col = config.COLOR_WARN_AMBER
                st_txt = f"{rwy.id} • TOO SHORT"
            else:
                st_col = (130, 215, 160)
                st_txt = f"{rwy.id} • {rwy.length_m}m"
        elif rwy.status == RunwayStatus.OCCUPIED:
            st_col = (255, 120, 120)
            st_txt = f"{rwy.id} • BUSY [{rwy.current_aircraft}]"
        else:
            st_col = config.COLOR_WARN_AMBER
            st_txt = f"{rwy.id} • CLOSED"

        lbl = self.font_tiny.render(st_txt, True, st_col)
        pill_w, pill_h = lbl.get_width() + 10, 16
        nx, ny = -rwy.uy, rwy.ux
        if ny > 0:
            nx, ny = -nx, -ny
        cx = rwy.center_x + nx * 26.0
        cy = rwy.center_y + ny * 26.0
        bx = int(cx - pill_w // 2)
        by = int(cy - pill_h // 2)
        pill = pygame.Rect(bx, by, pill_w, pill_h)
        pygame.draw.rect(self.screen, (16, 24, 34), pill, border_radius=3)
        pygame.draw.rect(self.screen, (42, 64, 82), pill, 1, border_radius=3)
        self.screen.blit(lbl, (bx + 5, by + 1))

    def _draw_hud_reticle(
        self,
        x: float,
        y: float,
        size: float,
        color: Tuple[int, int, int],
        arm_len: float = 6.0,
        line_width: int = 2,
    ):
        """Draws 4 modern aviation corner brackets [ ] around (x, y)."""
        s = size
        a = arm_len
        # Top-left
        pygame.draw.line(self.screen, color, (x - s, y - s), (x - s + a, y - s), line_width)
        pygame.draw.line(self.screen, color, (x - s, y - s), (x - s, y - s + a), line_width)
        # Top-right
        pygame.draw.line(self.screen, color, (x + s, y - s), (x + s - a, y - s), line_width)
        pygame.draw.line(self.screen, color, (x + s, y - s), (x + s, y - s + a), line_width)
        # Bottom-left
        pygame.draw.line(self.screen, color, (x - s, y + s), (x - s + a, y + s), line_width)
        pygame.draw.line(self.screen, color, (x - s, y + s), (x - s, y + s - a), line_width)
        # Bottom-right
        pygame.draw.line(self.screen, color, (x + s, y + s), (x + s - a, y + s), line_width)
        pygame.draw.line(self.screen, color, (x + s, y + s), (x + s, y + s - a), line_width)

    def _draw_plane_sprite(
        self,
        x: float,
        y: float,
        heading_deg: float,
        color: Tuple[int, int, int],
        scale: float = 1.0,
    ):
        """Draws crisp top-down aircraft silhouette with drop shadow and nav lights."""
        rad = math.radians(heading_deg)
        c, s = math.cos(rad), math.sin(rad)

        def pt(fx: float, fy: float, ox: float = 0.0, oy: float = 0.0) -> Tuple[int, int]:
            rx = fx * scale
            ry = fy * scale
            return (int(x + ox + rx * c - ry * s), int(y + oy + rx * s + ry * c))

        # 1. 3D Elevation Drop Shadow (cast southeast)
        sh_pts = [
            pt(13, 0, 4, 5), pt(5, 3, 4, 5), pt(-1, 14, 4, 5), pt(-4, 13, 4, 5), pt(-5, 3, 4, 5),
            pt(-11, 6, 4, 5), pt(-13, 0, 4, 5), pt(-11, -6, 4, 5), pt(-5, -3, 4, 5),
            pt(-4, -13, 4, 5), pt(-1, -14, 4, 5), pt(5, -3, 4, 5),
        ]
        pygame.draw.polygon(self.screen, (12, 20, 28), sh_pts)

        # 2. Fuselage & Wings
        pts = [
            pt(13, 0), pt(5, 3), pt(-1, 14), pt(-4, 13), pt(-5, 3),
            pt(-11, 6), pt(-13, 0), pt(-11, -6), pt(-5, -3),
            pt(-4, -13), pt(-1, -14), pt(5, -3),
        ]
        pygame.draw.polygon(self.screen, color, pts)
        pygame.draw.polygon(self.screen, (20, 28, 38), pts, 2)

        # 3. Cockpit windshield
        cp = pt(6, 0)
        pygame.draw.circle(self.screen, (40, 60, 80), cp, max(1, int(2 * scale)))

        # 4. Navigation wingtip lights & tail strobe
        p_port = pt(-1, -14)      # Port (left) = Red
        pygame.draw.circle(self.screen, (245, 55, 55), p_port, 2)
        p_star = pt(-1, 14)       # Starboard (right) = Green
        pygame.draw.circle(self.screen, (55, 235, 95), p_star, 2)
        if math.sin(self.pulse_phase * 4.0) > 0.3:
            p_tail = pt(-13, 0)   # White strobe
            pygame.draw.circle(self.screen, (255, 255, 255), p_tail, 2)

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

    def _draw_curved_drag_route(self, aircraft: Aircraft, runway: Any, drop_point: Tuple[int, int], color: Tuple[int, int, int]):
        """Previews a curved arrival leg that straightens onto the selected runway threshold."""
        threshold = runway.get_closest_threshold(drop_point[0], drop_point[1])
        p0 = (float(aircraft.x), float(aircraft.y))
        p3 = threshold["approach_pos"]
        p_end = threshold["start"]
        ux, uy = float(threshold["ux"]), float(threshold["uy"])
        dx, dy = p3[0] - p0[0], p3[1] - p0[1]
        distance = math.hypot(dx, dy)

        if distance < 12.0:
            self._draw_flow_approach_path(p0, p_end, color, spacing=26.0)
        else:
            # Bend the arrival leg away from the runway center, then line up with final.
            nx, ny = -uy, ux
            side = (p0[0] - p3[0]) * nx + (p0[1] - p3[1]) * ny
            if abs(side) < 8.0:
                side = 1.0
            bend = min(150.0, distance * 0.30) * (1.0 if side > 0 else -1.0)
            control = ((p0[0] + p3[0]) * 0.5 + nx * bend, (p0[1] + p3[1]) * 0.5 + ny * bend)
            points = []
            for index in range(33):
                t = index / 32.0
                omt = 1.0 - t
                x = omt * omt * p0[0] + 2.0 * omt * t * control[0] + t * t * p3[0]
                y = omt * omt * p0[1] + 2.0 * omt * t * control[1] + t * t * p3[1]
                points.append((x, y))

            dim_col = tuple(int(c * 0.22 + b * 0.78) for c, b in zip(color, (49, 82, 48)))
            flow_col = tuple(int(c * 0.72 + b * 0.28) for c, b in zip(color, (49, 82, 48)))
            pygame.draw.lines(self.screen, dim_col, False, points, 1)

            next_mark = (self.pulse_phase * 26.0) % 28.0
            walked = 0.0
            for index in range(1, len(points) - 1):
                prev_pt, center, next_pt = points[index - 1], points[index], points[index + 1]
                walked += math.hypot(center[0] - prev_pt[0], center[1] - prev_pt[1])
                if walked < next_mark:
                    continue
                tangent_len = math.hypot(next_pt[0] - prev_pt[0], next_pt[1] - prev_pt[1]) or 1.0
                tx, ty = (next_pt[0] - prev_pt[0]) / tangent_len, (next_pt[1] - prev_pt[1]) / tangent_len
                px, py = -ty, tx
                tip = (center[0] + tx * 5.0, center[1] + ty * 5.0)
                left = (center[0] - tx * 4.0 + px * 3.5, center[1] - ty * 4.0 + py * 3.5)
                right = (center[0] - tx * 4.0 - px * 3.5, center[1] - ty * 4.0 - py * 3.5)
                pygame.draw.lines(self.screen, flow_col, False, [left, tip, right], 1)
                next_mark += 28.0

            self._draw_flow_approach_path(p3, p_end, color, spacing=26.0)

        pygame.draw.circle(self.screen, color, (int(p_end[0]), int(p_end[1])), 8, 2)

    def _draw_flow_approach_path(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        color: Tuple[int, int, int],
        spacing: float = 18.0,
    ):
        """Draws animated chevrons >> >> >> flowing towards destination threshold."""
        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist < 12.0:
            return

        ux = (x2 - x1) / dist
        uy = (y2 - y1) / dist
        nx, ny = -uy, ux

        # Center trackline in muted tone
        dim_col = tuple(int(c * 0.22 + b * 0.78) for c, b in zip(color, (49, 82, 48)))
        pygame.draw.line(self.screen, dim_col, (int(x1), int(y1)), (int(x2), int(y2)), 1)

        # Marching offset towards destination
        spacing = max(spacing, 26.0)
        flow_offset = (self.pulse_phase * 26.0) % spacing
        flow_col = tuple(int(c * 0.72 + b * 0.28) for c, b in zip(color, (49, 82, 48)))
        d = flow_offset
        while d < dist - 14.0:
            cx = x1 + ux * d
            cy = y1 + uy * d
            w1x = cx - ux * 5.0 + nx * 4.0
            w1y = cy - uy * 5.0 + ny * 4.0
            w2x = cx - ux * 5.0 - nx * 4.0
            w2y = cy - uy * 5.0 - ny * 4.0
            pygame.draw.lines(self.screen, flow_col, False, [(w1x, w1y), (cx, cy), (w2x, w2y)], 1)
            d += spacing

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
        show_trajectory: bool = True,
    ):
        self.show_trajectory = show_trajectory
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

        # Clean radar airspace: only show subtle trajectory if a holding plane is selected
        if selected_ac and selected_ac.status == FlightStatus.HOLDING:
            pygame.draw.circle(self.screen, (45, 95, 75), (int(selected_ac.orbit_x), int(selected_ac.orbit_y)), int(selected_ac.orbit_radius), 1)

        # Draw local AI focus markers; the radio-style banner gives the recommendation.
        if not drag_state and hasattr(agent, "get_co_pilot_target"):
            co_target = agent.get_co_pilot_target()
            if co_target:
                self._draw_co_pilot_guide(co_target)

        # Draw Drag-and-Draw Manual Override Preview Path
        if drag_state and drag_state.get("aircraft"):
            src_ac = drag_state["aircraft"]
            mx, my = drag_state["mouse_pos"]
            line_col = config.COLOR_PRIMARY_GREEN if drag_valid else config.COLOR_CRITICAL_RED
            runway_id = drag_state.get("hovered_runway")
            target_runway = airbase.runways.get(runway_id) if runway_id else None
            if getattr(self, "show_trajectory", True):
                if target_runway:
                    self._draw_curved_drag_route(src_ac, target_runway, (mx, my), line_col)
                else:
                    self._draw_dotted_line((src_ac.x, src_ac.y), (mx, my), line_col, spacing=7)
                    pygame.draw.circle(self.screen, line_col, (mx, my), 7, 2)
            else:
                pygame.draw.line(self.screen, line_col, (int(src_ac.x), int(src_ac.y)), (int(mx), int(my)), 1)
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

        # Place labels with collision avoidance so busy scenes remain readable.
        self._aircraft_label_rects = []
        # Aircraft sprites + emergency circles + fuel % badges
        for ac in airbase.aircraft_fleet:
            if not ac.is_active_in_airspace():
                continue
            self._draw_gameplay_aircraft(ac, is_selected=(selected_ac is ac))

        # Floating score popups
        for f in self.floating_texts:
            f.draw(self.screen, self.font_body_bold)

        # Top HUD Bar
        tot_ac = level_mgr.level_cfg.get("total_aircraft", 10)
        max_pot = max(100, tot_ac * 150)
        p_score = agent.reward_system.player_cumulative_reward
        s_ratio = min(1.0, max(0.0, p_score / max_pot))

        active_target = agent.get_co_pilot_target() if hasattr(agent, "get_co_pilot_target") else None
        active_aircraft = active_target[0] if active_target else None
        d_rem = active_aircraft.hitl_decision_timer if active_aircraft else config.HITL_TIMEOUT_SECONDS
        d_init = active_aircraft.hitl_initial_timer if active_aircraft else config.HITL_TIMEOUT_SECONDS

        self._draw_top_hud_bar(
            landed_count=len(airbase.flight_history),
            score_label="YOU",
            score_val=p_score,
            mysql_ok=True,
            ai_ready=True,
            extra_text=f"WIND {int(airbase.wind_speed_kts)}KT",
            show_status_box=False,
            star_ratio=s_ratio,
            decision_remaining=d_rem,
            decision_initial=d_init,
            decision_active=active_target is not None,
            level_id=level_mgr.current_level,
        )

        # Unified Comms/Event Alert Banner (strictly 1 banner at a time in the clear corridor)
        co_target = active_target if (not drag_state and hasattr(agent, "get_co_pilot_target")) else None
        if co_target and co_target[0].status == FlightStatus.HOLDING:
            self._draw_radio_comms_bubble(co_target)
        elif level_mgr.active_banner:
            self._draw_event_banner(level_mgr.active_banner)

        hint = self.font_small.render("SPACE  Clear AI recommendation     Drag a plane to a runway     F1  Help", True, (207, 222, 207))
        hint_box = pygame.Rect(0, config.WINDOW_HEIGHT - 30, config.WINDOW_WIDTH, 30)
        pygame.draw.rect(self.screen, (19, 33, 27), hint_box)
        pygame.draw.line(self.screen, (73, 111, 73), hint_box.topleft, hint_box.topright, 1)
        self.screen.blit(hint, hint.get_rect(center=hint_box.center))

        # Optional Modal Overlay (Pause / Level Complete / Crash)
        if modal_state:
            self._render_modal_overlay(modal_state)
        elif is_paused:
            self._render_pause_overlay()

    def _get_fuel_ring_color(self, fuel: float) -> Tuple[int, int, int]:
        if fuel > 50.0:
            return (50, 220, 90)
        elif fuel >= 20.0:
            return (255, 185, 35)
        else:
            return (240, 50, 50)

    def _get_emergency_symbol(self, ac: Aircraft) -> Optional[str]:
        if ac.fuel_level <= config.FUEL_CRITICAL_THRESHOLD or ac.emergency_type == EmergencyType.CRITICAL_FUEL:
            return "FUEL"
        if ac.emergency_type == EmergencyType.ENGINE_PROBLEM:
            return "ENGINE"
        if ac.emergency_type == EmergencyType.MEDICAL:
            return "MEDICAL"
        if ac.emergency_type == EmergencyType.BIRD_STRIKE:
            return "BIRD_STRIKE"
        if ac.is_emergency():
            return "EMERGENCY"
        return None

    def _draw_ai_spotlight(self, co_pilot_target: Optional[Tuple[Any, Any]]):
        if not co_pilot_target:
            return
        ac, rwy = co_pilot_target
        if ac.status != FlightStatus.HOLDING:
            return

        pulse = 0.5 + 0.5 * math.sin(self.pulse_phase * 2.5)

        # Keep the recommendation local: spotlight the plane and runway threshold
        # without drawing a long route across the radar.
        gold_col = (255, 215, 65)
        self._draw_hud_reticle(ac.x, ac.y, size=int(22 + 3 * pulse), color=gold_col, arm_len=7)
        threshold = rwy.get_closest_threshold(ac.x, ac.y)["start"]
        self._draw_hud_reticle(threshold[0], threshold[1], size=int(20 + 3 * pulse), color=gold_col, arm_len=6)

    def _draw_radio_comms_bubble(self, co_pilot_target: Optional[Tuple[Any, Any]]):
        if not co_pilot_target:
            return
        ac, rwy = co_pilot_target
        if ac.status != FlightStatus.HOLDING:
            return

        is_em = ac.is_emergency()
        bg_col = (56, 14, 18, 230) if is_em else (16, 28, 44, 230)
        border_col = config.COLOR_CRITICAL_RED if is_em else (255, 215, 65)

        if is_em:
            reason = self._get_emergency_symbol(ac) or "EMERGENCY"
            emergency_detail = f"{int(ac.fuel_level)}% FUEL" if reason == "FUEL" else reason.replace("_", " ")
            msg = f"MAYDAY • {ac.flight_id} • {emergency_detail} • {rwy.id} • SPACE TO CLEAR"
        else:
            msg = f"AI RECOMMENDS • {ac.flight_id} → {rwy.id} • PRESS SPACE"

        lbl = self.font_tiny.render(msg, True, config.COLOR_WHITE)
        max_width = min(380, config.WINDOW_WIDTH - 32)
        if lbl.get_width() > max_width - 24:
            clipped = msg
            while clipped and self.font_tiny.size(clipped + "…")[0] > max_width - 24:
                clipped = clipped[:-1]
            lbl = self.font_tiny.render(clipped.rstrip() + "…", True, config.COLOR_WHITE)
        bw, bh = min(max_width, lbl.get_width() + 24), 26
        bx = (config.WINDOW_WIDTH - bw) // 2
        by = 54
        comm_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        comm_surf.fill(bg_col)
        self.screen.blit(comm_surf, (bx, by))
        pygame.draw.rect(self.screen, border_col, (bx, by, bw, bh), 1, border_radius=5)
        self.screen.blit(lbl, lbl.get_rect(center=(bx + bw // 2, by + bh // 2)))

    def _draw_co_pilot_guide(self, co_pilot_target: Optional[Tuple[Any, Any]]):
        self._draw_ai_spotlight(co_pilot_target)

    def _draw_gameplay_aircraft(self, ac: Aircraft, is_selected: bool):
        ax, ay = int(ac.x), int(ac.y)
        is_em = ac.is_emergency()

        fuel_col = self._get_fuel_ring_color(ac.fuel_level)

        if is_em:
            pulse_r = int(23 + 4 * math.sin(self.pulse_phase * 1.4))
            pygame.draw.circle(self.screen, config.COLOR_CRITICAL_RED, (ax, ay), pulse_r, 2)
            # Exclamation marker matching mockup
            ex, ey = ax + 20, ay - 18
            pygame.draw.circle(self.screen, config.COLOR_CRITICAL_RED, (ex, ey), 7)
            self.screen.blit(self.font_tiny.render("!", True, config.COLOR_WHITE), (ex - 2, ey - 7))
            plane_col = (218, 45, 52)
        elif ac.fuel_level < 40.0:
            plane_col = (232, 178, 38)
        elif ac.aircraft_size == "HEAVY":
            plane_col = (72, 138, 228)
        else:
            plane_col = (224, 232, 240)

        # Draw HUD corner brackets if selected (no concentric circles)
        if is_selected:
            self._draw_hud_reticle(ax, ay, size=22, color=config.COLOR_CYAN, arm_len=7)

        scale = 1.25 if ac.aircraft_size == "HEAVY" else (0.95 if ac.aircraft_size == "SMALL" else 1.1)
        self._draw_plane_sprite(ac.x, ac.y, ac.heading, plane_col, scale=scale)

        # Compact labels use short emergency names and avoid neighboring labels.
        sym = self._get_emergency_symbol(ac)
        short_sym = {"FUEL": "FUEL", "ENGINE": "ENGINE", "MEDICAL": "MED", "BIRD_STRIKE": "BIRD", "EMERGENCY": "ALERT"}.get(sym, "")
        if is_em:
            tag_txt = f"{ac.flight_id}  {int(ac.fuel_level)}%  {short_sym}"
            tag_col = (255, 120, 120)
            tag_bg = (54, 18, 22)
            tag_border = config.COLOR_CRITICAL_RED
        elif is_selected:
            tag_txt = f"{ac.flight_id}  {int(ac.fuel_level)}%  {ac.model}"
            tag_col = config.COLOR_CYAN
            tag_bg = (14, 28, 44)
            tag_border = config.COLOR_CYAN
        else:
            tag_txt = f"{ac.flight_id}  {int(ac.fuel_level)}%"
            tag_col = fuel_col if ac.fuel_level < 50.0 else config.COLOR_WHITE
            tag_bg = (16, 24, 36)
            tag_border = (38, 54, 76)

        lbl = self.font_small.render(tag_txt, True, tag_col)
        bg_w, bg_h = lbl.get_width() + 12, 19
        candidates = [
            pygame.Rect(ax - bg_w // 2, ay + 23, bg_w, bg_h),
            pygame.Rect(ax - bg_w // 2, ay - 25, bg_w, bg_h),
            pygame.Rect(ax + 22, ay - bg_h // 2, bg_w, bg_h),
            pygame.Rect(ax - bg_w - 22, ay - bg_h // 2, bg_w, bg_h),
        ]
        safe = pygame.Rect(5, config.TOP_BAR_HEIGHT + 8, config.CANVAS_WIDTH - 10, config.WINDOW_HEIGHT - config.TOP_BAR_HEIGHT - 44)
        candidates = [pygame.Rect(max(safe.left, min(r.x, safe.right-r.w)), max(safe.top, min(r.y, safe.bottom-r.h)), r.w, r.h) for r in candidates]
        occupied = getattr(self, "_aircraft_label_rects", [])
        bg = min(candidates, key=lambda r: sum(r.clip(other).w * r.clip(other).h for other in occupied))
        occupied.append(bg)
        pygame.draw.rect(self.screen, tag_bg, bg, border_radius=5)
        pygame.draw.rect(self.screen, tag_border, bg, 1, border_radius=5)
        self.screen.blit(lbl, (bg.x + 6, bg.y + 2))

    def _draw_event_banner(self, banner: Dict[str, Any]):
        b_type = banner.get("type", "NORMAL")
        border = config.COLOR_CRITICAL_RED if b_type == "EMERGENCY" else config.COLOR_CYAN
        bg = (56, 14, 18, 230) if b_type == "EMERGENCY" else (16, 28, 44, 230)
        title = banner.get("title", "")
        msg = banner.get("message", "")
        full_txt = f"{title}: {msg}" if title else msg
        max_width = min(360, config.WINDOW_WIDTH - 32)
        lbl = self.font_tiny.render(full_txt, True, config.COLOR_WHITE)
        if lbl.get_width() > max_width - 24:
            clipped = full_txt
            while clipped and self.font_tiny.size(clipped + "…")[0] > max_width - 24:
                clipped = clipped[:-1]
            lbl = self.font_tiny.render(clipped.rstrip() + "…", True, config.COLOR_WHITE)
        bw, bh = min(max_width, lbl.get_width() + 24), 26
        bx, by = (config.WINDOW_WIDTH - bw) // 2, 54
        comm_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        comm_surf.fill(bg)
        self.screen.blit(comm_surf, (bx, by))
        pygame.draw.rect(self.screen, border, (bx, by, bw, bh), 1, border_radius=5)
        self.screen.blit(lbl, lbl.get_rect(center=(bx + bw // 2, by + bh // 2)))

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

        # 3. 20s DECISION TIMER
        timer_box = pygame.Rect(sx + 16, sy + 458, sw - 32, 62)
        pygame.draw.rect(self.screen, config.COLOR_CARD_DARK, timer_box, border_radius=8)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, timer_box, 1, border_radius=8)

        top_pending = pending_ranked[0] if pending_ranked else None
        t_rem = top_pending.hitl_decision_timer if top_pending else config.HITL_TIMEOUT_SECONDS
        t_max = top_pending.hitl_initial_timer if top_pending else config.HITL_TIMEOUT_SECONDS
        pct = max(0.0, min(1.0, t_rem / max(0.1, t_max)))

        self.screen.blit(self.font_header.render("20s DECISION TIMER", True, config.COLOR_WHITE), (timer_box.x + 95, timer_box.y + 7))
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

    def _render_pause_overlay(self):
        dim = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 14, 24, 185))
        self.screen.blit(dim, (0, 0))

        pw, ph = 380, 270
        px = (config.WINDOW_WIDTH - pw) // 2
        py = (config.WINDOW_HEIGHT - ph) // 2
        box = pygame.Rect(px, py, pw, ph)

        pygame.draw.rect(self.screen, (6, 10, 16), (px + 4, py + 6, pw, ph), border_radius=14)
        pygame.draw.rect(self.screen, (18, 28, 42), box, border_radius=14)
        pygame.draw.rect(self.screen, config.COLOR_CYAN, box, 2, border_radius=14)

        t = self.font_title.render("SIMULATION PAUSED", True, config.COLOR_WHITE)
        self.screen.blit(t, t.get_rect(center=(box.centerx, py + 30)))
        s = self.font_small.render("Press [P] or select an action below:", True, config.COLOR_TEXT_MUTED)
        self.screen.blit(s, s.get_rect(center=(box.centerx, py + 56)))

    def _render_modal_overlay(self, modal: Dict[str, Any]):
        """Renders Level Complete or Crash / Game Over Modal with reward breakdown."""
        dim = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((6, 12, 20, 195))
        self.screen.blit(dim, (0, 0))

        if modal.get("type") == "TUTORIAL":
            mx, my, mw, mh = (config.WINDOW_WIDTH - 760) // 2, (config.WINDOW_HEIGHT - 390) // 2, 760, 390
            panel = pygame.Rect(mx, my, mw, mh)
            pygame.draw.rect(self.screen, (17, 29, 39), panel, border_radius=16)
            pygame.draw.rect(self.screen, (76, 143, 112), panel, 2, border_radius=16)

            steps = [
                ("1. READ THE RADAR", "Each aircraft shows its callsign and remaining fuel. Red aircraft are in an emergency.\nRunway badges show whether a runway is open, busy, or closed."),
                ("2. CLEAR A LANDING", "Press SPACE to clear the AI's highlighted recommendation.\nOr drag an aircraft onto an open runway. Click the aircraft, then the runway, also works."),
                ("3. WATCH THE CLOCK", "You get 20 real seconds for the active recommendation. Timeout penalizes delay; the AI\nrescues only critical-fuel or engine emergencies. Routine planes remain yours to clear."),
            ]
            step = max(0, min(len(steps) - 1, int(modal.get("step", 0))))
            title = self.font_title.render("FLIGHT CONTROL: QUICK GUIDE", True, config.COLOR_WHITE)
            self.screen.blit(title, (mx + 34, my + 28))
            self.screen.blit(self.font_small.render(f"STEP {step + 1} OF {len(steps)}", True, (132, 205, 164)), (mx + 36, my + 82))

            # Step progress indicator.
            for idx in range(len(steps)):
                dot_col = (93, 210, 145) if idx <= step else (63, 83, 82)
                pygame.draw.rect(self.screen, dot_col, (mx + 36 + idx * 26, my + 108, 18, 5), border_radius=3)

            section_title, body = steps[step]
            self.screen.blit(self.font_header.render(section_title, True, (248, 209, 96)), (mx + 36, my + 144))
            for line_idx, line in enumerate(body.split("\n")):
                self.screen.blit(self.font_body.render(line, True, (218, 229, 226)), (mx + 36, my + 184 + line_idx * 30))

            key_bg = pygame.Rect(mx + 34, my + 260, mw - 68, 42)
            pygame.draw.rect(self.screen, (25, 42, 50), key_bg, border_radius=8)
            key_hint = self.font_small.render("SPACE  AI clearance     Drag  Manual assignment     P  Pause     F1  Open this guide", True, (179, 203, 195))
            self.screen.blit(key_hint, key_hint.get_rect(center=key_bg.center))
            return

        mw, mh = 540, 360
        mx, my = (config.WINDOW_WIDTH - mw) // 2, (config.WINDOW_HEIGHT - mh) // 2
        m_rect = pygame.Rect(mx, my, mw, mh)
        is_crash = modal.get("type") == "CRASH"
        accent = config.COLOR_CRITICAL_RED if is_crash else config.COLOR_PRIMARY_GREEN

        # Drop shadow & panel body
        pygame.draw.rect(self.screen, (8, 14, 22), (mx + 6, my + 8, mw, mh), border_radius=16)
        pygame.draw.rect(self.screen, (16, 24, 36), m_rect, border_radius=16)
        pygame.draw.rect(self.screen, accent, m_rect, 2, border_radius=16)

        title = modal.get("title", "LEVEL SUMMARY")
        t_surf = self.font_title.render(title, True, accent)
        cx = mx + mw // 2
        self.screen.blit(t_surf, t_surf.get_rect(center=(cx, my + 28)))

        # Big 3-Star Visual Display (Well spaced below title, NO overlap!)
        stars = modal.get("stars", 0 if is_crash else 1)
        star_configs = [
            (cx - 58, my + 86, 17.0, 1),
            (cx, my + 80, 23.0, 2),        # Center star is majestic and larger
            (cx + 58, my + 86, 17.0, 3),
        ]

        for sx, sy, s_rad, s_idx in star_configs:
            is_earned = (s_idx <= stars)
            if is_earned:
                # Outer shadow
                self._draw_vector_star(self.screen, sx + 2, sy + 3, s_rad, (16, 22, 30))
                # Golden metallic border
                self._draw_vector_star(self.screen, sx, sy, s_rad + 2, (185, 135, 20))
                # Main radiant gold star
                self._draw_vector_star(self.screen, sx, sy, s_rad, (255, 218, 45))
                # Inner bright highlight facet
                self._draw_vector_star(self.screen, sx, sy - 1, s_rad * 0.68, (255, 248, 160))
                # Sparkle glint on top tip
                pygame.draw.circle(self.screen, (255, 255, 255), (int(sx), int(sy - s_rad + 3)), 2)
            else:
                # Inactive / silver-slate star
                self._draw_vector_star(self.screen, sx + 2, sy + 3, s_rad, (12, 16, 22))
                self._draw_vector_star(self.screen, sx, sy, s_rad, (36, 48, 64), outline_col=(65, 84, 108))
                self._draw_vector_star(self.screen, sx, sy, s_rad * 0.65, (26, 36, 48))

        # Performance text badge under stars
        ai_rescues = modal.get("ai_rescues", 0)
        if is_crash:
            rating_txt = "MISSION FAILED • AIRFIELD COLLISION"
            rating_col = config.COLOR_CRITICAL_RED
        elif stars == 3:
            rating_txt = "3 STARS • PERFECT HUMAN ATC!"
            rating_col = (255, 225, 65)
        elif stars == 2:
            rating_txt = "2 STARS • GREAT JOB!" if ai_rescues == 0 else "2 STARS • GREAT JOB! (1 AI RESCUE)"
            rating_col = (75, 225, 255)
        elif stars == 1:
            rating_txt = "1 STAR • LEVEL PASSED" if ai_rescues == 0 else f"1 STAR • AI ASSISTED ({ai_rescues} RESCUES)"
            rating_col = (130, 225, 160)
        else:
            rating_txt = "0 STARS • FULL AI AUTOPILOT (NO PLAYER ACTION)"
            rating_col = config.COLOR_WARN_AMBER

        r_surf = self.font_body_bold.render(rating_txt, True, rating_col)
        self.screen.blit(r_surf, r_surf.get_rect(center=(cx, my + 128)))

        sub_surf = self.font_small.render(modal.get("subtitle", ""), True, (185, 205, 220))
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, my + 150)))

        # Sleek, clean Score Card (Zero spreadsheet clutter!)
        score_box = pygame.Rect(mx + 36, my + 175, mw - 72, 80)
        pygame.draw.rect(self.screen, (12, 18, 28), score_box, border_radius=10)
        pygame.draw.rect(self.screen, (34, 52, 72), score_box, 1, border_radius=10)

        score = modal.get("score", 0)
        landings = modal.get("landings", 0)
        emerg = modal.get("emergencies", 0)

        # Left: Big Bold Score
        sc_lbl = self.font_tiny.render("FINAL SCORE", True, config.COLOR_TEXT_MUTED)
        self.screen.blit(sc_lbl, (score_box.x + 22, score_box.y + 14))
        sc_col = config.COLOR_CYAN if score >= 0 else config.COLOR_CRITICAL_RED
        sc_val = self.font_title.render(f"{score:+d} PTS", True, sc_col)
        self.screen.blit(sc_val, (score_box.x + 22, score_box.y + 32))

        # Divider
        pygame.draw.line(self.screen, (34, 52, 72), (score_box.centerx, score_box.y + 12), (score_box.centerx, score_box.bottom - 12), 1)

        # Right: Aircraft & Safety Status
        l_lbl = self.font_body.render(f"AIRCRAFT LANDED: {landings}", True, config.COLOR_WHITE)
        self.screen.blit(l_lbl, (score_box.centerx + 20, score_box.y + 18))
        if ai_rescues > 0:
            safe_str = f"AI RESCUES: {ai_rescues} (SCORE PENALTY)"
            safe_col = config.COLOR_WARN_AMBER
        elif emerg == 0:
            safe_str = "SAFETY: 100% PERFECT HUMAN ATC"
            safe_col = config.COLOR_PRIMARY_GREEN
        else:
            safe_str = f"SAFETY: {emerg} EMERGENCIES SAFE"
            safe_col = config.COLOR_PRIMARY_GREEN
        s_lbl = self.font_body.render(safe_str, True, safe_col)
        self.screen.blit(s_lbl, (score_box.centerx + 20, score_box.y + 44))

    def render_settings_modal(
        self,
        settings: Dict[str, Any],
        reset_confirm: bool = False,
        toast_msg: str = "",
    ):
        """Renders clean, professional settings modal with single-line rows and zero clutter."""
        dim = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((6, 12, 20, 205))
        self.screen.blit(dim, (0, 0))

        mw, mh = 520, 404
        mx = (config.WINDOW_WIDTH - mw) // 2
        my = (config.WINDOW_HEIGHT - mh) // 2
        box = pygame.Rect(mx, my, mw, mh)

        # Drop shadow & panel body
        pygame.draw.rect(self.screen, (6, 10, 16), (mx + 5, my + 6, mw, mh), border_radius=14)
        pygame.draw.rect(self.screen, (16, 24, 38), box, border_radius=14)
        pygame.draw.rect(self.screen, config.COLOR_CYAN, box, 2, border_radius=14)

        # Clean Header
        title_surf = self.font_header.render("SETTINGS", True, config.COLOR_WHITE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(box.centerx, my + 24)))

        # ---------------- Section 1: AUDIO ----------------
        self.screen.blit(self.font_tiny.render("AUDIO", True, config.COLOR_CYAN), (mx + 30, my + 52))
        pygame.draw.line(self.screen, (34, 52, 72), (mx + 30, my + 66), (mx + mw - 30, my + 66), 1)

        row1_y = my + 76
        self.screen.blit(self.font_body.render("Master Audio", True, config.COLOR_WHITE), (mx + 32, row1_y + 5))

        row2_y = my + 114
        self.screen.blit(self.font_body.render("Sound Effects (SFX)", True, config.COLOR_WHITE), (mx + 32, row2_y + 5))

        row3_y = my + 152
        self.screen.blit(self.font_body.render("Airport Ambience", True, config.COLOR_WHITE), (mx + 32, row3_y + 5))

        # ---------------- Section 2: GAMEPLAY ----------------
        self.screen.blit(self.font_tiny.render("GAMEPLAY", True, config.COLOR_CYAN), (mx + 30, my + 192))
        pygame.draw.line(self.screen, (34, 52, 72), (mx + 30, my + 204), (mx + mw - 30, my + 204), 1)

        row4_y = my + 214
        self.screen.blit(self.font_body.render("Co-Pilot Mode", True, config.COLOR_WHITE), (mx + 32, row4_y + 5))

        row5_y = my + 252
        self.screen.blit(self.font_body.render("Trajectory Paths", True, config.COLOR_WHITE), (mx + 32, row5_y + 5))

        # ---------------- Section 3: CAREER DATA ----------------
        self.screen.blit(self.font_tiny.render("CAREER DATA", True, config.COLOR_CYAN), (mx + 30, my + 292))
        pygame.draw.line(self.screen, (34, 52, 72), (mx + 30, my + 304), (mx + mw - 30, my + 304), 1)

        row6_y = my + 314
        if reset_confirm:
            self.screen.blit(self.font_body_bold.render("Reset all stars?", True, config.COLOR_CRITICAL_RED), (mx + 32, row6_y + 5))
        else:
            self.screen.blit(self.font_body.render("Career Progress", True, config.COLOR_WHITE), (mx + 32, row6_y + 5))

        # Toast Message (if present)
        if toast_msg:
            t_surf = self.font_tiny.render(toast_msg, True, config.COLOR_PRIMARY_GREEN)
            self.screen.blit(t_surf, t_surf.get_rect(center=(box.centerx, my + 348)))

    def render_rules_modal(self, active_tab: str = "CONTROLS"):
        """Renders clean, professional classic operations manual & game rules modal."""
        dim = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((6, 12, 20, 205))
        self.screen.blit(dim, (0, 0))

        mw, mh = 760, 480
        mx = (config.WINDOW_WIDTH - mw) // 2
        my = (config.WINDOW_HEIGHT - mh) // 2
        box = pygame.Rect(mx, my, mw, mh)

        # Drop shadow & panel body
        pygame.draw.rect(self.screen, (6, 10, 16), (mx + 5, my + 6, mw, mh), border_radius=14)
        pygame.draw.rect(self.screen, (16, 24, 38), box, border_radius=14)
        pygame.draw.rect(self.screen, config.COLOR_CYAN, box, 2, border_radius=14)

        # Clean Header
        title_surf = self.font_header.render("FLIGHT OPERATIONS & RULES", True, config.COLOR_WHITE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(box.centerx, my + 26)))

        # Tab bar separator line
        pygame.draw.line(self.screen, (34, 52, 72), (mx + 30, my + 92), (mx + mw - 30, my + 92), 1)

        # Inner Content Panel
        c_rect = pygame.Rect(mx + 36, my + 104, mw - 72, 316)
        pygame.draw.rect(self.screen, (11, 17, 28), c_rect, border_radius=8)
        pygame.draw.rect(self.screen, (28, 44, 64), c_rect, 1, border_radius=8)

        px, py = c_rect.x + 22, c_rect.y + 16

        if active_tab == "CONTROLS":
            self.screen.blit(self.font_body_bold.render("AIRCRAFT NAVIGATION & CLEARANCE CONTROLS", True, (255, 215, 65)), (px, py))
            items = [
                ("1. Drag-and-Draw Routing:", "Click and drag any holding aircraft toward an open runway. A green dotted path confirms safe alignment; red indicates an occupied or invalid runway.", config.COLOR_WHITE),
                ("2. Co-Pilot Quick Clearance [SPACE]:", "Press SPACEBAR at any time to instantly authorize the recommendation prepared by the automated co-pilot.", config.COLOR_CYAN),
                ("3. Direct Runway Assignment [1, 2, 3]:", "Select a holding flight, then press 1, 2, or 3 to directly clear Runway 1, 2, or 3 without dragging.", config.COLOR_WHITE),
                ("4. Holding Orbit & Simulation Pause:", "Press [H] to direct selected flight into holding orbit. Press [P] to pause simulation anytime.", config.COLOR_TEXT_MUTED),
            ]
            cy = py + 28
            for header, desc, h_col in items:
                self.screen.blit(self.font_small.render(header, True, h_col), (px, cy))
                self.screen.blit(self.font_tiny.render(desc, True, (180, 198, 215)), (px + 14, cy + 18))
                cy += 44

        elif active_tab == "CO-PILOT":
            self.screen.blit(self.font_body_bold.render("CO-PILOT ASSISTANCE & TAKEOVER MODES", True, (255, 215, 65)), (px, py))
            items = [
                ("BALANCED MODE (Standard Pacing):", "Each recommendation provides a 20-second human decision window. If expired, the co-pilot executes an emergency takeover to rescue the flight, applying an AI penalty (-50 PTS) and restricting star rating.", (75, 225, 255)),
                ("HARDCORE MODE (Expert Challenge):", "All automated takeover rescues are DISABLED. If you fail to clear aircraft before fuel exhaustion or conflicts arise, aircraft will crash. Strict human ATC responsibility.", config.COLOR_CRITICAL_RED),
                ("RELAXED MODE (Practice & Training):", "Expands decision window to 30 seconds for comfortable pacing. Recommended for learning multi-runway sequencing and emergency prioritization.", config.COLOR_PRIMARY_GREEN),
            ]
            cy = py + 28
            for header, desc, h_col in items:
                self.screen.blit(self.font_small.render(header, True, h_col), (px, cy))
                words = desc.split()
                line1, line2 = "", ""
                for w in words:
                    if len(line1 + " " + w) < 85:
                        line1 += (" " if line1 else "") + w
                    else:
                        line2 += (" " if line2 else "") + w
                self.screen.blit(self.font_tiny.render(line1, True, (180, 198, 215)), (px + 14, cy + 18))
                if line2:
                    self.screen.blit(self.font_tiny.render(line2, True, (180, 198, 215)), (px + 14, cy + 32))
                cy += 54

        elif active_tab == "SCORING":
            self.screen.blit(self.font_body_bold.render("MISSION PERFORMANCE & 3-STAR RATING", True, (255, 215, 65)), (px, py))
            star_rules = [
                ("3 STARS (Master Human ATC):", "All aircraft landed safely with 100% human clearances and ZERO automated AI rescues.", (255, 225, 65)),
                ("2 STARS (Proficient ATC):", "Successful mission with at most 1 automated AI takeover rescue.", (75, 225, 255)),
                ("1 STAR (Assisted Landing):", "Airbase secured, but required multiple AI automated rescues.", (130, 225, 160)),
                ("0 STARS (Mission Failed):", "Airfield collision occurred or 100% full automated autopilot landings (no player input).", config.COLOR_WARN_AMBER),
            ]
            cy = py + 28
            for s_hdr, s_desc, s_col in star_rules:
                self.screen.blit(self.font_small.render(s_hdr, True, s_col), (px, cy))
                self.screen.blit(self.font_tiny.render(s_desc, True, (180, 198, 215)), (px + 14, cy + 18))
                cy += 38

            pygame.draw.line(self.screen, (28, 44, 64), (px, cy + 4), (px + c_rect.w - 44, cy + 4), 1)
            pts_summary = "Touchdown: +100 PTS  |  Landing Streak Combo: +50 PTS  |  Timely Decision: +20 PTS  |  AI Rescue: -50 PTS"
            self.screen.blit(self.font_tiny.render(pts_summary, True, config.COLOR_CYAN), (px, cy + 12))

        elif active_tab == "SAFETY":
            self.screen.blit(self.font_body_bold.render("AIRFIELD SAFETY RULES & FLIGHT RESTRICTIONS", True, (255, 215, 65)), (px, py))
            rules = [
                ("1. Emergency Priority (Red Flights):", "Aircraft with critical fuel (<20%) or engine problems declare emergency. They hold top priority and must be cleared immediately ahead of routine flights.", config.COLOR_CRITICAL_RED),
                ("2. Runway Length Constraints:", "Heavy widebody aircraft require long runways (>=1800m). Assigning a heavy jet to an undersized runway violates safety guardrails and will be rejected.", config.COLOR_WHITE),
                ("3. Runway Separation & Occupancy:", "Only one aircraft may land or rollout on a runway at a time. Routing a second flight to an active runway causes collision.", config.COLOR_WARN_AMBER),
                ("4. Holding Fuel Exhaustion:", "Aircraft in holding orbits continuously consume fuel. If fuel drops to 0% before touching down, the aircraft will crash.", config.COLOR_WHITE),
            ]
            cy = py + 28
            for r_hdr, r_desc, r_col in rules:
                self.screen.blit(self.font_small.render(r_hdr, True, r_col), (px, cy))
                self.screen.blit(self.font_tiny.render(r_desc, True, (180, 198, 215)), (px + 14, cy + 18))
                cy += 44

    # =========================================================================
    # SCREEN 4: AI & DB STATS
    # =========================================================================

    def render_ai_stats(
        self,
        airbase: Airbase,
        global_stats: Dict[str, int],
        dash_data: Dict[str, Any],
        log_scroll: int,
        export_toast: str,
        mysql_ok: bool,
        ai_ready: bool,
    ):
        self.screen.blit(self._terrain_cache, (0, 0))
        self._draw_airbase_tarmac_and_runways(airbase)

        dim = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 18, 28, 178))
        self.screen.blit(dim, (0, 0))

        self._draw_top_hud_bar(
            landed_count=global_stats.get("aircraft_landed", 0),
            score_label="HI-SCORE",
            score_val=global_stats.get("hi_score", 0),
            mysql_ok=mysql_ok,
            ai_ready=ai_ready,
            extra_text="DIAGNOSTICS & TELEMETRY",
            show_debug_box=True,
        )

        cx = config.WINDOW_WIDTH // 2
        stats_title = self.font_title.render("AI & DB STATS", True, config.COLOR_CYAN)
        self.screen.blit(stats_title, stats_title.get_rect(center=(cx, 84)))
        sub = self.font_sub.render("HISTORICAL PERFORMANCE & DATABASE RECORDS", True, config.COLOR_WHITE)
        self.screen.blit(sub, sub.get_rect(center=(cx, 118)))

        # Card 1: GENERAL MISSION STATS
        c1 = pygame.Rect(60, 148, 590, 195)
        pygame.draw.rect(self.screen, (18, 30, 48), c1, border_radius=10)
        pygame.draw.rect(self.screen, config.COLOR_CYAN, c1, 2, border_radius=10)
        self.screen.blit(self.font_header.render("GENERAL MISSION STATS", True, config.COLOR_CYAN), (c1.x + 18, c1.y + 12))

        mini_stats = [
            ("TOTAL MISSIONS:", f"{dash_data['total_missions']}", config.COLOR_WHITE, c1.x + 18, c1.y + 44),
            ("EMERGENCIES HANDLED:", f"{dash_data['emergencies_handled']}", config.COLOR_CRITICAL_RED, c1.x + 305, c1.y + 44),
            ("SUCCESSFUL LANDINGS:", f"{dash_data['successful_landings']} ({dash_data['landing_rate']}%)", config.COLOR_PRIMARY_GREEN, c1.x + 18, c1.y + 116),
            ("ACCUMULATED REWARDS:", f"{dash_data['accumulated_rewards']:+d} PTS", (245, 215, 70), c1.x + 305, c1.y + 116),
        ]
        for label, val, col, mx, my in mini_stats:
            box = pygame.Rect(mx, my, 268, 62)
            pygame.draw.rect(self.screen, config.COLOR_CARD_BG, box, border_radius=6)
            self.screen.blit(self.font_tiny.render(label, True, config.COLOR_TEXT_MUTED), (mx + 12, my + 8))
            self.screen.blit(self.font_big_stat.render(val, True, col), (mx + 12, my + 27))

        # Card 2: AI PERFORMANCE
        c2 = pygame.Rect(675, 148, 625, 195)
        pygame.draw.rect(self.screen, (18, 30, 48), c2, border_radius=10)
        pygame.draw.rect(self.screen, config.COLOR_WARN_AMBER, c2, 2, border_radius=10)
        self.screen.blit(self.font_header.render("AI PERFORMANCE", True, config.COLOR_WARN_AMBER), (c2.x + 18, c2.y + 12))

        self.screen.blit(self.font_tiny.render("AI VS PLAYER ACCURACY", True, config.COLOR_TEXT_MUTED), (c2.x + 225, c2.y + 38))
        for label, pct, col, by in [
            ("PLAYER", dash_data["player_accuracy"], config.COLOR_PRIMARY_GREEN, c2.y + 58),
            ("AI", dash_data["ai_accuracy"], config.COLOR_CYAN, c2.y + 84),
        ]:
            self.screen.blit(self.font_tiny.render(label, True, col), (c2.x + 20, by))
            bar = pygame.Rect(c2.x + 82, by + 2, 470, 12)
            pygame.draw.rect(self.screen, (32, 46, 66), bar, border_radius=5)
            pygame.draw.rect(self.screen, col, (bar.x, bar.y, int(bar.w * min(1.0, pct / 100.0)), bar.h), border_radius=5)
            self.screen.blit(self.font_tiny.render(f"{pct:.0f}%", True, config.COLOR_WHITE), (bar.right + 10, by))

        avg_ms = float(dash_data.get("avg_ai_decision_ms", 0.0))
        if avg_ms <= 0.0:
            avg_ms = float(dash_data.get("avg_ai_decision_sec", 0.0)) * 1000.0
        dec_time_str = f"{avg_ms:.1f} ms" if avg_ms < 100.0 else f"{dash_data['avg_ai_decision_sec']:.2f}s"

        ai_cols = [
            ("AI DECISION TIME:", dec_time_str, config.COLOR_WHITE, c2.x + 24),
            ("VALIDATION REJECTIONS:", f"{dash_data['validation_rejections']} ({dash_data['validation_rejection_rate']}%)", config.COLOR_WARN_AMBER, c2.x + 220),
            ("TIMEOUT AUTO-EXECUTE:", f"{dash_data['timeout_auto_executes']}", config.COLOR_CYAN, c2.x + 445),
        ]
        for lbl, val, col, ax in ai_cols:
            self.screen.blit(self.font_tiny.render(lbl, True, config.COLOR_TEXT_MUTED), (ax, c2.y + 122))
            self.screen.blit(self.font_big_stat.render(val, True, col), (ax, c2.y + 144))

        # Card 3: DATABASE LOGS (Scrollable Table)
        c3 = pygame.Rect(60, 362, 860, 294)
        pygame.draw.rect(self.screen, (18, 30, 48), c3, border_radius=10)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, c3, 1, border_radius=10)
        self.screen.blit(self.font_header.render("DATABASE LOGS", True, config.COLOR_WHITE), (c3.x + 18, c3.y + 12))

        hdr = "REQ ID   FLIGHT ID    EVENT TYPE             AI SUGGESTION   RESULT        SCORE"
        pygame.draw.rect(self.screen, config.COLOR_CARD_BG, (c3.x + 14, c3.y + 38, c3.w - 60, 24), border_radius=4)
        self.screen.blit(self.font_mono_sm.render(hdr, True, config.COLOR_TEXT_MUTED), (c3.x + 24, c3.y + 43))

        logs = dash_data.get("recent_logs", [])
        visible_rows = logs[log_scroll:log_scroll + 8]
        ry = c3.y + 70
        if not visible_rows:
            self.screen.blit(self.font_body.render("No operational database records yet. Play a level to record telemetry.", True, config.COLOR_TEXT_DIM), (c3.x + 24, ry + 10))
        else:
            for row in visible_rows:
                res = row["result"]
                if res == "Success":
                    r_col = config.COLOR_PRIMARY_GREEN
                elif res == "Override":
                    r_col = config.COLOR_WARN_AMBER
                elif res == "Auto-Exec":
                    r_col = config.COLOR_CYAN
                else:
                    r_col = config.COLOR_CRITICAL_RED
                sc_str = f"{row['score']:+d}"
                line = f"{row['req_id']:<8} {row['flight_id']:<12} {row['event_type']:<22} {row['ai_suggestion']:<15} {res:<13} {sc_str}"
                self.screen.blit(self.font_mono_sm.render(line, True, r_col), (c3.x + 24, ry))
                ry += 26

        # Card 4: LEVEL COMPLETION HISTORY
        c4 = pygame.Rect(945, 362, 355, 294)
        pygame.draw.rect(self.screen, (18, 30, 48), c4, border_radius=10)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BORDER, c4, 1, border_radius=10)
        self.screen.blit(self.font_header.render("LEVEL COMPLETION HISTORY", True, config.COLOR_WHITE), (c4.x + 18, c4.y + 14))

        done_cnt = dash_data.get("levels_completed", 0)
        self.screen.blit(self.font_body_bold.render(f"LEVELS COMPLETED: {done_cnt}/20", True, config.COLOR_CYAN), (c4.x + 18, c4.y + 52))

        # 20-segment progress bar
        seg_x = c4.x + 18
        seg_w = 14
        for idx in range(20):
            seg_col = config.COLOR_PRIMARY_GREEN if idx < done_cnt else (38, 54, 74)
            pygame.draw.rect(self.screen, seg_col, (seg_x + idx * 16, c4.y + 82, seg_w, 24), border_radius=2)

        hi_lvl = dash_data.get("highest_completed_level", 0)
        self.screen.blit(self.font_body_bold.render(f"HIGHEST CLEARED: Level {hi_lvl:02d}", True, (245, 215, 70)), (c4.x + 18, c4.y + 132))
        hi_box = pygame.Rect(c4.x + 18, c4.y + 164, c4.w - 36, 68)
        pygame.draw.rect(self.screen, config.COLOR_CARD_BG, hi_box, border_radius=8)
        self.screen.blit(self.font_title.render(f"Level {hi_lvl:02d}", True, config.COLOR_WHITE), (hi_box.x + 20, hi_box.y + 16))

        if export_toast:
            toast_surf = self.font_small.render(export_toast, True, config.COLOR_PRIMARY_GREEN)
            self.screen.blit(toast_surf, toast_surf.get_rect(center=(cx, 665)))
