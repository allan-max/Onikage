"""
Biblioteca Matemática 3D feita do zero para a Engine Soulslike.
Inclui Vetores 3D, interpolação, ângulos e colisões geométricas 3D (Esfera, Cilindro/Cápsula, AABB).
"""

import math
from dataclasses import dataclass


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def copy(self) -> "Vec3":
        return Vec3(self.x, self.y, self.z)

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vec3":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vec3":
        if abs(scalar) < 1e-8:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        return math.sqrt(self.length_sq())

    def length_xz(self) -> float:
        return math.sqrt(self.x * self.x + self.z * self.z)

    def normalized(self) -> "Vec3":
        l = self.length()
        if l < 1e-8:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / l, self.y / l, self.z / l)

    def normalized_xz(self) -> "Vec3":
        l = self.length_xz()
        if l < 1e-8:
            return Vec3(0.0, 0.0, 0.0)
        return Vec3(self.x / l, 0.0, self.z / l)

    def distance_to(self, other: "Vec3") -> float:
        return (self - other).length()

    def distance_xz_to(self, other: "Vec3") -> float:
        dx = self.x - other.x
        dz = self.z - other.z
        return math.sqrt(dx * dx + dz * dz)

    def lerp(self, target: "Vec3", t: float) -> "Vec3":
        t = max(0.0, min(1.0, t))
        return Vec3(
            self.x + (target.x - self.x) * t,
            self.y + (target.y - self.y) * t,
            self.z + (target.z - self.z) * t,
        )

    def rotate_y(self, angle_rad: float) -> "Vec3":
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return Vec3(
            self.x * c + self.z * s,
            self.y,
            -self.x * s + self.z * c,
        )

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def lerp_float(a: float, b: float, t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return a + (b - a) * t


def normalize_angle(angle_rad: float) -> float:
    """Normaliza um ângulo em radianos para o intervalo [-pi, pi]."""
    while angle_rad > math.pi:
        angle_rad -= 2.0 * math.pi
    while angle_rad < -math.pi:
        angle_rad += 2.0 * math.pi
    return angle_rad


def lerp_angle(a: float, b: float, t: float) -> float:
    """Interpola suavemente entre dois ângulos respeitando a volta de 360 graus."""
    diff = normalize_angle(b - a)
    return normalize_angle(a + diff * clamp(t, 0.0, 1.0))


@dataclass
class CylinderCollider:
    """Colisor cilíndrico vertical usado para personagens, inimigos e pilares."""
    radius: float
    height: float

    def resolve_xz(self, pos_a: Vec3, other: "CylinderCollider", pos_b: Vec3) -> Vec3:
        """Retorna o vetor de separação em XZ caso dois cilindros se sobreponham."""
        dx = pos_a.x - pos_b.x
        dz = pos_a.z - pos_b.z
        dist_sq = dx * dx + dz * dz
        min_dist = self.radius + other.radius
        if dist_sq >= min_dist * min_dist:
            return Vec3(0.0, 0.0, 0.0)
        dist = math.sqrt(dist_sq)
        if dist < 1e-6:
            return Vec3(min_dist, 0.0, 0.0)
        overlap = min_dist - dist
        return Vec3((dx / dist) * overlap, 0.0, (dz / dist) * overlap)


@dataclass
class BoxCollider:
    """AABB 3D centrada em `center` com meias-extensões `half_extents`."""
    center: Vec3
    half_extents: Vec3

    def push_out_cylinder_xz(self, pos: Vec3, radius: float) -> Vec3:
        """Resolve colisão de um cilindro de raio `radius` contra esta caixa no plano XZ."""
        # Verifica se está na faixa de altura da caixa
        if pos.y > self.center.y + self.half_extents.y or (pos.y + 2.0) < self.center.y - self.half_extents.y:
            return pos

        closest_x = clamp(pos.x, self.center.x - self.half_extents.x, self.center.x + self.half_extents.x)
        closest_z = clamp(pos.z, self.center.z - self.half_extents.z, self.center.z + self.half_extents.z)

        dx = pos.x - closest_x
        dz = pos.z - closest_z
        dist_sq = dx * dx + dz * dz

        if dist_sq < radius * radius:
            dist = math.sqrt(dist_sq)
            if dist < 1e-6:
                # Dentro da caixa: empurra pelo eixo mais próximo
                pen_x = self.half_extents.x - abs(pos.x - self.center.x) + radius
                pen_z = self.half_extents.z - abs(pos.z - self.center.z) + radius
                if pen_x < pen_z:
                    sign = 1.0 if pos.x >= self.center.x else -1.0
                    return Vec3(pos.x + sign * pen_x, pos.y, pos.z)
                else:
                    sign = 1.0 if pos.z >= self.center.z else -1.0
                    return Vec3(pos.x, pos.y, pos.z + sign * pen_z)
            overlap = radius - dist
            return Vec3(pos.x + (dx / dist) * overlap, pos.y, pos.z + (dz / dist) * overlap)
        return pos


def segment_sphere_intersect(p0: Vec3, p1: Vec3, sphere_center: Vec3, sphere_radius: float) -> bool:
    """
    Testa se um segmento 3D (ex: lâmina da espada da base até a ponta)
    intercepta uma esfera de hurtbox.
    """
    seg = p1 - p0
    seg_len_sq = seg.length_sq()
    if seg_len_sq < 1e-8:
        return p0.distance_to(sphere_center) <= sphere_radius
    t = clamp((sphere_center - p0).dot(seg) / seg_len_sq, 0.0, 1.0)
    closest = p0 + seg * t
    return closest.distance_to(sphere_center) <= sphere_radius
