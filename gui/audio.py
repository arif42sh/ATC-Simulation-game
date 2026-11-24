"""
=============================================================================
SkyATC AI - Audio Manager (MP3 / WAV / OGG Asset Loader)
Ready for user-provided MP3/WAV/OGG sound assets.
Procedural synthetic audio has been removed so custom MP3 audio can be added.
=============================================================================
"""

import os
from pathlib import Path
from typing import Dict, Optional, List
import pygame

# Backward compatibility with test harness
NUMPY_AVAILABLE = False


class SoundManager:
    """Manages playback of user-provided MP3, WAV, and OGG audio assets."""

    SOUND_NAMES = ["click", "landing", "touchdown", "emergency", "warning", "victory"]

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.master_volume: float = 1.0
        self.sfx_volume: float = 1.0
        self.ambience_enabled: bool = True
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {k: None for k in self.SOUND_NAMES}
        self.ambience_sound: Optional[pygame.mixer.Sound] = None
        self.ambience_channel: Optional[pygame.mixer.Channel] = None
        self.assets_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"
        self._init_mixer()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self._load_user_assets()
            has_files = any(s is not None for s in self.sounds.values()) or (self.ambience_sound is not None)
            self.enabled = has_files
        except Exception:
            self.enabled = False

    def unlock_audio(self):
        """Lazy mixer initialization after browser user gesture unlocks Web Audio."""
        if not pygame.mixer.get_init():
            self._init_mixer()

    def _load_user_assets(self):
        """Discovers and loads any user-provided MP3/WAV/OGG sound files."""
        if not self.assets_dir.exists():
            return

        extensions = [".mp3", ".wav", ".ogg"]
        for name in self.SOUND_NAMES:
            for ext in extensions:
                file_path = self.assets_dir / f"{name}{ext}"
                if file_path.exists():
                    try:
                        self.sounds[name] = pygame.mixer.Sound(str(file_path))
                        break
                    except Exception:
                        pass

        for ext in extensions:
            amb_path = self.assets_dir / f"ambience{ext}"
            if amb_path.exists():
                try:
                    self.ambience_sound = pygame.mixer.Sound(str(amb_path))
                    break
                except Exception:
                    pass

    def start_ambience(self):
        if not self.enabled or self.muted or not self.ambience_enabled or not self.ambience_sound:
            return
        try:
            if self.ambience_channel is None:
                self.ambience_channel = pygame.mixer.Channel(7)
            vol = 0.35 * self.master_volume * (1.0 if self.ambience_enabled else 0.0)
            self.ambience_channel.set_volume(vol)
            if not self.ambience_channel.get_busy():
                self.ambience_channel.play(self.ambience_sound, loops=-1)
        except Exception:
            pass

    def stop_ambience(self):
        if self.ambience_channel is not None:
            try:
                self.ambience_channel.stop()
            except Exception:
                pass

    def set_master_volume(self, vol: float):
        self.master_volume = max(0.0, min(1.0, vol))
        self.muted = (self.master_volume <= 0.0)
        self._update_volumes()

    def set_sfx_volume(self, vol: float):
        self.sfx_volume = max(0.0, min(1.0, vol))
        self._update_volumes()

    def set_ambience_enabled(self, enabled: bool):
        self.ambience_enabled = enabled
        if enabled and not self.muted:
            self.start_ambience()
        else:
            self.stop_ambience()

    def _update_volumes(self):
        eff_vol = 0.0 if self.muted else (self.master_volume * self.sfx_volume)
        for snd in self.sounds.values():
            if snd:
                try:
                    snd.set_volume(eff_vol)
                except Exception:
                    pass
        if self.ambience_channel is not None:
            amb_vol = 0.0 if (self.muted or not self.ambience_enabled) else (0.35 * self.master_volume)
            try:
                self.ambience_channel.set_volume(amb_vol)
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        self._update_volumes()
        if self.muted:
            self.stop_ambience()
        elif self.ambience_enabled:
            self.start_ambience()
        return self.muted

    def play(self, name: str):
        if not self.muted and self.sfx_volume > 0.0:
            snd = self.sounds.get(name)
            if snd:
                try:
                    snd.play()
                except Exception:
                    pass
