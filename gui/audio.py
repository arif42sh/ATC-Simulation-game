"""
=============================================================================
SkyATC AI - Procedural Audio Feedback Synthesizer (Game Improvement Sec 1)
Generates crisp radar emergency beeps and cockpit landing chimes in memory.
=============================================================================
"""

import math
from typing import Dict
import pygame

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class SoundManager:
    """Zero-asset procedural sound engine using pygame.mixer & numpy."""

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self._init_mixer()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            if NUMPY_AVAILABLE:
                self.sounds["emergency"] = self._synth_sequence([(880, 0.09), (0, 0.04), (880, 0.09)], volume=0.22)
                self.sounds["landing"] = self._synth_sequence([(523, 0.08), (784, 0.14)], volume=0.20)
                self.sounds["click"] = self._synth_sequence([(640, 0.04)], volume=0.14)
                self.sounds["warning"] = self._synth_sequence([(240, 0.11), (180, 0.16)], volume=0.24)
                self.sounds["victory"] = self._synth_sequence([(523, 0.09), (659, 0.09), (784, 0.18)], volume=0.22)
            self.enabled = True
        except Exception:
            self.enabled = False

    def _synth_sequence(self, notes: list[tuple[int, float]], volume: float = 0.2) -> pygame.mixer.Sound:
        sample_rate = 22050
        segments = []
        for freq, dur in notes:
            n_samples = max(1, int(sample_rate * dur))
            t = np.linspace(0, dur, n_samples, endpoint=False)
            if freq <= 0:
                wave = np.zeros(n_samples, dtype=np.float32)
            else:
                env = np.minimum(1.0, np.minimum(t * 60.0, (dur - t) * 45.0))
                wave = np.sin(2.0 * math.pi * freq * t) * env
            segments.append(wave)
        full = np.concatenate(segments)
        pcm = (full * 32767.0 * volume).astype(np.int16)
        return pygame.sndarray.make_sound(pcm)

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted

    def play(self, name: str):
        if self.enabled and not self.muted:
            snd = self.sounds.get(name)
            if snd:
                try:
                    snd.play()
                except Exception:
                    pass
