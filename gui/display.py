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

