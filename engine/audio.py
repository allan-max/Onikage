"""
Sintetizador de Áudio Procedural feito do zero (usando NumPy + Pygame Mixer).
Gera efeitos sonoros de combate Soulslike matematicamente em tempo real,
sem depender de arquivos externos (.wav/.ogg).
"""

import numpy as np
import pygame


class SoundEngine:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
            self._generate_all_sounds()
        except Exception:
            self.enabled = False

    def _make_sound(self, mono_wave: np.ndarray, volume: float = 0.45) -> pygame.mixer.Sound:
        mono_wave = np.clip(mono_wave * volume, -1.0, 1.0)
        pcm16 = (mono_wave * 32767).astype(np.int16)
        stereo = np.column_stack((pcm16, pcm16))
        return pygame.sndarray.make_sound(stereo)

    def _generate_all_sounds(self) -> None:
        sr = 44100

        # 1. Corte de espada leve (Whoosh metálico)
        dur = 0.22
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        env = np.sin(np.pi * (t / dur)) ** 1.8
        sweep = np.sin(2 * np.pi * (280 + 420 * (1 - t / dur)) * t) * 0.35
        self.sounds["swing_light"] = self._make_sound((noise * 0.55 + sweep) * env, 0.32)

        # 2. Corte de espada pesado / Boss (Whoosh grave + ressonância metálica)
        dur = 0.38
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        env = np.sin(np.pi * (t / dur)) ** 1.5
        low_sweep = np.sin(2 * np.pi * (120 + 220 * (1 - t / dur)) * t) * 0.65
        self.sounds["swing_heavy"] = self._make_sound((noise * 0.5 + low_sweep) * env, 0.42)

        # 3. Impacto de espada em carne/armadura (Hit)
        dur = 0.25
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-t * 18.0)
        thud = np.sin(2 * np.pi * (140 * np.exp(-t * 8.0)) * t)
        metal = (
            np.sin(2 * np.pi * 1180 * t) * 0.25
            + np.sin(2 * np.pi * 1740 * t) * 0.15
        ) * np.exp(-t * 25.0)
        crunch = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 24.0) * 0.45
        self.sounds["hit"] = self._make_sound((thud * 0.7 + metal + crunch) * env, 0.55)

        # 4. Bloqueio no escudo (Clang metálico)
        dur = 0.32
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-t * 14.0)
        clang = (
            np.sin(2 * np.pi * 640 * t) * 0.4
            + np.sin(2 * np.pi * 980 * t) * 0.35
            + np.sin(2 * np.pi * 1520 * t) * 0.25
        )
        noise = np.random.uniform(-0.4, 0.4, len(t)) * np.exp(-t * 30.0)
        self.sounds["block"] = self._make_sound((clang + noise) * env, 0.48)

        # 5. Parry / Quebra de Postura (Som icônico grave + sino ressonante de Dark Souls!)
        dur = 0.85
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        sub_boom = np.sin(2 * np.pi * (95 * np.exp(-t * 2.5)) * t) * np.exp(-t * 4.0)
        bell = (
            np.sin(2 * np.pi * 528 * t) * 0.45
            + np.sin(2 * np.pi * 792 * t) * 0.30
            + np.sin(2 * np.pi * 1320 * t) * 0.25
        ) * np.exp(-t * 4.5)
        self.sounds["parry"] = self._make_sound(sub_boom * 0.65 + bell * 0.6, 0.65)

        # 6. Esquiva (Roll)
        dur = 0.20
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.sin(np.pi * (t / dur))
        thump = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 15.0) * 0.6
        cloth = np.random.uniform(-0.6, 0.6, len(t)) * env * 0.4
        self.sounds["roll"] = self._make_sound(thump + cloth, 0.36)

        # 7. Frasco de Estus / Cura (Brilho cristalino ascendente)
        dur = 0.65
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.sin(np.pi * (t / dur)) * np.exp(-t * 2.2)
        chime = (
            np.sin(2 * np.pi * (440 + 220 * (t / dur)) * t) * 0.45
            + np.sin(2 * np.pi * (880 + 440 * (t / dur)) * t) * 0.35
            + np.sin(2 * np.pi * 1320 * t) * 0.2
        )
        self.sounds["estus"] = self._make_sound(chime * env, 0.42)

        # 8. Golpe esmagador no chão (Boss Slam / Shockwave)
        dur = 0.60
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-t * 6.5)
        boom = np.sin(2 * np.pi * (75 * np.exp(-t * 3.0)) * t) * 0.8
        rumble = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t * 8.0) * 0.55
        self.sounds["slam"] = self._make_sound((boom + rumble) * env, 0.62)

        # 9. Morte / Banner ("YOU DIED" / "GREAT ENEMY FELLED")
        dur = 1.4
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-t * 2.2)
        chord = (
            np.sin(2 * np.pi * 110 * t) * 0.5
            + np.sin(2 * np.pi * 164.8 * t) * 0.35
            + np.sin(2 * np.pi * 220 * t) * 0.3
            + np.sin(2 * np.pi * 554.37 * t) * 0.2 * np.exp(-t * 4.0)
        )
        self.sounds["banner"] = self._make_sound(chord * env, 0.55)

        # 10. Navegação no Menu Inicial (Clique metálico suave)
        dur = 0.09
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-t * 38.0)
        tick = np.sin(2 * np.pi * 660 * t) * 0.6 + np.sin(2 * np.pi * 1320 * t) * 0.4
        self.sounds["menu_move"] = self._make_sound(tick * env, 0.28)

        # 11. Confirmar no Menu Inicial ("Press Start" ressonante estilo Dark Souls)
        dur = 1.25
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        env = np.exp(-t * 2.8)
        start_chime = (
            np.sin(2 * np.pi * 146.83 * t) * 0.45
            + np.sin(2 * np.pi * 220.0 * t) * 0.35
            + np.sin(2 * np.pi * 293.66 * t) * 0.35
            + np.sin(2 * np.pi * 440.0 * t) * 0.25
            + np.sin(2 * np.pi * 880.0 * t) * 0.18 * np.exp(-t * 5.0)
        )
        self.sounds["menu_confirm"] = self._make_sound(start_chime * env, 0.55)

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()
