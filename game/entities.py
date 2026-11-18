"""
Entidades do Jogo:
- Player (Cavaleiro das Cinzas) com atributos RPG, Máquina de Estados, I-Frames, Combos, Parry, Estus
- HollowEnemy (Guardião Vazio) com IA de patrulha e combate
- Boss (Malakor, Lorde das Cinzas) com IA de 2 Fases, ataques telegrafados, Poise/Stagger e Ondas de Choque
"""

import math
import random
from enum import Enum, auto
from engine.math3d import Vec3, CylinderCollider, clamp, lerp_angle, normalize_angle


class PlayerState(Enum):
    IDLE = auto()
    MOVE = auto()
    SPRINT = auto()
    ROLL = auto()
    LIGHT_1 = auto()
    LIGHT_2 = auto()
    LIGHT_3 = auto()
    HEAVY = auto()
    BLOCK = auto()
    PARRY = auto()
    ESTUS = auto()
    STAGGER = auto()
    DEAD = auto()


class Player:
    def __init__(self, spawn_pos: Vec3) -> None:
        self.spawn_pos = spawn_pos.copy()
        self.pos = spawn_pos.copy()
        self.vel = Vec3(0.0, 0.0, 0.0)
        self.facing_yaw = math.pi  # Olhando para o norte (-Z, direção da arena)
        self.collider = CylinderCollider(radius=0.52, height=1.85)
        self.hurt_radius = 0.65

        # Atributos RPG (Soulslike Level Up)
        self.level = 1
        self.vigor = 10       # Aumenta HP máximo
        self.endurance = 10   # Aumenta Stamina máxima
        self.strength = 10    # Aumenta dano físico
        self.souls = 0

        # Status derivados
        self.max_hp = 450.0
        self.hp = self.max_hp
        self.hp_trail = self.max_hp

        self.max_stamina = 120.0
        self.stamina = self.max_stamina
        self.stamina_regen_delay = 0.0

        self.max_poise = 60.0
        self.poise = self.max_poise
        self.poise_reset_timer = 0.0

        # Frasco de Cinzas (Estus Flask)
        self.max_estus = 5
        self.estus = self.max_estus
        self.estus_heal_amount = 240.0
        self.healed_in_current_anim = False

        # Máquina de estados
        self.state = PlayerState.IDLE
        self.state_timer = 0.0
        self.state_duration = 0.0
        self.queued_attack: PlayerState | None = None
        self.roll_dir = Vec3(0.0, 0.0, -1.0)
        self.hit_targets_this_swing: set[int] = set()
        self.walk_cycle = 0.0
        self.alive = True
        self.recalc_stats(full_restore=True)

    def get_level_up_cost(self) -> int:
        return int(250 + (self.level - 1) * 175)

    def recalc_stats(self, full_restore: bool = False) -> None:
        old_max_hp = self.max_hp
        self.max_hp = 350.0 + (self.vigor - 10) * 45.0 + 100.0
        self.max_stamina = 100.0 + (self.endurance - 10) * 14.0 + 20.0
        if full_restore:
            self.hp = self.max_hp
            self.hp_trail = self.max_hp
            self.stamina = self.max_stamina
        else:
            self.hp += max(0.0, self.max_hp - old_max_hp)

    def get_attack_damage(self) -> float:
        base = 52.0 + (self.strength - 10) * 8.5
        if self.state == PlayerState.LIGHT_1:
            return base * 1.0
        elif self.state == PlayerState.LIGHT_2:
            return base * 1.15
        elif self.state == PlayerState.LIGHT_3:
            return base * 1.40
        elif self.state == PlayerState.HEAVY:
            return base * 1.85
        return base

    def get_poise_damage(self) -> float:
        if self.state == PlayerState.HEAVY:
            return 48.0
        elif self.state == PlayerState.LIGHT_3:
            return 34.0
        return 22.0

    def reset_at_bonfire(self) -> None:
        self.recalc_stats(full_restore=True)
        self.estus = self.max_estus
        self.poise = self.max_poise
        self.state = PlayerState.IDLE
        self.state_timer = 0.0
        self.queued_attack = None
        self.alive = True

    def is_invulnerable(self) -> bool:
        """Retorna True durante os I-Frames da esquiva (Roll)."""
        if self.state == PlayerState.ROLL:
            return 0.04 <= self.state_timer <= 0.36
        return False

    def is_in_parry_window(self) -> bool:
        """Retorna True durante os frames ativos do Parry com escudo."""
        if self.state == PlayerState.PARRY:
            return 0.04 <= self.state_timer <= 0.25
        return False

    def is_attack_active(self) -> bool:
        """Retorna True durante os Active Frames (quando a espada corta e tem hitbox ativa)."""
        t = self.state_timer
        if self.state == PlayerState.LIGHT_1:
            return 0.14 <= t <= 0.31
        elif self.state == PlayerState.LIGHT_2:
            return 0.13 <= t <= 0.30
        elif self.state == PlayerState.LIGHT_3:
            return 0.18 <= t <= 0.38
        elif self.state == PlayerState.HEAVY:
            return 0.32 <= t <= 0.56
        return False

    def consume_stamina(self, amount: float) -> None:
        self.stamina = max(-10.0, self.stamina - amount)
        self.stamina_regen_delay = 0.68

    def start_roll(self, move_dir: Vec3, sound_engine) -> bool:
        if self.stamina <= 2.0:
            return False
        if self.state in (PlayerState.DEAD, PlayerState.STAGGER, PlayerState.ROLL):
            return False
        # Permite cancelar recuperação de ataque em esquiva (dodge cancel no final do golpe)
        if self.state in (PlayerState.LIGHT_1, PlayerState.LIGHT_2, PlayerState.LIGHT_3, PlayerState.HEAVY):
            if self.state_timer < self.state_duration * 0.62:
                return False

        self.consume_stamina(22.0)
        self.state = PlayerState.ROLL
        self.state_timer = 0.0
        self.state_duration = 0.48
        self.queued_attack = None
        if move_dir.length_xz() > 0.1:
            self.roll_dir = move_dir.normalized_xz()
            self.facing_yaw = math.atan2(self.roll_dir.x, self.roll_dir.z)
        else:
            self.roll_dir = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
        sound_engine.play("roll")
        return True

    def request_light_attack(self, sound_engine) -> None:
        if self.stamina <= 2.0 or not self.alive:
            return
        if self.state in (PlayerState.IDLE, PlayerState.MOVE, PlayerState.SPRINT, PlayerState.BLOCK):
            self._enter_attack(PlayerState.LIGHT_1, 0.48, 18.0, "swing_light", sound_engine)
        elif self.state == PlayerState.LIGHT_1 and self.state_timer >= 0.20:
            self.queued_attack = PlayerState.LIGHT_2
        elif self.state == PlayerState.LIGHT_2 and self.state_timer >= 0.20:
            self.queued_attack = PlayerState.LIGHT_3

    def request_heavy_attack(self, sound_engine) -> None:
        if self.stamina <= 5.0 or not self.alive:
            return
        if self.state in (PlayerState.IDLE, PlayerState.MOVE, PlayerState.SPRINT, PlayerState.BLOCK):
            self._enter_attack(PlayerState.HEAVY, 0.78, 32.0, "swing_heavy", sound_engine)
        elif self.state in (PlayerState.LIGHT_1, PlayerState.LIGHT_2) and self.state_timer >= 0.22:
            self.queued_attack = PlayerState.HEAVY

    def request_parry(self, sound_engine) -> None:
        if self.stamina <= 5.0 or not self.alive:
            return
        if self.state in (PlayerState.IDLE, PlayerState.MOVE, PlayerState.SPRINT, PlayerState.BLOCK):
            self.consume_stamina(16.0)
            self.state = PlayerState.PARRY
            self.state_timer = 0.0
            self.state_duration = 0.44
            sound_engine.play("swing_light")

    def request_estus(self) -> None:
        if self.estus <= 0 or not self.alive:
            return
        if self.state in (PlayerState.IDLE, PlayerState.MOVE, PlayerState.SPRINT, PlayerState.BLOCK):
            self.estus -= 1
            self.state = PlayerState.ESTUS
            self.state_timer = 0.0
            self.state_duration = 0.85
            self.healed_in_current_anim = False

    def _enter_attack(
        self,
        atk_state: PlayerState,
        duration: float,
        stam_cost: float,
        snd_name: str,
        sound_engine,
    ) -> None:
        self.consume_stamina(stam_cost)
        self.state = atk_state
        self.state_timer = 0.0
        self.state_duration = duration
        self.queued_attack = None
        self.hit_targets_this_swing.clear()
        sound_engine.play(snd_name)

    def get_sword_segment(self) -> tuple[Vec3, Vec3]:
        """Calcula no espaço 3D a posição da mão/guarda e da ponta da espada do jogador."""
        fwd = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
        right = Vec3(math.cos(self.facing_yaw), 0.0, -math.sin(self.facing_yaw))

        hand_base = Vec3(self.pos.x, self.pos.y + 1.38, self.pos.z) + right * 0.32 + fwd * 0.25
        sword_len = 1.46

        t = clamp(self.state_timer / max(0.001, self.state_duration), 0.0, 1.0)
        if self.state == PlayerState.LIGHT_1:
            # Corte horizontal da direita para a esquerda
            swing_ang = (0.5 - t) * 2.5
            dir_vec = (fwd * math.cos(swing_ang) + right * math.sin(swing_ang)).normalized()
            tip = hand_base + dir_vec * sword_len
        elif self.state == PlayerState.LIGHT_2:
            # Corte reverso da esquerda para a direita
            swing_ang = (t - 0.5) * 2.5
            dir_vec = (fwd * math.cos(swing_ang) + right * math.sin(swing_ang)).normalized()
            tip = hand_base + dir_vec * sword_len
        elif self.state == PlayerState.LIGHT_3:
            # Estocada / Corte giratório profundo à frente
            hand_base = hand_base + fwd * (math.sin(t * math.pi) * 0.75)
            tip = hand_base + fwd * (sword_len + 0.35)
        elif self.state == PlayerState.HEAVY:
            # Golpe vertical esmagador de cima para baixo
            elev = math.cos(t * math.pi) * 1.15
            dir_vec = Vec3(fwd.x, elev, fwd.z).normalized()
            tip = hand_base + dir_vec * (sword_len + 0.25)
        else:
            tip = hand_base + Vec3(fwd.x * 0.5, 0.85, fwd.z * 0.5).normalized() * sword_len

        return hand_base, tip

    def take_hit(
        self,
        damage: float,
        poise_dmg: float,
        attacker_pos: Vec3,
        sound_engine,
        particles,
        camera,
    ) -> str:
        """
        Processa um golpe recebido pelo jogador.
        Retorna: 'ignored' (i-frames), 'parried', 'blocked' ou 'hit'.
        """
        if not self.alive or self.is_invulnerable():
            return "ignored"

        to_attacker = (attacker_pos - self.pos).normalized_xz()
        facing_vec = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
        in_front = facing_vec.dot(to_attacker) > -0.15

        # 1. Verifica Parry!
        if self.is_in_parry_window() and in_front:
            sound_engine.play("parry")
            particles.spawn_hit_sparks(
                Vec3(self.pos.x, self.pos.y + 1.25, self.pos.z) + facing_vec * 0.6,
                color=(0.45, 0.88, 1.0),
                count=36,
                speed=10.5,
            )
            camera.add_shake(0.35, 0.28)
            self.stamina = min(self.max_stamina, self.stamina + 30.0)
            return "parried"

        # 2. Verifica Bloqueio com Escudo!
        if self.state == PlayerState.BLOCK and in_front:
            stam_drain = damage * 0.55
            self.consume_stamina(stam_drain)
            if self.stamina > 0.0:
                chip_dmg = damage * 0.12
                self.hp = max(1.0, self.hp - chip_dmg)
                sound_engine.play("block")
                particles.spawn_hit_sparks(
                    Vec3(self.pos.x, self.pos.y + 1.2, self.pos.z) + facing_vec * 0.5,
                    color=(1.0, 0.82, 0.35),
                    count=20,
                    speed=6.5,
                )
                camera.add_shake(0.18, 0.15)
                # Pequeno recuo no bloqueio
                self.pos = self.pos - to_attacker * 0.45
                return "blocked"
            else:
                # Guard Break! (Escudo quebrado por falta de stamina)
                sound_engine.play("slam")

        # 3. Dano direto!
        self.hp = max(0.0, self.hp - damage)
        self.poise -= poise_dmg
        self.poise_reset_timer = 4.0
        sound_engine.play("hit")
        particles.spawn_blood_burst(Vec3(self.pos.x, self.pos.y + 1.15, self.pos.z), count=20)
        particles.spawn_floating_text(self.pos, f"-{int(damage)}", color=(240, 75, 75))
        camera.add_shake(0.32, 0.25)

        if self.hp <= 0.0:
            self.alive = False
            self.state = PlayerState.DEAD
            self.state_timer = 0.0
            sound_engine.play("banner")
            return "hit"

        if self.poise <= 0.0:
            self.poise = self.max_poise
            self.state = PlayerState.STAGGER
            self.state_timer = 0.0
            self.state_duration = 0.52
            self.queued_attack = None
            self.pos = self.pos - to_attacker * 0.55

        return "hit"

    def update(
        self,
        dt: float,
        move_input: Vec3,
        want_sprint: bool,
        want_block: bool,
        locked_target,
        sound_engine,
        particles,
    ) -> None:
        # Atualiza barra amarela de dano recente (trail)
        if self.hp_trail > self.hp:
            self.hp_trail = max(self.hp, self.hp_trail - 95.0 * dt)
        else:
            self.hp_trail = self.hp

        if not self.alive:
            self.state_timer += dt
            return

        # Regeneração de Poise
        if self.poise_reset_timer > 0.0:
            self.poise_reset_timer -= dt
        else:
            self.poise = min(self.max_poise, self.poise + 20.0 * dt)

        # Regeneração de Stamina
        if self.stamina_regen_delay > 0.0:
            self.stamina_regen_delay -= dt
        else:
            regen_rate = 14.0 if self.state == PlayerState.BLOCK else 42.0
            if self.state not in (PlayerState.SPRINT, PlayerState.ROLL):
                self.stamina = min(self.max_stamina, self.stamina + regen_rate * dt)

        self.state_timer += dt

        # Orienta para o alvo travado (Lock-On) quando atacando ou defendendo
        if locked_target is not None and getattr(locked_target, "alive", False):
            if self.state in (
                PlayerState.IDLE,
                PlayerState.MOVE,
                PlayerState.BLOCK,
                PlayerState.LIGHT_1,
                PlayerState.LIGHT_2,
                PlayerState.LIGHT_3,
                PlayerState.HEAVY,
            ):
                to_target = (locked_target.pos - self.pos).normalized_xz()
                if to_target.length_xz() > 0.01:
                    target_yaw = math.atan2(to_target.x, to_target.z)
                    self.facing_yaw = lerp_angle(self.facing_yaw, target_yaw, clamp(dt * 14.0, 0.0, 1.0))

        # Máquina de estados
        if self.state == PlayerState.ROLL:
            # Velocidade maior no início da esquiva e desacelera no final
            progress = self.state_timer / max(0.001, self.state_duration)
            roll_speed = 11.2 * (1.0 - 0.55 * progress)
            self.pos = self.pos + self.roll_dir * (roll_speed * dt)
            if self.state_timer >= self.state_duration:
                self.state = PlayerState.IDLE
                self.state_timer = 0.0

        elif self.state in (PlayerState.LIGHT_1, PlayerState.LIGHT_2, PlayerState.LIGHT_3, PlayerState.HEAVY):
            # Ligeiro avanço (step-in) durante o início do golpe
            if self.state_timer < self.state_duration * 0.45:
                fwd = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
                step_spd = 4.2 if self.state == PlayerState.HEAVY else 2.8
                self.pos = self.pos + fwd * (step_spd * dt)

            # Emite rastro de lâmina 3D nos frames ativos
            if self.is_attack_active():
                b_pos, t_pos = self.get_sword_segment()
                trail_col = (1.0, 0.78, 0.35) if self.state == PlayerState.HEAVY else (0.82, 0.90, 1.0)
                particles.add_trail_sample(b_pos, t_pos, color=trail_col, duration=0.14)

            # Transição para o próximo golpe do combo na janela de combo
            if self.queued_attack is not None and self.state_timer >= self.state_duration * 0.66:
                nxt = self.queued_attack
                self.queued_attack = None
                if nxt == PlayerState.LIGHT_2:
                    self._enter_attack(PlayerState.LIGHT_2, 0.46, 18.0, "swing_light", sound_engine)
                elif nxt == PlayerState.LIGHT_3:
                    self._enter_attack(PlayerState.LIGHT_3, 0.56, 22.0, "swing_heavy", sound_engine)
                elif nxt == PlayerState.HEAVY:
                    self._enter_attack(PlayerState.HEAVY, 0.75, 30.0, "swing_heavy", sound_engine)
                return

            if self.state_timer >= self.state_duration:
                self.state = PlayerState.IDLE
                self.state_timer = 0.0

        elif self.state == PlayerState.PARRY:
            if self.state_timer >= self.state_duration:
                self.state = PlayerState.IDLE
                self.state_timer = 0.0

        elif self.state == PlayerState.ESTUS:
            # Movimento lento enquanto bebe o Estus
            if move_input.length_xz() > 0.1:
                self.pos = self.pos + move_input * (1.8 * dt)
            if not self.healed_in_current_anim and self.state_timer >= 0.36:
                self.healed_in_current_anim = True
                self.hp = min(self.max_hp, self.hp + self.estus_heal_amount)
                sound_engine.play("estus")
                particles.spawn_estus_heal(self.pos)
                particles.spawn_floating_text(self.pos, f"+{int(self.estus_heal_amount)} HP", color=(120, 255, 140))
            if self.state_timer >= self.state_duration:
                self.state = PlayerState.IDLE
                self.state_timer = 0.0

        elif self.state == PlayerState.STAGGER:
            if self.state_timer >= self.state_duration:
                self.state = PlayerState.IDLE
                self.state_timer = 0.0

        else:
            # Estados de locomoção livre (IDLE, MOVE, SPRINT, BLOCK)
            has_move = move_input.length_xz() > 0.05
            if want_block and self.stamina > 2.0:
                self.state = PlayerState.BLOCK
                speed = 3.2
            elif has_move and want_sprint and self.stamina > 2.0:
                self.state = PlayerState.SPRINT
                speed = 8.2
                self.stamina = max(0.0, self.stamina - 16.0 * dt)
                self.stamina_regen_delay = 0.35
            elif has_move:
                self.state = PlayerState.MOVE
                speed = 5.6
            else:
                self.state = PlayerState.IDLE
                speed = 0.0

            if has_move:
                self.pos = self.pos + move_input * (speed * dt)
                self.walk_cycle += speed * dt * 1.9
                if locked_target is None or self.state == PlayerState.SPRINT:
                    desired_yaw = math.atan2(move_input.x, move_input.z)
                    self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * 12.0, 0.0, 1.0))


