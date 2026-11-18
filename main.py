"""
ASHEN SOULS 3D - Jogo Soulslike 3D em Terceira Pessoa programado do zero em Python + OpenGL.
Sem engine comercial: Matemática 3D, Física/Colisões, Câmera Orbital + Lock-On,
Máquina de Estados de Combate, I-Frames, Parry, Poise/Stagger, Sintetizador de Áudio,
Partículas 3D, Renderizador OpenGL, Paisagem 3D de Menu e HUD foram todos programados na mão.
"""

import sys
import random
import pygame
from engine.math3d import Vec3, segment_sphere_intersect
from engine.camera import ThirdPersonCamera
from engine.audio import SoundEngine
from engine.particles import ParticleSystem
from engine.renderer import Renderer3D
from game.world import ArenaWorld
from game.entities import Player, HollowEnemy, BossMalakor
from ui.hud import SoulsHUD


STARTING_CLASSES = [
    {
        "name": "Cavaleiro Errante",
        "desc": "Equilibrado em defesa, vitalidade e lâmina longa.",
        "vigor": 12,
        "endurance": 11,
        "strength": 11,
        "estus": 5,
    },
    {
        "name": "Guerreiro Colossal",
        "desc": "Força brutal e alta vitalidade para quebrar posturas.",
        "vigor": 13,
        "endurance": 9,
        "strength": 14,
        "estus": 4,
    },
    {
        "name": "Lâmina das Cinzas",
        "desc": "Fôlego elevado e 6 Frascos de Estus para esquivas ágeis.",
        "vigor": 9,
        "endurance": 15,
        "strength": 11,
        "estus": 6,
    },
]


