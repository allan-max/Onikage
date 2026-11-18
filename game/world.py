"""
Mundo 3D, Arena Gótica, Colisores de Cenário, Fogueira (Bonfire) e Poça de Almas (Bloodstain).
"""

import math
from dataclasses import dataclass
from engine.math3d import Vec3, CylinderCollider, clamp


@dataclass
class Pillar3D:
    pos: Vec3
    radius: float
    height: float
    broken: bool = False


@dataclass
class Torch3D:
    pos: Vec3
    height: float = 2.8


@dataclass
class Bloodstain:
    pos: Vec3
    souls: int
    active: bool = False


class Bonfire:
    def __init__(self, pos: Vec3) -> None:
        self.pos = pos
        self.lit = True
        self.interact_radius = 2.8
        self.collider = CylinderCollider(radius=0.65, height=1.5)

    def can_interact(self, player_pos: Vec3) -> bool:
        return self.pos.distance_xz_to(player_pos) <= self.interact_radius


class ArenaWorld:
    def __init__(self) -> None:
        self.arena_radius = 38.0
        # Fogueira na entrada sul do pátio
        self.bonfire = Bonfire(Vec3(0.0, 0.0, 26.0))
        self.bloodstain = Bloodstain(pos=Vec3(0.0, 0.0, 0.0), souls=0, active=False)

        self.pillars: list[Pillar3D] = []
        self.torches: list[Torch3D] = []
        self._build_architecture()

    def _build_architecture(self) -> None:
        # Colunata gótica interna (8 pilares ao redor do centro da arena do Boss)
        inner_r = 16.5
        for i in range(8):
            angle = i * (2.0 * math.pi / 8.0) + (math.pi / 8.0)
            px = math.cos(angle) * inner_r
            pz = math.sin(angle) * inner_r
            broken = i in (1, 4, 6)
            h = 4.2 if broken else 7.8
            self.pillars.append(Pillar3D(pos=Vec3(px, 0.0, pz), radius=1.05, height=h, broken=broken))
            # Tocha acesa em alguns pilares
            if not broken:
                tx = math.cos(angle) * (inner_r - 1.15)
                tz = math.sin(angle) * (inner_r - 1.15)
                self.torches.append(Torch3D(pos=Vec3(tx, 2.6, tz)))

        # Pilares do corredor da Fogueira (entrada sul)
        for z_pos in (21.5, 29.5):
            for sign in (-1.0, 1.0):
                self.pillars.append(
                    Pillar3D(
                        pos=Vec3(sign * 5.2, 0.0, z_pos),
                        radius=0.85,
                        height=6.2,
                        broken=False,
                    )
                )

    def resolve_environment_collisions(self, pos: Vec3, radius: float) -> Vec3:
        """Resolve colisões contra os pilares, a fogueira e os muros circulares da catedral."""
        out = pos.copy()

        # Colisão com a Fogueira
        bf_sep = CylinderCollider(radius, 2.0).resolve_xz(out, self.bonfire.collider, self.bonfire.pos)
        out = out + bf_sep

        # Colisão com os pilares góticos
        for p in self.pillars:
            p_col = CylinderCollider(p.radius, p.height)
            sep = CylinderCollider(radius, 2.0).resolve_xz(out, p_col, p.pos)
            out = out + sep

        # Limite da muralha circular da arena
        max_r = self.arena_radius - radius - 0.5
        dist_xz = out.length_xz()
        if dist_xz > max_r:
            scale = max_r / dist_xz
            out.x *= scale
            out.z *= scale

        return out
