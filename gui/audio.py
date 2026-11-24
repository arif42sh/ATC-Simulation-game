"""
=============================================================================
SkyATC AI - Procedural Audio Feedback Synthesizer & Ambience Engine
Generates crisp radar beeps, landing chimes, and airport radar sweep ambience.
Supports universal Mono/Stereo SDL mixers and WebAudio Pygbag environments.
=============================================================================
"""

from array import array
import math
from typing import Dict, Optional, Tuple, List
import pygame

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class SoundManager:
    """Zero-asset procedural sound & ambience engine."""

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.master_volume: float = 1.0
        self.sfx_volume: float = 1.0
        self.ambience_enabled: bool = True
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.ambience_sound: Optional[pygame.mixer.Sound] = None
        self.ambience_channel: Optional[pygame.mixer.Channel] = None
        self._init_mixer()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self._generate_all_sounds()
            self.enabled = True
            if self.ambience_enabled and not self.muted:
                self.start_ambience()
        except Exception:
            self.enabled = False

    def unlock_audio(self):
        """Lazy mixer initialization after browser user gesture unlocks Web Audio."""
        if not self.enabled or not pygame.mixer.get_init():
            self._init_mixer()
        if self.enabled and self.ambience_enabled and not self.muted:
            self.start_ambience()

    def _generate_all_sounds(self):
        # 1. UI Click: crisp modern tap (650Hz, 35ms)
        self.sounds["click"] = self._synth_sequence([(650, 0.035)], volume=0.18)
        # 2. Landing / Clearance: ascending chime (523Hz, 784Hz)
        self.sounds["landing"] = self._synth_sequence([(523, 0.08), (784, 0.14)], volume=0.22)
        # 3. Touchdown Fanfare: rich 3-tone harmony
        self.sounds["touchdown"] = self._synth_sequence([(523, 0.08), (659, 0.08), (784, 0.16)], volume=0.24)
        # 4. Emergency: urgent pulsing alarm
        self.sounds["emergency"] = self._synth_sequence([(880, 0.09), (0, 0.04), (880, 0.09)], volume=0.25)
        # 5. Warning: caution tone
        self.sounds["warning"] = self._synth_sequence([(260, 0.12), (180, 0.16)], volume=0.25)
        # 6. Victory Fanfare: complete celebration arpeggio
        self.sounds["victory"] = self._synth_sequence([(523, 0.09), (659, 0.09), (784, 0.09), (1046, 0.22)], volume=0.26)
        # 7. Ambience loop (2.0s background hum and radar pulse)
        self.ambience_sound = self._synth_ambience_loop()

    def _synth_sequence(self, notes: List[Tuple[int, float]], volume: float = 0.2) -> Optional[pygame.mixer.Sound]:
        init = pygame.mixer.get_init()
        if not init:
            return None
        sample_rate, fmt, channels = init
        if channels not in (1, 2):
            channels = 2

        if NUMPY_AVAILABLE and np is not None:
            segments = []
            for freq, dur in notes:
                n_samples = max(1, int(sample_rate * dur))
                t = np.linspace(0, dur, n_samples, endpoint=False)
                if freq <= 0:
                    wave = np.zeros(n_samples, dtype=np.float32)
                else:
                    env = np.minimum(1.0, np.minimum(t * 70.0, (dur - t) * 50.0))
                    wave = np.sin(2.0 * math.pi * freq * t) * env
                segments.append(wave)
            full = np.concatenate(segments)
            pcm = (full * 32767.0 * volume).astype(np.int16)
            if channels == 2:
                pcm = np.column_stack([pcm, pcm])
            return pygame.sndarray.make_sound(pcm)

        # Pure Python array fallback
        pcm_arr = array("h")
        scale = 32767.0 * volume
        for freq, dur in notes:
            n_samples = max(1, int(sample_rate * dur))
            if freq <= 0:
                zeroes = [0] * (n_samples * channels)
                pcm_arr.extend(zeroes)
            else:
                two_pi_f = 2.0 * math.pi * freq
                for i in range(n_samples):
                    t = i / sample_rate
                    env = min(1.0, min(t * 70.0, (dur - t) * 50.0))
                    sample = int(math.sin(two_pi_f * t) * env * scale)
                    val = max(-32768, min(32767, sample))
                    if channels == 2:
                        pcm_arr.extend([val, val])
                    else:
                        pcm_arr.append(val)
        return pygame.mixer.Sound(buffer=pcm_arr)

    def _synth_ambience_loop(self) -> Optional[pygame.mixer.Sound]:
        init = pygame.mixer.get_init()
        if not init:
            return None
        sample_rate, fmt, channels = init
        if channels not in (1, 2):
            channels = 2

        dur = 2.4
        n_samples = int(sample_rate * dur)

        if NUMPY_AVAILABLE and np is not None:
            t = np.linspace(0, dur, n_samples, endpoint=False)
            # Low ambient hum (110Hz + 165Hz harmonic)
            hum = (np.sin(2.0 * np.pi * 110.0 * t) * 0.6 + np.sin(2.0 * np.pi * 165.0 * t) * 0.4) * 0.025
            # Soft radar pulse at t=0.15s
            blip = np.zeros(n_samples, dtype=np.float32)
            idx0 = int(sample_rate * 0.12)
            idx1 = int(sample_rate * 0.22)
            if idx1 > idx0:
                bt = t[idx0:idx1] - 0.12
                b_env = np.sin(np.pi * bt / 0.10)
                blip[idx0:idx1] = np.sin(2.0 * np.pi * 1050.0 * bt) * b_env * 0.05
            combined = (hum + blip) * 32767.0
            pcm = combined.astype(np.int16)
            if channels == 2:
                pcm = np.column_stack([pcm, pcm])
            return pygame.sndarray.make_sound(pcm)

        pcm_arr = array("h")
        for i in range(n_samples):
            t = i / sample_rate
            hum = (math.sin(2.0 * math.pi * 110.0 * t) * 0.6 + math.sin(2.0 * math.pi * 165.0 * t) * 0.4) * 0.025
            blip = 0.0
            if 0.12 <= t <= 0.22:
                bt = t - 0.12
                blip = math.sin(2.0 * math.pi * 1050.0 * bt) * math.sin(math.pi * bt / 0.10) * 0.05
            val = int(max(-32768, min(32767, (hum + blip) * 32767.0)))
            if channels == 2:
                pcm_arr.extend([val, val])
            else:
                pcm_arr.append(val)
        return pygame.mixer.Sound(buffer=pcm_arr)

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
        if self.enabled and not self.muted and self.sfx_volume > 0.0:
            snd = self.sounds.get(name)
            if snd:
                try:
                    snd.play()
                except Exception:
                    pass
