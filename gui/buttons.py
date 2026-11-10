"""
=============================================================================
SkyATC AI - Interactive GUI Buttons & Action Panel
=============================================================================
"""

import pygame
from typing import Callable, Optional, Tuple, List, Dict
import config


_BUTTON_FONT_CACHE: Dict[int, pygame.font.Font] = {}