class EnemyState(Enum):
    IDLE = auto()
    CHASE = auto()
    WINDUP = auto()
    ATTACK = auto()
    RECOVER = auto()
    STAGGER = auto()
    DEAD = auto()


class HollowEnemy:
    """Soldado Vazio (Hollow Guard) que guarda o pátio antes do Boss."""
    _next_id = 1

    def __init__(self, spawn_pos: Vec3, patrol_offset: Vec3 = Vec3(0.0, 0.0, 0.0)) -> None:
        self.entity_id = HollowEnemy._next_id
        HollowEnemy._next_id += 1

        self.name = "Guardião Vazio"
        self.spawn_pos = spawn_pos.copy()
        self.pos = spawn_pos.copy()
        self.facing_yaw = 0.0
        self.collider = CylinderCollider(radius=0.55, height=1.9)
        self.hurt_radius = 0.78
        self.lock_height = 1.35

        self.max_hp = 210.0
        self.hp = self.max_hp
        self.hp_trail = self.max_hp
        self.max_poise = 40.0
        self.poise = self.max_poise

        self.souls_reward = 180
        self.state = EnemyState.IDLE
        self.state_timer = 0.0
        self.alive = True
        self.dealt_damage_this_swing = False
        self.walk_cycle = random.uniform(0.0, 6.28)
        self.patrol_offset = patrol_offset

    def respawn(self) -> None:
        self.pos = self.spawn_pos.copy()
        self.hp = self.max_hp
        self.hp_trail = self.max_hp
        self.poise = self.max_poise
        self.state = EnemyState.IDLE
        self.state_timer = 0.0
        self.alive = True
        self.dealt_damage_this_swing = False

    def take_damage(self, amount: float, poise_dmg: float, sound_engine, particles) -> int:
        if not self.alive:
            return 0
        # Se estiver em Stagger (guarda aberta / parried), recebe dano crítico!
        if self.state == EnemyState.STAGGER:
            amount *= 1.5
            particles.spawn_floating_text(self.pos, f"CRÍTICO! -{int(amount)}", color=(255, 215, 60))
        else:
            particles.spawn_floating_text(self.pos, f"-{int(amount)}", color=(255, 235, 190))

        self.hp = max(0.0, self.hp - amount)
        self.poise -= poise_dmg
        sound_engine.play("hit")
        particles.spawn_blood_burst(Vec3(self.pos.x, self.pos.y + 1.2, self.pos.z), count=16)
        particles.spawn_hit_sparks(Vec3(self.pos.x, self.pos.y + 1.2, self.pos.z), count=14)

        if self.hp <= 0.0:
            self.alive = False
            self.state = EnemyState.DEAD
            self.state_timer = 0.0
            return self.souls_reward

        if self.poise <= 0.0:
            self.poise = self.max_poise
            self.state = EnemyState.STAGGER
            self.state_timer = 0.0
        elif self.state == EnemyState.IDLE:
            self.state = EnemyState.CHASE
            self.state_timer = 0.0

        return 0

    def trigger_parry_stagger(self) -> None:
        self.state = EnemyState.STAGGER
        self.state_timer = -0.8  # Fica vulnerável por mais tempo após tomar Parry!
        self.poise = self.max_poise

    def update(self, dt: float, player: Player, sound_engine, particles, camera) -> None:
        if self.hp_trail > self.hp:
            self.hp_trail = max(self.hp, self.hp_trail - 120.0 * dt)
        else:
            self.hp_trail = self.hp

        if not self.alive:
            self.state_timer += dt
            return

        self.state_timer += dt
        dist_to_player = self.pos.distance_xz_to(player.pos)
        to_player = (player.pos - self.pos).normalized_xz()

        if self.state == EnemyState.IDLE:
            if dist_to_player < 11.5 and player.alive:
                self.state = EnemyState.CHASE
                self.state_timer = 0.0

        elif self.state == EnemyState.CHASE:
            if not player.alive or dist_to_player > 20.0:
                self.state = EnemyState.IDLE
                return
            desired_yaw = math.atan2(to_player.x, to_player.z)
            self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * 7.5, 0.0, 1.0))

            if dist_to_player > 2.25:
                self.pos = self.pos + to_player * (3.6 * dt)
                self.walk_cycle += 3.6 * dt * 2.0
            else:
                self.state = EnemyState.WINDUP
                self.state_timer = 0.0
                self.dealt_damage_this_swing = False

        elif self.state == EnemyState.WINDUP:
            desired_yaw = math.atan2(to_player.x, to_player.z)
            self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * 5.0, 0.0, 1.0))
            if self.state_timer >= 0.55:
                self.state = EnemyState.ATTACK
                self.state_timer = 0.0
                sound_engine.play("swing_light")

        elif self.state == EnemyState.ATTACK:
            fwd = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
            if self.state_timer < 0.18:
                self.pos = self.pos + fwd * (3.5 * dt)

            # Frame ativo do ataque
            if 0.05 <= self.state_timer <= 0.22 and not self.dealt_damage_this_swing:
                hit_center = self.pos + fwd * 1.35
                if hit_center.distance_xz_to(player.pos) <= (1.15 + player.hurt_radius):
                    self.dealt_damage_this_swing = True
                    res = player.take_hit(58.0, 28.0, self.pos, sound_engine, particles, camera)
                    if res == "parried":
                        self.trigger_parry_stagger()
                        return

            if self.state_timer >= 0.32:
                self.state = EnemyState.RECOVER
                self.state_timer = 0.0

        elif self.state == EnemyState.RECOVER:
            if self.state_timer >= 0.75:
                self.state = EnemyState.CHASE
                self.state_timer = 0.0

        elif self.state == EnemyState.STAGGER:
            if self.state_timer >= 1.35:
                self.state = EnemyState.CHASE
                self.state_timer = 0.0


