"""
=============================================================================
SkyATC AI - Interactive GUI Buttons & Action Panel
=============================================================================
"""

import pygame
from typing import Callable, Optional, Tuple, List, Dict
import config


_BUTTON_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def get_button_font(font_size: int) -> pygame.font.Font:
    if font_size not in _BUTTON_FONT_CACHE:
        pygame.font.init()
        _BUTTON_FONT_CACHE[font_size] = pygame.font.SysFont("Segoe UI, Arial, sans-serif", font_size, bold=True)
    return _BUTTON_FONT_CACHE[font_size]


class Button:
    """Interactive rounded button with glow border, enabled/selected states, and hotkey tag."""

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        callback: Optional[Callable] = None,
        bg_color: Tuple[int, int, int] = (28, 46, 72),
        hover_color: Tuple[int, int, int] = (44, 70, 108),
        text_color: Tuple[int, int, int] = config.COLOR_WHITE,
        border_color: Tuple[int, int, int] = config.COLOR_CARD_BORDER,
        font_size: int = 14,
        enabled: bool = True,
        selected: bool = False,
        tag_icon: Optional[str] = None,  # "CHECK" or "LOCK"
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.font_size = font_size
        self.enabled = enabled
        self.selected = selected
        self.tag_icon = tag_icon
        self.is_hovered = False
        self.font = get_button_font(font_size)

    def draw(self, surface: pygame.Surface):
        if not self.enabled:
            bg = (52, 64, 78)
            border = (78, 92, 110)
            fg = (135, 148, 165)
        else:
            bg = self.hover_color if self.is_hovered else self.bg_color
            border = config.COLOR_WHITE if self.is_hovered else (config.COLOR_CYAN if self.selected else self.border_color)
            fg = config.COLOR_WHITE if self.is_hovered else self.text_color

        # Subtle drop shadow
        pygame.draw.rect(surface, (8, 14, 22), (self.rect.x + 2, self.rect.y + 3, self.rect.w, self.rect.h), border_radius=8)
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, border, self.rect, 2 if (self.is_hovered or self.selected) else 1, border_radius=8)

        text_surf = self.font.render(self.text, True, fg)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))

        # Optional corner completion/lock badge
        if self.tag_icon == "CHECK":
            cx, cy = self.rect.right - 11, self.rect.bottom - 11
            pygame.draw.circle(surface, config.COLOR_PRIMARY_GREEN, (cx, cy), 7)
            pygame.draw.lines(surface, (10, 30, 15), False, [(cx - 4, cy), (cx - 1, cy + 3), (cx + 4, cy - 3)], 2)
        elif self.tag_icon == "LOCK":
            lx, ly = self.rect.right - 14, self.rect.bottom - 14
            pygame.draw.rect(surface, (200, 180, 90), (lx, ly + 4, 10, 8), border_radius=2)
            pygame.draw.arc(surface, (200, 180, 90), (lx + 2, ly, 6, 8), 0, 3.14, 2)

