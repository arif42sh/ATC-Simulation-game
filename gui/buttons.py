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

