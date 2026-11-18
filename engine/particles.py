"""
Sistema de Partículas 3D, Rastros de Lâmina (Weapon Trails) e Ondas de Choque (Shockwaves).
Programado do zero para dar impacto visual a golpes, esquivas, fogueiras e magias do Boss.
"""

import math
import random
from dataclasses import dataclass, field
from engine.math3d import Vec3


@dataclass
class Particle3D:
    pos: Vec3
    vel: Vec3
    color: tuple[float, float, float]
    size: float
    life: float
    max_life: float
    gravity: float = 0.0
    additive: bool = True


@dataclass
class ShockwaveRing:
    center: Vec3
    radius: float
    max_radius: float
    speed: float
    color: tuple[float, float, float]
    life: float
    max_life: float
    damage: float = 0.0
    hit_player: bool = False


@dataclass
class WeaponTrailSample:
    base_pos: Vec3
    tip_pos: Vec3
    life: float
    max_life: float
    color: tuple[float, float, float]


@dataclass
class FloatingDamageText:
    pos: Vec3
    text: str
    color: tuple[int, int, int]
    life: float = 1.1
    max_life: float = 1.1


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle3D] = []
        self.shockwaves: list[ShockwaveRing] = []
        self.trails: list[WeaponTrailSample] = []
        self.floating_texts: list[FloatingDamageText] = []

    def clear(self) -> None:
        self.particles.clear()
        self.shockwaves.clear()
        self.trails.clear()
        self.floating_texts.clear()

    def add_trail_sample(
        self,
        base_pos: Vec3,
        tip_pos: Vec3,
        color: tuple[float, float, float] = (0.85, 0.9, 1.0),
        duration: float = 0.14,
    ) -> None:
        self.trails.append(
            WeaponTrailSample(
                base_pos=base_pos.copy(),
                tip_pos=tip_pos.copy(),
                life=duration,
                max_life=duration,
                color=color,
            )
        )

    def spawn_hit_sparks(
        self,
        pos: Vec3,
        color: tuple[float, float, float] = (1.0, 0.72, 0.25),
        count: int = 22,
        speed: float = 7.5,
    ) -> None:
        for _ in range(count):
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(-0.3, 1.2)
            spd = random.uniform(speed * 0.4, speed * 1.2)
            vel = Vec3(
                math.cos(theta) * math.cos(phi) * spd,
                math.sin(phi) * spd + 2.0,
                math.sin(theta) * math.cos(phi) * spd,
            )
            c = (
                min(1.0, color[0] + random.uniform(-0.1, 0.1)),
                min(1.0, max(0.0, color[1] + random.uniform(-0.15, 0.15))),
                min(1.0, max(0.0, color[2] + random.uniform(-0.1, 0.1))),
            )
            lt = random.uniform(0.22, 0.52)
            self.particles.append(
                Particle3D(
                    pos=pos.copy(),
                    vel=vel,
                    color=c,
                    size=random.uniform(0.08, 0.18),
                    life=lt,
                    max_life=lt,
                    gravity=14.0,
                    additive=True,
                )
            )

    def spawn_blood_burst(self, pos: Vec3, count: int = 16) -> None:
        for _ in range(count):
            theta = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.0, 5.5)
            vel = Vec3(
                math.cos(theta) * spd,
                random.uniform(1.0, 4.2),
                math.sin(theta) * spd,
            )
            lt = random.uniform(0.28, 0.55)
            self.particles.append(
                Particle3D(
                    pos=pos.copy(),
                    vel=vel,
                    color=(random.uniform(0.55, 0.85), 0.05, 0.06),
                    size=random.uniform(0.10, 0.20),
                    life=lt,
                    max_life=lt,
                    gravity=16.0,
                    additive=False,
                )
            )

    def spawn_estus_heal(self, center: Vec3, count: int = 34) -> None:
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0.2, 0.95)
            p = Vec3(
                center.x + math.cos(angle) * r,
                center.y + random.uniform(0.1, 1.3),
                center.z + math.sin(angle) * r,
            )
            vel = Vec3(
                math.cos(angle) * 0.6,
                random.uniform(1.8, 3.8),
                math.sin(angle) * 0.6,
            )
            lt = random.uniform(0.45, 0.95)
            self.particles.append(
                Particle3D(
                    pos=p,
                    vel=vel,
                    color=(1.0, random.uniform(0.75, 0.95), 0.25),
                    size=random.uniform(0.09, 0.18),
                    life=lt,
                    max_life=lt,
                    gravity=-1.2,
                    additive=True,
                )
            )

    def spawn_bonfire_ember(self, fire_pos: Vec3) -> None:
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(0.05, 0.42)
        p = Vec3(
            fire_pos.x + math.cos(angle) * r,
            fire_pos.y + random.uniform(0.15, 0.55),
            fire_pos.z + math.sin(angle) * r,
        )
        vel = Vec3(
            random.uniform(-0.4, 0.4),
            random.uniform(1.2, 2.8),
            random.uniform(-0.4, 0.4),
        )
        lt = random.uniform(0.6, 1.4)
        self.particles.append(
            Particle3D(
                pos=p,
                vel=vel,
                color=(1.0, random.uniform(0.35, 0.80), 0.08),
                size=random.uniform(0.07, 0.16),
                life=lt,
                max_life=lt,
                gravity=-0.3,
                additive=True,
            )
        )

    def spawn_shockwave(
        self,
        center: Vec3,
        max_radius: float = 9.0,
        speed: float = 16.0,
        color: tuple[float, float, float] = (1.0, 0.42, 0.12),
        damage: float = 0.0,
    ) -> None:
        dur = max_radius / max(1.0, speed)
        self.shockwaves.append(
            ShockwaveRing(
                center=Vec3(center.x, 0.08, center.z),
                radius=0.5,
                max_radius=max_radius,
                speed=speed,
                color=color,
                life=dur,
                max_life=dur,
                damage=damage,
                hit_player=False,
            )
        )

    def spawn_floating_text(
        self,
        pos: Vec3,
        text: str,
        color: tuple[int, int, int] = (255, 230, 180),
    ) -> None:
        self.floating_texts.append(
            FloatingDamageText(
                pos=Vec3(pos.x, pos.y + 2.2, pos.z),
                text=text,
                color=color,
                life=1.1,
                max_life=1.1,
            )
        )

    def update(self, dt: float) -> None:
        # Atualiza partículas
        alive_particles: list[Particle3D] = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0.0:
                p.vel.y -= p.gravity * dt
                p.pos = p.pos + p.vel * dt
                if p.pos.y < 0.05:
                    p.pos.y = 0.05
                    p.vel.y *= -0.35
                    p.vel.x *= 0.65
                    p.vel.z *= 0.65
                alive_particles.append(p)
        self.particles = alive_particles

        # Atualiza ondas de choque
        alive_waves: list[ShockwaveRing] = []
        for w in self.shockwaves:
            w.life -= dt
            if w.life > 0.0:
                w.radius += w.speed * dt
                alive_waves.append(w)
        self.shockwaves = alive_waves

        # Atualiza rastros de lâmina
        alive_trails: list[WeaponTrailSample] = []
        for tr in self.trails:
            tr.life -= dt
            if tr.life > 0.0:
                alive_trails.append(tr)
        self.trails = alive_trails

        # Atualiza textos flutuantes de dano
        alive_texts: list[FloatingDamageText] = []
        for ft in self.floating_texts:
            ft.life -= dt
            if ft.life > 0.0:
                ft.pos.y += 0.85 * dt
                alive_texts.append(ft)
        self.floating_texts = alive_texts