class BossAttackType(Enum):
    SLASH_COMBO = auto()     # Duplo corte horizontal amplo
    OVERHEAD_SLAM = auto()   # Golpe vertical esmagador com onda de choque
    THRUST_CHARGE = auto()   # Investida rápida com estocada longa
    WHIRLWIND = auto()       # Giro de 360 graus com a espada colossal


class BossState(Enum):
    DORMANT = auto()
    INTRO = auto()
    IDLE_STRAFE = auto()
    CHASE = auto()
    WINDUP = auto()
    ATTACK = auto()
    RECOVER = auto()
    PHASE_TRANSITION = auto()
    STAGGER = auto()
    DEAD = auto()


class BossMalakor:
    """
    Boss Principal: Malakor, o Lorde das Cinzas.
    Possui 2 Fases, ataques telegrafados, sistema de Poise/Stagger e lâmina flamejante na Fase 2.
    """
    def __init__(self, spawn_pos: Vec3) -> None:
        self.entity_id = 999
        self.name = "Malakor, Lorde das Cinzas"
        self.spawn_pos = spawn_pos.copy()
        self.pos = spawn_pos.copy()
        self.facing_yaw = 0.0  # Olhando para o sul (+Z, direção da entrada)
        self.collider = CylinderCollider(radius=1.05, height=3.4)
        self.hurt_radius = 1.35
        self.lock_height = 2.1

        self.max_hp = 1350.0
        self.hp = self.max_hp
        self.hp_trail = self.max_hp
        self.combo_damage_counter = 0.0
        self.combo_damage_timer = 0.0

        self.max_poise = 120.0
        self.poise = self.max_poise
        self.poise_regen_timer = 0.0

        self.phase = 1
        self.state = BossState.DORMANT
        self.state_timer = 0.0
        self.current_attack = BossAttackType.SLASH_COMBO
        self.combo_step = 0
        self.dealt_damage_this_swing = False
        self.alive = True
        self.souls_reward = 3000
        self.walk_cycle = 0.0
        self.strafe_dir = 1.0

    def respawn(self) -> None:
        if not self.alive:
            # Se o Boss já foi derrotado, você ainda pode revivê-lo descansando na fogueira se quiser,
            # mas vamos restaurá-lo para permitir revanche a qualquer momento!
            pass
        self.pos = self.spawn_pos.copy()
        self.facing_yaw = 0.0
        self.hp = self.max_hp
        self.hp_trail = self.max_hp
        self.poise = self.max_poise
        self.phase = 1
        self.state = BossState.DORMANT
        self.state_timer = 0.0
        self.alive = True
        self.dealt_damage_this_swing = False

    def get_sword_segment(self) -> tuple[Vec3, Vec3]:
        """Retorna a base e a ponta da Espada Colossal do Boss no espaço 3D."""
        fwd = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
        right = Vec3(math.cos(self.facing_yaw), 0.0, -math.sin(self.facing_yaw))
        hand = Vec3(self.pos.x, self.pos.y + 2.0, self.pos.z) + right * 0.65 + fwd * 0.45
        blade_len = 3.55

        if self.state == BossState.WINDUP:
            if self.current_attack == BossAttackType.OVERHEAD_SLAM:
                tip = hand + Vec3(fwd.x * 0.2, 1.0, fwd.z * 0.2).normalized() * blade_len
            elif self.current_attack == BossAttackType.THRUST_CHARGE:
                tip = hand - fwd * 0.6 + Vec3(fwd.x, 0.1, fwd.z).normalized() * blade_len
            else:
                side = 1.0 if self.combo_step == 0 else -1.0
                tip = hand + (right * side * 0.85 + Vec3(0.0, 0.45, 0.0)).normalized() * blade_len
        elif self.state == BossState.ATTACK:
            t = clamp(self.state_timer / 0.38, 0.0, 1.0)
            if self.current_attack == BossAttackType.OVERHEAD_SLAM:
                elev = math.cos(t * math.pi)
                tip = hand + Vec3(fwd.x, elev, fwd.z).normalized() * blade_len
            elif self.current_attack == BossAttackType.THRUST_CHARGE:
                tip = hand + fwd * (blade_len + 0.9)
            elif self.current_attack == BossAttackType.WHIRLWIND:
                ang = self.facing_yaw + t * math.pi * 2.2
                dir_v = Vec3(math.sin(ang), 0.0, math.cos(ang))
                tip = hand + dir_v * blade_len
            else:
                # SLASH_COMBO
                sign = 1.0 if self.combo_step == 0 else -1.0
                ang = (0.5 - t) * 2.6 * sign
                dir_v = (fwd * math.cos(ang) + right * math.sin(ang)).normalized()
                tip = hand + dir_v * blade_len
        else:
            tip = hand + Vec3(fwd.x * 0.55, 0.65, fwd.z * 0.55).normalized() * blade_len

        return hand, tip

    def trigger_parry_stagger(self, sound_engine, particles) -> None:
        self.state = BossState.STAGGER
        self.state_timer = 0.0
        self.poise = self.max_poise
        particles.spawn_floating_text(self.pos, "POSTURA QUEBRADA!", color=(110, 225, 255))

    def take_damage(self, amount: float, poise_dmg: float, sound_engine, particles, camera) -> tuple[int, bool]:
        """Retorna (almas_ganhas, boss_morreu_agora)."""
        if not self.alive:
            return 0, False

        if self.state == BossState.DORMANT:
            self.state = BossState.INTRO
            self.state_timer = 0.0

        if self.state == BossState.STAGGER:
            amount *= 1.45
            particles.spawn_floating_text(self.pos, f"CRÍTICO! -{int(amount)}", color=(255, 215, 70))
        else:
            particles.spawn_floating_text(self.pos, f"-{int(amount)}", color=(255, 235, 195))

        self.hp = max(0.0, self.hp - amount)
        self.combo_damage_counter += amount
        self.combo_damage_timer = 2.0

        self.poise -= poise_dmg
        self.poise_regen_timer = 5.0

        sound_engine.play("hit")
        particles.spawn_blood_burst(Vec3(self.pos.x, self.pos.y + 1.8, self.pos.z), count=22)
        particles.spawn_hit_sparks(
            Vec3(self.pos.x, self.pos.y + 1.8, self.pos.z),
            color=(1.0, 0.65, 0.2) if self.phase == 2 else (0.9, 0.85, 0.7),
            count=20,
        )

        if self.hp <= 0.0:
            self.alive = False
            self.state = BossState.DEAD
            self.state_timer = 0.0
            sound_engine.play("banner")
            camera.add_shake(0.55, 0.65)
            particles.spawn_shockwave(self.pos, max_radius=15.0, speed=18.0, color=(1.0, 0.75, 0.25))
            return self.souls_reward, True

        # Transição para Fase 2 aos 55% de vida!
        if self.phase == 1 and self.hp <= self.max_hp * 0.55:
            self.phase = 2
            self.state = BossState.PHASE_TRANSITION
            self.state_timer = 0.0
            self.poise = self.max_poise
            sound_engine.play("slam")
            camera.add_shake(0.45, 0.55)
            return 0, False

        if self.poise <= 0.0 and self.state != BossState.PHASE_TRANSITION:
            self.poise = self.max_poise
            self.state = BossState.STAGGER
            self.state_timer = 0.0
            sound_engine.play("parry")
            camera.add_shake(0.32, 0.30)
            particles.spawn_floating_text(self.pos, "STAGGER!", color=(255, 200, 80))

        return 0, False

    def _choose_next_attack(self, dist_to_player: float) -> None:
        self.dealt_damage_this_swing = False
        self.combo_step = 0
        if dist_to_player > 6.5:
            self.current_attack = random.choice([BossAttackType.THRUST_CHARGE, BossAttackType.OVERHEAD_SLAM])
        else:
            choices = [
                BossAttackType.SLASH_COMBO,
                BossAttackType.SLASH_COMBO,
                BossAttackType.OVERHEAD_SLAM,
                BossAttackType.WHIRLWIND,
                BossAttackType.THRUST_CHARGE,
            ]
            self.current_attack = random.choice(choices)
        self.state = BossState.WINDUP
        self.state_timer = 0.0

    def update(self, dt: float, player: Player, sound_engine, particles, camera) -> None:
        # Atualiza barra amarela de dano do Boss
        if self.combo_damage_timer > 0.0:
            self.combo_damage_timer -= dt
        else:
            self.combo_damage_counter = 0.0
            if self.hp_trail > self.hp:
                self.hp_trail = max(self.hp, self.hp_trail - 180.0 * dt)
            else:
                self.hp_trail = self.hp

        if not self.alive:
            self.state_timer += dt
            return

        # Na Fase 2, a lâmina do Boss emite brasas de fogo constantemente
        if self.phase == 2 and random.random() < 0.65:
            b_pos, t_pos = self.get_sword_segment()
            flame_pt = b_pos.lerp(t_pos, random.uniform(0.15, 1.0))
            particles.spawn_bonfire_ember(flame_pt)

        if self.poise_regen_timer > 0.0:
            self.poise_regen_timer -= dt
        else:
            self.poise = min(self.max_poise, self.poise + 18.0 * dt)

        self.state_timer += dt
        dist_to_player = self.pos.distance_xz_to(player.pos)
        to_player = (player.pos - self.pos).normalized_xz()

        if self.state == BossState.DORMANT:
            # Desperta quando o jogador entra no círculo interno da catedral
            if player.alive and (dist_to_player < 19.5 or player.pos.z < 12.0):
                self.state = BossState.INTRO
                self.state_timer = 0.0
                sound_engine.play("slam")
                camera.add_shake(0.30, 0.40)
                particles.spawn_shockwave(self.pos, max_radius=12.0, speed=18.0, color=(0.95, 0.55, 0.18))

        elif self.state == BossState.INTRO:
            desired_yaw = math.atan2(to_player.x, to_player.z)
            self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * 5.0, 0.0, 1.0))
            if self.state_timer >= 1.25:
                self.state = BossState.CHASE
                self.state_timer = 0.0

        elif self.state == BossState.PHASE_TRANSITION:
            # Explosão de Fogo Negro/Rubro ao entrar na Fase 2
            if 0.68 <= self.state_timer <= 0.75 and not self.dealt_damage_this_swing:
                self.dealt_damage_this_swing = True
                sound_engine.play("slam")
                camera.add_shake(0.55, 0.50)
                particles.spawn_shockwave(
                    self.pos,
                    max_radius=14.0,
                    speed=17.0,
                    color=(1.0, 0.32, 0.08),
                    damage=65.0,
                )
                particles.spawn_hit_sparks(
                    Vec3(self.pos.x, self.pos.y + 1.8, self.pos.z),
                    color=(1.0, 0.4, 0.1),
                    count=48,
                    speed=12.0,
                )
            if self.state_timer >= 1.45:
                self.dealt_damage_this_swing = False
                self.state = BossState.CHASE
                self.state_timer = 0.0

        elif self.state == BossState.IDLE_STRAFE:
            if not player.alive:
                return
            desired_yaw = math.atan2(to_player.x, to_player.z)
            self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * 6.5, 0.0, 1.0))
            right = Vec3(math.cos(self.facing_yaw), 0.0, -math.sin(self.facing_yaw))
            self.pos = self.pos + right * (self.strafe_dir * 2.6 * dt)
            self.walk_cycle += 2.6 * dt * 1.4

            if self.state_timer >= 0.85 or dist_to_player < 3.6 or dist_to_player > 8.5:
                self.state = BossState.CHASE
                self.state_timer = 0.0

        elif self.state == BossState.CHASE:
            if not player.alive:
                return
            desired_yaw = math.atan2(to_player.x, to_player.z)
            self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * 7.0, 0.0, 1.0))

            move_spd = 5.4 if self.phase == 2 else 4.4
            if dist_to_player > 3.85:
                self.pos = self.pos + to_player * (move_spd * dt)
                self.walk_cycle += move_spd * dt * 1.5
                # Pode iniciar ataque de investida à distância
                if 6.5 <= dist_to_player <= 11.0 and self.state_timer > 0.9:
                    self._choose_next_attack(dist_to_player)
            else:
                self._choose_next_attack(dist_to_player)

        elif self.state == BossState.WINDUP:
            # Durante o windup (antecipação), o Boss acompanha parcialmente a rotação do jogador
            desired_yaw = math.atan2(to_player.x, to_player.z)
            track_spd = 5.5 if self.state_timer < 0.45 else 2.0
            self.facing_yaw = lerp_angle(self.facing_yaw, desired_yaw, clamp(dt * track_spd, 0.0, 1.0))

            windup_dur = {
                BossAttackType.SLASH_COMBO: 0.56,
                BossAttackType.OVERHEAD_SLAM: 0.78,
                BossAttackType.THRUST_CHARGE: 0.62,
                BossAttackType.WHIRLWIND: 0.68,
            }[self.current_attack]
            if self.phase == 2:
                windup_dur *= 0.86  # Mais agressivo na Fase 2

            if self.state_timer >= windup_dur:
                self.state = BossState.ATTACK
                self.state_timer = 0.0
                self.dealt_damage_this_swing = False
                sound_engine.play("swing_heavy")

        elif self.state == BossState.ATTACK:
            fwd = Vec3(math.sin(self.facing_yaw), 0.0, math.cos(self.facing_yaw))
            b_pos, t_pos = self.get_sword_segment()
            trail_col = (1.0, 0.42, 0.12) if self.phase == 2 else (0.95, 0.80, 0.55)
            particles.add_trail_sample(b_pos, t_pos, color=trail_col, duration=0.18)

            # Deslocamento físico do Boss durante o golpe
            if self.current_attack == BossAttackType.THRUST_CHARGE and self.state_timer < 0.28:
                self.pos = self.pos + fwd * (15.5 * dt)
            elif self.current_attack == BossAttackType.OVERHEAD_SLAM and self.state_timer < 0.22:
                self.pos = self.pos + fwd * (6.5 * dt)
            elif self.current_attack == BossAttackType.SLASH_COMBO and self.state_timer < 0.22:
                self.pos = self.pos + fwd * (4.8 * dt)

            # Verificação de Hitbox nos frames ativos
            if 0.06 <= self.state_timer <= 0.30 and not self.dealt_damage_this_swing:
                if self.current_attack == BossAttackType.WHIRLWIND:
                    hit = self.pos.distance_xz_to(player.pos) <= 4.3
                    dmg, poise_d = (95.0, 45.0)
                elif self.current_attack == BossAttackType.OVERHEAD_SLAM:
                    impact_pt = self.pos + fwd * 2.8
                    hit = impact_pt.distance_xz_to(player.pos) <= 2.7
                    dmg, poise_d = (125.0, 65.0)
                elif self.current_attack == BossAttackType.THRUST_CHARGE:
                    impact_pt = self.pos + fwd * 2.9
                    hit = impact_pt.distance_xz_to(player.pos) <= 2.3
                    dmg, poise_d = (105.0, 50.0)
                else:
                    # SLASH_COMBO
                    impact_pt = self.pos + fwd * 2.5
                    hit = impact_pt.distance_xz_to(player.pos) <= 2.75
                    dmg, poise_d = (85.0, 38.0)

                if self.phase == 2:
                    dmg *= 1.18

                # Efeito de impacto no chão no OVERHEAD_SLAM
                if self.current_attack == BossAttackType.OVERHEAD_SLAM and self.state_timer >= 0.18:
                    self.dealt_damage_this_swing = True
                    slam_pt = self.pos + fwd * 2.8
                    sound_engine.play("slam")
                    camera.add_shake(0.42, 0.32)
                    particles.spawn_hit_sparks(slam_pt, color=(1.0, 0.55, 0.15), count=32, speed=9.5)
                    if self.phase == 2:
                        particles.spawn_shockwave(
                            slam_pt,
                            max_radius=9.5,
                            speed=14.5,
                            color=(1.0, 0.38, 0.10),
                            damage=55.0,
                        )
                    if hit:
                        player.take_hit(dmg, poise_d, self.pos, sound_engine, particles, camera)
                elif hit:
                    self.dealt_damage_this_swing = True
                    res = player.take_hit(dmg, poise_d, self.pos, sound_engine, particles, camera)
                    if res == "parried":
                        self.trigger_parry_stagger(sound_engine, particles)
                        return

            if self.state_timer >= 0.38:
                # Se for SLASH_COMBO, emenda o 2º golpe (e 3º golpe na Fase 2!)
                max_steps = 2 if self.phase == 2 else 1
                if self.current_attack == BossAttackType.SLASH_COMBO and self.combo_step < max_steps and dist_to_player < 6.0:
                    self.combo_step += 1
                    self.state = BossState.WINDUP
                    self.state_timer = 0.22  # Windup mais curto entre golpes do combo
                    self.dealt_damage_this_swing = False
                else:
                    self.state = BossState.RECOVER
                    self.state_timer = 0.0

        elif self.state == BossState.RECOVER:
            rec_time = 0.75 if self.phase == 2 else 0.98
            if self.state_timer >= rec_time:
                self.strafe_dir = random.choice([-1.0, 1.0])
                self.state = BossState.IDLE_STRAFE if random.random() < 0.45 else BossState.CHASE
                self.state_timer = 0.0

        elif self.state == BossState.STAGGER:
            if self.state_timer >= 2.1:
                self.state = BossState.CHASE
                self.state_timer = 0.0