class SoulslikeGame:
    def __init__(self, width: int = 1280, height: int = 720) -> None:
        pygame.init()
        self.width = width
        self.height = height

        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        self.screen = pygame.display.set_mode(
            (self.width, self.height),
            pygame.OPENGL | pygame.DOUBLEBUF,
        )
        pygame.display.set_caption("ASHEN SOULS 3D - O Eclipse de Malakor")

        self.clock = pygame.time.Clock()
        self.running = True

        # Inicializa subsistemas da nossa própria Engine
        self.sound = SoundEngine()
        self.particles = ParticleSystem()
        self.renderer = Renderer3D(self.width, self.height)
        self.hud = SoulsHUD(self.width, self.height)
        self.camera = ThirdPersonCamera()
        self.world = ArenaWorld()

        # Entidades do Jogo
        self.player = Player(spawn_pos=Vec3(0.0, 0.0, 29.0))
        self.enemies: list[HollowEnemy] = [
            HollowEnemy(Vec3(-4.2, 0.0, 17.5)),
            HollowEnemy(Vec3(4.2, 0.0, 17.5)),
        ]
        self.boss = BossMalakor(spawn_pos=Vec3(0.0, 0.0, -5.5))

        # Estado da Tela Inicial (Title Screen)
        self.in_title_screen = True
        self.title_selected_idx = 0
        self.title_class_idx = 0
        self.title_help_open = False
        self.title_starting_transition = False
        self.title_fade_alpha = 0.0
        self.title_btn_rects: list[tuple[float, float, float, float]] = []

        self.bonfire_menu_open = False
        self.death_respawn_timer = 0.0
        self.mouse_captured = False
        self._set_mouse_capture(False)

    def _set_mouse_capture(self, capture: bool) -> None:
        self.mouse_captured = capture
        pygame.event.set_grab(capture)
        pygame.mouse.set_visible(not capture)
        pygame.mouse.get_rel()

    def _apply_starting_class_and_begin(self) -> None:
        cls = STARTING_CLASSES[self.title_class_idx]
        self.player.level = 1
        self.player.vigor = cls["vigor"]
        self.player.endurance = cls["endurance"]
        self.player.strength = cls["strength"]
        self.player.max_estus = cls["estus"]
        self.player.estus = cls["estus"]
        self.player.souls = 0
        self.player.pos = self.player.spawn_pos.copy()
        self.player.facing_yaw = 3.14159
        self.player.reset_at_bonfire()

        for e in self.enemies:
            e.respawn()
        self.boss.respawn()
        self.particles.clear()

        self.in_title_screen = False
        self.title_starting_transition = False
        self.title_fade_alpha = 0.0
        self._set_mouse_capture(True)

        self.hud.trigger_banner(
            "CATEDRAL DAS CINZAS",
            color=(235, 205, 135),
            subtext=f"{cls['name']} — Enfrente Malakor, Lorde das Cinzas",
            duration=3.6,
        )

    def _activate_title_option(self, idx: int) -> None:
        if self.title_starting_transition:
            return
        if idx == 0:
            # Iniciar Jornada!
            self.sound.play("menu_confirm")
            self.title_starting_transition = True
        elif idx == 1:
            # Alternar Classe
            self.title_class_idx = (self.title_class_idx + 1) % len(STARTING_CLASSES)
            self.sound.play("menu_move")
        elif idx == 2:
            # Abrir Guia de Combate
            self.title_help_open = not self.title_help_open
            self.sound.play("menu_move")
        elif idx == 3:
            # Sair do Jogo
            self.running = False

    def process_title_events(self) -> None:
        mx, my = pygame.mouse.get_pos()

        # Hover do mouse sobre os botões do menu
        if not self.title_help_open and not self.title_starting_transition:
            for i, (bx, by, bw, bh) in enumerate(self.title_btn_rects):
                if bx <= mx <= bx + bw and by <= my <= by + bh:
                    if self.title_selected_idx != i:
                        self.title_selected_idx = i
                        self.sound.play("menu_move")
                    break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.title_help_open:
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                        self.title_help_open = False
                        self.sound.play("menu_move")
                    continue

                if self.title_starting_transition:
                    continue

                if event.key in (pygame.K_w, pygame.K_UP):
                    self.title_selected_idx = (self.title_selected_idx - 1) % 4
                    self.sound.play("menu_move")
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.title_selected_idx = (self.title_selected_idx + 1) % 4
                    self.sound.play("menu_move")
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    self.title_class_idx = (self.title_class_idx - 1) % len(STARTING_CLASSES)
                    self.sound.play("menu_move")
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    self.title_class_idx = (self.title_class_idx + 1) % len(STARTING_CLASSES)
                    self.sound.play("menu_move")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                    self._activate_title_option(self.title_selected_idx)
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.title_help_open:
                    self.title_help_open = False
                    self.sound.play("menu_move")
                    continue
                for i, (bx, by, bw, bh) in enumerate(self.title_btn_rects):
                    if bx <= mx <= bx + bw and by <= my <= by + bh:
                        self.title_selected_idx = i
                        self._activate_title_option(i)
                        break

    def update_title_screen(self, dt: float) -> None:
        # Brasas subindo da Fogueira do penhasco e cinzas sopradas pelo vento da montanha!
        if random.random() < 0.65:
            self.particles.spawn_bonfire_ember(Vec3(1.55, 0.0, 0.65))
        if random.random() < 0.35:
            # Cinzas flutuando pelo ar diante do penhasco
            ash_pos = Vec3(
                random.uniform(-5.5, 5.5),
                random.uniform(0.2, 3.8),
                random.uniform(-3.5, 2.5),
            )
            self.particles.spawn_bonfire_ember(ash_pos)

        self.particles.update(dt)

        if self.title_starting_transition:
            self.title_fade_alpha += dt * 1.15
            if self.title_fade_alpha >= 1.0:
                self._apply_starting_class_and_begin()

    def render_title_screen(self, dt: float) -> None:
        self.renderer.render_title_landscape(dt, self.player, self.particles)
        self.title_btn_rects = self.hud.render_title_screen(
            self.title_selected_idx,
            self.title_class_idx,
            STARTING_CLASSES,
            self.title_help_open,
            self.title_fade_alpha,
            self.renderer.time_accum,
        )
        pygame.display.flip()

    def toggle_lock_on(self) -> None:
        if self.camera.locked_target is not None:
            self.camera.locked_target = None
            return

        candidates = []
        for e in self.enemies:
            if e.alive:
                d = self.player.pos.distance_to(e.pos)
                if d <= 24.0:
                    candidates.append((d, e))
        if self.boss.alive:
            d_boss = self.player.pos.distance_to(self.boss.pos)
            if d_boss <= 28.0:
                candidates.append((d_boss * 0.85, self.boss))

        if candidates:
            candidates.sort(key=lambda item: item[0])
            self.camera.locked_target = candidates[0][1]

    def _handle_bonfire_key(self, key: int) -> None:
        cost = self.player.get_level_up_cost()
        if key == pygame.K_1 and self.player.souls >= cost:
            self.player.souls -= cost
            self.player.level += 1
            self.player.vigor += 1
            self.player.recalc_stats(full_restore=True)
            self.sound.play("estus")
        elif key == pygame.K_2 and self.player.souls >= cost:
            self.player.souls -= cost
            self.player.level += 1
            self.player.endurance += 1
            self.player.recalc_stats(full_restore=True)
            self.sound.play("estus")
        elif key == pygame.K_3 and self.player.souls >= cost:
            self.player.souls -= cost
            self.player.level += 1
            self.player.strength += 1
            self.player.recalc_stats(full_restore=True)
            self.sound.play("estus")
        elif key == pygame.K_4:
            for e in self.enemies:
                e.respawn()
            self.boss.respawn()
            self.sound.play("banner")
            self.hud.trigger_banner(
                "MUNDO RESTAURADO",
                color=(230, 190, 110),
                subtext="Malakor e os Guardiões Vazios renasceram das cinzas",
                duration=2.6,
            )
        elif key in (pygame.K_e, pygame.K_ESCAPE):
            self.bonfire_menu_open = False
            self._set_mouse_capture(True)

    def _interact(self) -> None:
        # 1. Recuperar poça de almas (Bloodstain)
        if self.world.bloodstain.active:
            if self.player.pos.distance_xz_to(self.world.bloodstain.pos) <= 2.5:
                recovered = self.world.bloodstain.souls
                self.player.souls += recovered
                self.world.bloodstain.active = False
                self.world.bloodstain.souls = 0
                self.sound.play("estus")
                self.particles.spawn_estus_heal(self.player.pos, count=30)
                self.hud.trigger_banner(
                    "ALMAS RECUPERADAS",
                    color=(120, 240, 190),
                    subtext=f"+{recovered} Almas restauradas",
                    duration=2.5,
                )
                return

        # 2. Descansar na Fogueira (Bonfire)
        if self.world.bonfire.can_interact(self.player.pos):
            self.player.reset_at_bonfire()
            for e in self.enemies:
                e.respawn()
            if self.boss.alive:
                self.boss.respawn()
            self.camera.locked_target = None
            self.sound.play("estus")
            self.particles.spawn_estus_heal(self.world.bonfire.pos, count=42)
            self.bonfire_menu_open = True
            self._set_mouse_capture(False)

    def process_events(self) -> Vec3:
        keys = pygame.key.get_pressed()
        fwd = self.camera.get_forward_xz()
        right = self.camera.get_right_xz()

        move_dir = Vec3(0.0, 0.0, 0.0)
        if keys[pygame.K_w]:
            move_dir = move_dir + fwd
        if keys[pygame.K_s]:
            move_dir = move_dir - fwd
        if keys[pygame.K_d]:
            move_dir = move_dir + right
        if keys[pygame.K_a]:
            move_dir = move_dir - right
        if move_dir.length_xz() > 0.01:
            move_dir = move_dir.normalized_xz()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.bonfire_menu_open:
                    self._handle_bonfire_key(event.key)
                    continue

                if event.key == pygame.K_ESCAPE:
                    self._set_mouse_capture(not self.mouse_captured)
                elif event.key == pygame.K_F1:
                    self.hud.show_controls = not self.hud.show_controls
                elif event.key == pygame.K_F2:
                    # Permite voltar à Tela Inicial a qualquer momento!
                    self.in_title_screen = True
                    self.particles.clear()
                    self._set_mouse_capture(False)
                elif event.key == pygame.K_TAB:
                    self.toggle_lock_on()
                elif event.key == pygame.K_SPACE:
                    self.player.start_roll(move_dir, self.sound)
                elif event.key == pygame.K_f:
                    self.player.request_heavy_attack(self.sound)
                elif event.key == pygame.K_c:
                    self.player.request_parry(self.sound)
                elif event.key == pygame.K_r:
                    self.player.request_estus()
                elif event.key == pygame.K_e:
                    self._interact()

            elif event.type == pygame.MOUSEBUTTONDOWN and not self.bonfire_menu_open:
                if not self.mouse_captured:
                    self._set_mouse_capture(True)
                    continue

                if event.button == 1:
                    if keys[pygame.K_q]:
                        self.player.request_heavy_attack(self.sound)
                    else:
                        self.player.request_light_attack(self.sound)
                elif event.button == 2:
                    self.toggle_lock_on()

        if self.mouse_captured and not self.bonfire_menu_open:
            mx, my = pygame.mouse.get_rel()
            self.camera.handle_mouse(float(mx), float(my))

        return move_dir

    def _check_player_sword_hits(self) -> None:
        if not self.player.is_attack_active():
            return

        base_pos, tip_pos = self.player.get_sword_segment()
        dmg = self.player.get_attack_damage()
        poise_dmg = self.player.get_poise_damage()

        for e in self.enemies:
            if not e.alive or e.entity_id in self.player.hit_targets_this_swing:
                continue
            enemy_center = Vec3(e.pos.x, e.pos.y + 1.0, e.pos.z)
            if segment_sphere_intersect(base_pos, tip_pos, enemy_center, e.hurt_radius):
                self.player.hit_targets_this_swing.add(e.entity_id)
                souls_won = e.take_damage(dmg, poise_dmg, self.sound, self.particles)
                self.camera.add_shake(0.18, 0.14)
                if souls_won > 0:
                    self.player.souls += souls_won
                    self.particles.spawn_floating_text(
                        e.pos, f"+{souls_won} ALMAS", color=(180, 240, 255)
                    )

        if self.boss.alive and self.boss.entity_id not in self.player.hit_targets_this_swing:
            boss_center = Vec3(self.boss.pos.x, self.boss.pos.y + 1.6, self.boss.pos.z)
            if segment_sphere_intersect(base_pos, tip_pos, boss_center, self.boss.hurt_radius):
                self.player.hit_targets_this_swing.add(self.boss.entity_id)
                souls_won, boss_died = self.boss.take_damage(
                    dmg, poise_dmg, self.sound, self.particles, self.camera
                )
                self.camera.add_shake(0.22, 0.16)
                if boss_died:
                    self.player.souls += souls_won
                    self.camera.locked_target = None
                    self.hud.trigger_banner(
                        "GREAT ENEMY FELLED",
                        color=(255, 205, 85),
                        subtext=f"Malakor foi derrotado! +{souls_won} Almas obtidas",
                        duration=5.0,
                    )

    def _check_shockwaves_and_collisions(self) -> None:
        for w in self.particles.shockwaves:
            if w.damage > 0.0 and not w.hit_player and self.player.alive:
                dist = self.player.pos.distance_xz_to(w.center)
                if abs(dist - w.radius) <= 0.75:
                    w.hit_player = True
                    self.player.take_hit(
                        w.damage, 30.0, w.center, self.sound, self.particles, self.camera
                    )

        for e in self.enemies:
            if e.alive:
                sep = self.player.collider.resolve_xz(self.player.pos, e.collider, e.pos)
                self.player.pos = self.player.pos + sep * 0.5
                e.pos = e.pos - sep * 0.5
                e.pos = self.world.resolve_environment_collisions(e.pos, e.collider.radius)

        if self.boss.alive:
            sep = self.player.collider.resolve_xz(self.player.pos, self.boss.collider, self.boss.pos)
            self.player.pos = self.player.pos + sep * 0.7
            self.boss.pos = self.boss.pos - sep * 0.3
            self.boss.pos = self.world.resolve_environment_collisions(
                self.boss.pos, self.boss.collider.radius
            )

        self.player.pos = self.world.resolve_environment_collisions(
            self.player.pos, self.player.collider.radius
        )

    def update(self, dt: float, move_dir: Vec3) -> None:
        if random.random() < 0.45:
            self.particles.spawn_bonfire_ember(self.world.bonfire.pos)

        if self.bonfire_menu_open:
            self.particles.update(dt)
            self.hud.update(dt)
            self.camera.update(dt, self.player.pos)
            return

        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        want_sprint = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        want_block = bool(mouse_buttons[2])

        was_alive = self.player.alive
        self.player.update(
            dt,
            move_dir,
            want_sprint,
            want_block,
            self.camera.locked_target,
            self.sound,
            self.particles,
        )

        if was_alive and not self.player.alive:
            self.death_respawn_timer = 3.5
            self.camera.locked_target = None
            if self.player.souls > 0:
                self.world.bloodstain.pos = self.player.pos.copy()
                self.world.bloodstain.souls = self.player.souls
                self.world.bloodstain.active = True
                self.player.souls = 0
            self.hud.trigger_banner(
                "YOU DIED",
                color=(195, 28, 28),
                subtext="Suas almas ficaram caídas no local da morte",
                duration=3.4,
            )

        if not self.player.alive:
            self.death_respawn_timer -= dt
            if self.death_respawn_timer <= 0.0:
                self.player.pos = self.player.spawn_pos.copy()
                self.player.facing_yaw = 3.14159
                self.player.reset_at_bonfire()
                for e in self.enemies:
                    e.respawn()
                if self.boss.alive:
                    self.boss.respawn()

        for e in self.enemies:
            e.update(dt, self.player, self.sound, self.particles, self.camera)
        self.boss.update(dt, self.player, self.sound, self.particles, self.camera)

        self._check_player_sword_hits()
        self._check_shockwaves_and_collisions()

        self.particles.update(dt)
        self.camera.update(dt, self.player.pos)
        self.hud.update(dt)

    def render(self, dt: float) -> None:
        self.renderer.begin_frame_3d(dt, self.camera, self.world, self.boss)
        self.renderer.render_world(self.world)

        for e in self.enemies:
            self.renderer.render_hollow_enemy(e)

        self.renderer.render_boss(self.boss)
        self.renderer.render_player(self.player)
        self.renderer.render_particles_and_effects(self.particles)

        self.hud.render(
            self.renderer,
            self.player,
            self.enemies,
            self.boss,
            self.world,
            self.particles,
            self.camera.locked_target,
            self.bonfire_menu_open,
        )

        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            if self.in_title_screen:
                self.process_title_events()
                self.update_title_screen(dt)
                self.render_title_screen(dt)
            else:
                move_dir = self.process_events()
                self.update(dt, move_dir)
                self.render(dt)

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    game = SoulslikeGame()
    game.run()
