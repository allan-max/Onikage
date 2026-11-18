"""
Câmera 3D em Terceira Pessoa estilo Dark Souls / Elden Ring.
Suporta:
- Rotação orbital com o mouse (Yaw / Pitch)
- Lock-On (Travar Mira) com enquadramento dinâmico entre o jogador e o inimigo/Boss
- Tremor de câmera (Screen Shake) para golpes pesados e impactos
- Suavização exponencial (Damping)
"""

import math
import random
from engine.math3d import Vec3, clamp, lerp_angle


class ThirdPersonCamera:
    def __init__(self) -> None:
        self.position = Vec3(0.0, 4.0, -8.0)
        self.target = Vec3(0.0, 1.5, 0.0)
        self.up = Vec3(0.0, 1.0, 0.0)
        self.fovy = 55.0

        # Ângulos orbitais (em radianos)
        self.yaw = 0.0
        self.pitch = 0.32  # Ligeiramente olhando de cima

        # Distância e altura
        self.distance = 7.1
        self.pivot_height = 1.92
        self.shoulder_offset = 0.45

        # Sensibilidade do mouse
        self.mouse_sensitivity = 0.0026

        # Lock-On
        self.locked_target = None  # Referência à entidade alvo

        # Screen shake
        self.shake_timer = 0.0
        self.shake_duration = 0.0
        self.shake_intensity = 0.0

        # Limites da arena para evitar que a câmera atravesse paredes externas
        self.arena_radius = 37.0

    def add_shake(self, intensity: float, duration: float = 0.22) -> None:
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_timer = self.shake_duration

    def handle_mouse(self, dx: float, dy: float) -> None:
        if self.locked_target is not None and getattr(self.locked_target, "alive", False):
            # Quando em Lock-On, o mouse influencia só sutilmente o pitch
            self.pitch = clamp(self.pitch + dy * self.mouse_sensitivity * 0.35, 0.08, 0.85)
            return

        self.yaw -= dx * self.mouse_sensitivity
        self.pitch = clamp(self.pitch + dy * self.mouse_sensitivity, -0.15, 1.15)

    def get_forward_xz(self) -> Vec3:
        """Direção horizontal para onde a câmera está olhando."""
        fwd = self.target - self.position
        fwd.y = 0.0
        return fwd.normalized_xz()

    def get_right_xz(self) -> Vec3:
        """Vetor para a direita da câmera no plano XZ."""
        fwd = self.get_forward_xz()
        # Produto vetorial fwd x up (onde up = (0, 1, 0)) -> (-fwd.z, 0, fwd.x)
        return Vec3(-fwd.z, 0.0, fwd.x).normalized_xz()

    def update(self, dt: float, player_pos: Vec3) -> None:
        # Verifica validade do Lock-On
        if self.locked_target is not None:
            if not getattr(self.locked_target, "alive", False):
                self.locked_target = None
            elif player_pos.distance_to(self.locked_target.pos) > 32.0:
                self.locked_target = None

        pivot = Vec3(player_pos.x, player_pos.y + self.pivot_height, player_pos.z)

        if self.locked_target is not None:
            target_pos = Vec3(
                self.locked_target.pos.x,
                self.locked_target.pos.y + getattr(self.locked_target, "lock_height", 1.5),
                self.locked_target.pos.z,
            )
            to_enemy = target_pos - pivot
            dist_xz = to_enemy.length_xz()
            desired_yaw = math.atan2(-to_enemy.x, -to_enemy.z)
            self.yaw = lerp_angle(self.yaw, desired_yaw, clamp(dt * 10.0, 0.0, 1.0))

            # Ajusta pitch conforme a distância para manter o Boss inteiro na tela
            desired_pitch = clamp(0.28 + (0.012 * max(0.0, 12.0 - dist_xz)), 0.18, 0.62)
            self.pitch += (desired_pitch - self.pitch) * clamp(dt * 6.0, 0.0, 1.0)

            # Ponto de foco fica 60% no inimigo, 40% no jogador
            desired_target = pivot.lerp(target_pos, 0.58)
            dynamic_dist = clamp(self.distance + dist_xz * 0.12, 6.5, 9.5)
        else:
            desired_target = pivot
            dynamic_dist = self.distance

        # Calcula posição esférica ao redor do pivô
        horiz_dist = dynamic_dist * math.cos(self.pitch)
        vert_dist = dynamic_dist * math.sin(self.pitch)

        offset_x = math.sin(self.yaw) * horiz_dist
        offset_z = math.cos(self.yaw) * horiz_dist

        # Ligeiro deslocamento sobre o ombro direito
        right_x = -math.cos(self.yaw) * self.shoulder_offset
        right_z = math.sin(self.yaw) * self.shoulder_offset

        desired_pos = Vec3(
            pivot.x + offset_x + right_x,
            max(0.6, pivot.y + vert_dist),
            pivot.z + offset_z + right_z,
        )

        # Impede a câmera de sair dos muros da arena circular
        dist_center = desired_pos.length_xz()
        if dist_center > self.arena_radius:
            scale = self.arena_radius / dist_center
            desired_pos.x *= scale
            desired_pos.z *= scale

        # Interpolação suave da câmera
        smooth_pos = 1.0 - math.exp(-16.0 * dt)
        smooth_tgt = 1.0 - math.exp(-18.0 * dt)
        self.position = self.position.lerp(desired_pos, smooth_pos)
        self.target = self.target.lerp(desired_target, smooth_tgt)

        # Aplica Screen Shake se ativo
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            factor = (self.shake_timer / max(0.001, self.shake_duration)) * self.shake_intensity
            shake_vec = Vec3(
                random.uniform(-1.0, 1.0) * factor,
                random.uniform(-1.0, 1.0) * factor,
                random.uniform(-1.0, 1.0) * factor,
            )
            self.position = self.position + shake_vec
            self.target = self.target + shake_vec * 0.5
        else:
            self.shake_intensity = 0.0
