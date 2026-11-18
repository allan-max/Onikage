"""
Interface Gráfica (HUD) 2D estilo Dark Souls / Elden Ring renderizada sobre o OpenGL.
Usa projeção ortográfica 2D e cache de texturas de fontes do Pygame para máxima performance.
"""

import math
import pygame
import OpenGL.GL as gl
from engine.math3d import Vec3, clamp
from game.entities import Player, HollowEnemy, BossMalakor, BossState


class SoulsHUD:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        pygame.font.init()

        self.fonts = {
            "small": pygame.font.SysFont("georgia", 15, bold=False),
            "ui": pygame.font.SysFont("georgia", 18, bold=True),
            "boss": pygame.font.SysFont("georgia", 24, bold=True),
            "banner": pygame.font.SysFont("georgia", 54, bold=True),
            "subbanner": pygame.font.SysFont("georgia", 22, bold=True),
            "title_logo": pygame.font.SysFont("georgia", 64, bold=True),
        }

        # Cache de texturas de texto: (texto, font_key, cor_rgb) -> (tex_id, w, h)
        self._text_cache: dict[tuple[str, str, tuple[int, int, int]], tuple[int, int, int]] = {}

        # Banner dramático ("YOU DIED", "GREAT ENEMY FELLED", "BONFIRE LIT")
        self.banner_text = ""
        self.banner_subtext = ""
        self.banner_color = (200, 35, 35)
        self.banner_timer = 0.0
        self.banner_duration = 0.0

        self.show_controls = True

    def trigger_banner(
        self,
        text: str,
        color: tuple[int, int, int] = (210, 40, 40),
        subtext: str = "",
        duration: float = 3.6,
    ) -> None:
        self.banner_text = text
        self.banner_subtext = subtext
        self.banner_color = color
        self.banner_duration = duration
        self.banner_timer = duration

    def update(self, dt: float) -> None:
        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

    def _get_text_texture(
        self, text: str, font_key: str, color: tuple[int, int, int]
    ) -> tuple[int, int, int]:
        key = (text, font_key, color)
        if key in self._text_cache:
            return self._text_cache[key]

        # Limita tamanho do cache para evitar vazamento de VRAM em números variáveis
        if len(self._text_cache) > 350:
            for old_tex, _, _ in self._text_cache.values():
                gl.glDeleteTextures([old_tex])
            self._text_cache.clear()

        font = self.fonts[font_key]
        surf = font.render(text, True, color)
        w, h = surf.get_size()
        raw = pygame.image.tostring(surf, "RGBA", False)

        tex_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA,
            w,
            h,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            raw,
        )
        self._text_cache[key] = (tex_id, w, h)
        return tex_id, w, h

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        font_key: str = "ui",
        color: tuple[int, int, int] = (235, 228, 210),
        alpha: float = 1.0,
        center: bool = False,
        shadow: bool = True,
    ) -> None:
        if not text:
            return
        if shadow:
            sh_tex, sw, sh = self._get_text_texture(text, font_key, (10, 10, 12))
            sx = x - sw * 0.5 + 2.0 if center else x + 2.0
            sy = y - sh * 0.5 + 2.0 if center else y + 2.0
            self._draw_tex_quad(sh_tex, sx, sy, sw, sh, alpha * 0.85)

        tex_id, w, h = self._get_text_texture(text, font_key, color)
        dx = x - w * 0.5 if center else x
        dy = y - h * 0.5 if center else y
        self._draw_tex_quad(tex_id, dx, dy, w, h, alpha)

    def _draw_tex_quad(
        self, tex_id: int, x: float, y: float, w: float, h: float, alpha: float
    ) -> None:
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id)
        gl.glColor4f(1.0, 1.0, 1.0, clamp(alpha, 0.0, 1.0))
        gl.glBegin(gl.GL_QUADS)
        gl.glTexCoord2f(0.0, 0.0)
        gl.glVertex2f(x, y)
        gl.glTexCoord2f(1.0, 0.0)
        gl.glVertex2f(x + w, y)
        gl.glTexCoord2f(1.0, 1.0)
        gl.glVertex2f(x + w, y + h)
        gl.glTexCoord2f(0.0, 1.0)
        gl.glVertex2f(x, y + h)
        gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D)

    def draw_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color: tuple[float, float, float, float],
    ) -> None:
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(x, y)
        gl.glVertex2f(x + w, y)
        gl.glVertex2f(x + w, y + h)
        gl.glVertex2f(x, y + h)
        gl.glEnd()

    def draw_rect_border(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        color: tuple[float, float, float, float],
        thickness: float = 1.5,
    ) -> None:
        gl.glLineWidth(thickness)
        gl.glColor4f(*color)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(x, y)
        gl.glVertex2f(x + w, y)
        gl.glVertex2f(x + w, y + h)
        gl.glVertex2f(x, y + h)
        gl.glEnd()

    def _draw_souls_bar(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        val: float,
        trail_val: float,
        max_val: float,
        fill_color: tuple[float, float, float, float],
    ) -> None:
        # Fundo escuro da barra
        self.draw_rect(x, y, w, h, (0.06, 0.06, 0.08, 0.88))

        # Barra amarela de dano recente (Damage Trail)
        trail_ratio = clamp(trail_val / max(1.0, max_val), 0.0, 1.0)
        if trail_ratio > 0.0:
            self.draw_rect(x, y, w * trail_ratio, h, (0.88, 0.72, 0.20, 0.90))

        # Preenchimento principal
        ratio = clamp(val / max(1.0, max_val), 0.0, 1.0)
        if ratio > 0.0:
            self.draw_rect(x, y, w * ratio, h, fill_color)
            # Brilho superior sutil para efeito metálico/vidro
            self.draw_rect(x, y, w * ratio, h * 0.35, (1.0, 1.0, 1.0, 0.14))

        # Moldura dourada envelhecida estilo Dark Souls / Elden Ring
        self.draw_rect_border(x, y, w, h, (0.55, 0.48, 0.34, 0.95), 1.5)

    def render(
        self,
        renderer3d,
        player: Player,
        enemies: list[HollowEnemy],
        boss: BossMalakor,
        world,
        particles,
        locked_target,
        bonfire_menu_open: bool,
    ) -> None:
        # Primeiro projeta posições 3D necessárias enquanto as matrizes 3D estão ativas!
        lock_screen = None
        if locked_target is not None and getattr(locked_target, "alive", False):
            lh = getattr(locked_target, "lock_height", 1.4)
            sx, sy, ok = renderer3d.project_to_screen(
                Vec3(locked_target.pos.x, locked_target.pos.y + lh, locked_target.pos.z)
            )
            if ok:
                lock_screen = (sx, sy)

        enemy_bars_2d = []
        for e in enemies:
            if e.alive and (e.hp < e.max_hp or locked_target is e):
                sx, sy, ok = renderer3d.project_to_screen(Vec3(e.pos.x, e.pos.y + 2.25, e.pos.z))
                if ok:
                    enemy_bars_2d.append((sx, sy, e.hp, e.hp_trail, e.max_hp))

        floating_texts_2d = []
        for ft in particles.floating_texts:
            sx, sy, ok = renderer3d.project_to_screen(ft.pos)
            if ok:
                alpha = clamp(ft.life / max(0.001, ft.max_life), 0.0, 1.0)
                floating_texts_2d.append((sx, sy, ft.text, ft.color, alpha))

        # Muda o OpenGL para Projeção Ortográfica 2D
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, self.width, self.height, 0, -1, 1)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_FOG)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # 1. Desenha Retícula de Lock-On no alvo
        if lock_screen is not None:
            lx, ly = lock_screen
            gl.glColor4f(1.0, 0.96, 0.85, 0.95)
            gl.glLineWidth(2.0)
            r = 11.0
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(20):
                a = i * (2.0 * math.pi / 20.0)
                gl.glVertex2f(lx + math.cos(a) * r, ly + math.sin(a) * r)
            gl.glEnd()
            self.draw_rect(lx - 2.5, ly - 2.5, 5.0, 5.0, (1.0, 1.0, 1.0, 1.0))

        # 2. Barras de vida flutuantes dos Guardiões Vazios
        for sx, sy, hp, trail, mhp in enemy_bars_2d:
            bw, bh = 76.0, 7.0
            self._draw_souls_bar(sx - bw * 0.5, sy, bw, bh, hp, trail, mhp, (0.76, 0.18, 0.18, 0.95))

        # 3. Números de Dano Flutuantes
        for sx, sy, txt, col, alpha in floating_texts_2d:
            self.draw_text(txt, sx, sy, font_key="ui", color=col, alpha=alpha, center=True)

        # 4. Barras do Jogador no Canto Superior Esquerdo (HP, Poise, Stamina)
        # Emblema de Pacto (Covenant Medallion)
        self.draw_rect(26, 26, 44, 44, (0.12, 0.11, 0.10, 0.92))
        self.draw_rect_border(26, 26, 44, 44, (0.68, 0.56, 0.34, 0.95), 2.0)
        self.draw_text(f"Nv.{player.level}", 48, 48, font_key="small", color=(240, 215, 150), center=True)

        hp_w = clamp(player.max_hp * 0.62, 220.0, 480.0)
        stam_w = clamp(player.max_stamina * 1.65, 160.0, 380.0)

        # Barra de Vida (Vermelho Carmesim)
        self._draw_souls_bar(
            80, 28, hp_w, 15, player.hp, player.hp_trail, player.max_hp, (0.74, 0.14, 0.14, 0.96)
        )
        # Barra de Postura / Poise (Azul Aço)
        self._draw_souls_bar(
            80, 48, 165, 9, player.poise, player.poise, player.max_poise, (0.24, 0.48, 0.72, 0.95)
        )
        # Barra de Stamina (Verde Esmeralda)
        self._draw_souls_bar(
            80, 62, stam_w, 12, max(0.0, player.stamina), max(0.0, player.stamina), player.max_stamina, (0.18, 0.64, 0.28, 0.96)
        )

        # 5. Slot de Item no Canto Inferior Esquerdo (Frasco de Estus + Escudo)
        slot_x, slot_y = 32, self.height - 108
        self.draw_rect(slot_x, slot_y, 68, 76, (0.08, 0.08, 0.10, 0.88))
        self.draw_rect_border(slot_x, slot_y, 68, 76, (0.62, 0.52, 0.32, 0.95), 2.0)
        # Ícone estilizado do Frasco de Estus dourado
        estus_col = (0.95, 0.72, 0.18, 0.95) if player.estus > 0 else (0.3, 0.3, 0.32, 0.7)
        self.draw_rect(slot_x + 22, slot_y + 18, 24, 30, estus_col)
        self.draw_rect(slot_x + 28, slot_y + 10, 12, 8, (0.75, 0.68, 0.50, 0.9))
        self.draw_text(
            f"{player.estus}/{player.max_estus}",
            slot_x + 34,
            slot_y + 60,
            font_key="ui",
            color=(255, 225, 130),
            center=True,
        )
        self.draw_text(
            "[R] Frasco de Estus",
            slot_x + 82,
            slot_y + 28,
            font_key="small",
            color=(220, 210, 190),
        )
        if player.is_invulnerable():
            self.draw_text(
                "I-FRAMES (INVENCÍVEL)",
                slot_x + 82,
                slot_y + 50,
                font_key="small",
                color=(120, 220, 255),
            )

        # 6. Contador de Almas (Souls) no Canto Inferior Direito
        souls_box_w, souls_box_h = 190, 42
        sb_x = self.width - souls_box_w - 32
        sb_y = self.height - souls_box_h - 32
        self.draw_rect(sb_x, sb_y, souls_box_w, souls_box_h, (0.07, 0.07, 0.09, 0.88))
        self.draw_rect_border(sb_x, sb_y, souls_box_w, souls_box_h, (0.58, 0.50, 0.34, 0.95), 1.8)
        self.draw_text("ALMAS", sb_x + 14, sb_y + 11, font_key="small", color=(190, 180, 155))
        self.draw_text(
            f"{player.souls}",
            sb_x + souls_box_w - 16,
            sb_y + 21,
            font_key="ui",
            color=(245, 235, 195),
            center=True,
        )

        # 7. Barra de Vida do Boss na Parte Inferior Central
        if boss.alive and boss.state != BossState.DORMANT:
            bw = min(760.0, self.width * 0.64)
            bx = (self.width - bw) * 0.5
            by = self.height - 92.0
            boss_title = (
                "Malakor, Chama Profana (Fase II)"
                if boss.phase == 2
                else "Malakor, Lorde das Cinzas"
            )
            title_col = (255, 185, 120) if boss.phase == 2 else (235, 225, 205)
            self.draw_text(boss_title, bx + 4, by - 26, font_key="boss", color=title_col)

            if boss.combo_damage_counter > 0:
                self.draw_text(
                    f"{int(boss.combo_damage_counter)}",
                    bx + bw - 20,
                    by - 22,
                    font_key="ui",
                    color=(245, 220, 165),
                    center=True,
                )

            self._draw_souls_bar(
                bx,
                by,
                bw,
                16.0,
                boss.hp,
                boss.hp_trail,
                boss.max_hp,
                (0.78, 0.14, 0.12, 0.96) if boss.phase == 1 else (0.90, 0.28, 0.10, 0.96),
            )
            # Barra de Postura (Poise) do Boss logo abaixo
            self._draw_souls_bar(
                bx,
                by + 20.0,
                bw * 0.45,
                6.0,
                boss.poise,
                boss.poise,
                boss.max_poise,
                (0.85, 0.68, 0.25, 0.90),
            )

        # 8. Prompts Contextuais (Fogueira / Poça de Almas)
        if not bonfire_menu_open and player.alive:
            if world.bonfire.can_interact(player.pos):
                self._draw_center_prompt("[E] Descansar na Fogueira (Restaurar & Subir de Nível)")
            elif world.bloodstain.active and player.pos.distance_xz_to(world.bloodstain.pos) <= 2.5:
                self._draw_center_prompt(f"[E] Recuperar Almas Perdidas ({world.bloodstain.souls} Almas)")

        # 9. Menu da Fogueira (Level Up & Respawn)
        if bonfire_menu_open:
            self._draw_bonfire_menu(player)

        # 10. Legenda de Controles no Canto Superior Direito
        if self.show_controls and not bonfire_menu_open:
            self._draw_controls_panel()

        # 11. Banner Dramático ("YOU DIED" / "GREAT ENEMY FELLED" / "BONFIRE LIT")
        if self.banner_timer > 0.0:
            self._draw_dramatic_banner()

        # Restaura matrizes do OpenGL
        gl.glDisable(gl.GL_BLEND)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()

    def _draw_center_prompt(self, msg: str) -> None:
        pw, ph = 460, 38
        px = (self.width - pw) * 0.5
        py = self.height - 165
        self.draw_rect(px, py, pw, ph, (0.05, 0.05, 0.07, 0.88))
        self.draw_rect_border(px, py, pw, ph, (0.65, 0.55, 0.35, 0.95), 1.5)
        self.draw_text(msg, self.width * 0.5, py + ph * 0.5, font_key="ui", color=(245, 230, 185), center=True)

    def _draw_bonfire_menu(self, player: Player) -> None:
        mw, mh = 500, 350
        mx = (self.width - mw) * 0.5
        my = (self.height - mh) * 0.5
        self.draw_rect(mx, my, mw, mh, (0.05, 0.05, 0.07, 0.94))
        self.draw_rect_border(mx, my, mw, mh, (0.75, 0.60, 0.32, 0.98), 2.5)

        self.draw_text(
            "FOGUEIRA DAS CINZAS",
            self.width * 0.5,
            my + 34,
            font_key="boss",
            color=(255, 200, 110),
            center=True,
        )
        cost = player.get_level_up_cost()
        can_afford = player.souls >= cost
        cost_col = (140, 245, 150) if can_afford else (235, 110, 110)

        self.draw_text(
            f"Nível Atual: {player.level}   |   Almas: {player.souls}   |   Custo p/ Subir: {cost}",
            self.width * 0.5,
            my + 72,
            font_key="small",
            color=cost_col,
            center=True,
        )

        options = [
            f"[1] Evoluir Vigor ({player.vigor} -> {player.vigor + 1})   [HP Máx: {int(player.max_hp)} -> {int(player.max_hp + 45)}]",
            f"[2] Evoluir Endurance ({player.endurance} -> {player.endurance + 1})   [Stamina: {int(player.max_stamina)} -> {int(player.max_stamina + 14)}]",
            f"[3] Evoluir Força ({player.strength} -> {player.strength + 1})   [Dano Base: +8.5]",
            "[4] Renascer Inimigos e Boss Malakor para Revanche",
            "[E / ESC] Levantar da Fogueira e Voltar ao Jogo",
        ]
        for idx, line in enumerate(options):
            oy = my + 122 + idx * 42
            self.draw_rect(mx + 26, oy - 14, mw - 52, 32, (0.10, 0.10, 0.14, 0.85))
            self.draw_rect_border(mx + 26, oy - 14, mw - 52, 32, (0.42, 0.36, 0.25, 0.8), 1.0)
            self.draw_text(line, mx + 40, oy - 8, font_key="small", color=(235, 225, 205))

    def _draw_controls_panel(self) -> None:
        cw, ch = 285, 208
        cx = self.width - cw - 20
        cy = 20
        self.draw_rect(cx, cy, cw, ch, (0.05, 0.05, 0.07, 0.76))
        self.draw_rect_border(cx, cy, cw, ch, (0.45, 0.40, 0.28, 0.85), 1.2)
        lines = [
            "CONTROLES [F1 Ocultar]:",
            "WASD : Mover  |  Shift : Correr",
            "Mouse : Câmera 3D",
            "Espaço : Esquiva (Roll c/ I-Frames)",
            "Botão Esq. (LMB) : Combo Leve (3x)",
            "Q ou E + LMB / Tecla F : Golpe Forte",
            "Botão Dir. (RMB) : Guarda Cruzada",
            "Tecla C : Parry (Defletir Golpe)",
            "Tab / Botão Meio : Lock-On (Mira)",
            "Tecla R : Beber Estus (Cura)",
            "Tecla E : Interagir (Fogueira/Almas)",
        ]
        for i, ln in enumerate(lines):
            col = (245, 215, 140) if i == 0 else (215, 210, 200)
            self.draw_text(ln, cx + 12, cy + 10 + i * 17, font_key="small", color=col)

    def _draw_dramatic_banner(self) -> None:
        progress = 1.0 - (self.banner_timer / max(0.001, self.banner_duration))
        if progress < 0.2:
            alpha = progress / 0.2
        elif progress > 0.78:
            alpha = (1.0 - progress) / 0.22
        else:
            alpha = 1.0
        alpha = clamp(alpha, 0.0, 1.0)

        cy = self.height * 0.44
        band_h = 115.0
        self.draw_rect(0, cy - band_h * 0.5, self.width, band_h, (0.02, 0.02, 0.03, 0.86 * alpha))
        self.draw_rect(0, cy - band_h * 0.5, self.width, 2.0, (0.55, 0.45, 0.28, 0.65 * alpha))
        self.draw_rect(0, cy + band_h * 0.5 - 2.0, self.width, 2.0, (0.55, 0.45, 0.28, 0.65 * alpha))

        self.draw_text(
            self.banner_text,
            self.width * 0.5,
            cy - (10 if self.banner_subtext else 0),
            font_key="banner",
            color=self.banner_color,
            alpha=alpha,
            center=True,
        )
        if self.banner_subtext:
            self.draw_text(
                self.banner_subtext,
                self.width * 0.5,
                cy + 34,
                font_key="subbanner",
                color=(230, 220, 195),
                alpha=alpha,
                center=True,
            )

    def render_title_screen(
        self,
        selected_idx: int,
        class_idx: int,
        classes_data: list[dict],
        show_help_modal: bool,
        fade_alpha: float,
        time_accum: float,
    ) -> list[tuple[float, float, float, float]]:
        """
        Renderiza a interface 2D da Tela Inicial sobre a paisagem 3D do penhasco e Eclipse.
        Retorna a lista de retângulos clicáveis `(x, y, w, h)` dos botões do menu para suporte a mouse.
        """
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.glOrtho(0, self.width, self.height, 0, -1, 1)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()

        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_FOG)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        # Vinheta cinematográfica suave no topo e na base da tela
        gl.glBegin(gl.GL_QUADS)
        gl.glColor4f(0.01, 0.01, 0.02, 0.72)
        gl.glVertex2f(0, 0)
        gl.glVertex2f(self.width, 0)
        gl.glColor4f(0.01, 0.01, 0.02, 0.0)
        gl.glVertex2f(self.width, 135)
        gl.glVertex2f(0, 135)

        gl.glColor4f(0.01, 0.01, 0.02, 0.0)
        gl.glVertex2f(0, self.height - 150)
        gl.glVertex2f(self.width, self.height - 150)
        gl.glColor4f(0.01, 0.01, 0.02, 0.82)
        gl.glVertex2f(self.width, self.height)
        gl.glVertex2f(0, self.height)
        gl.glEnd()

        # 1. Logotipo Épico "ASHEN SOULS" no topo esquerdo/central
        title_x = self.width * 0.5
        title_y = 82.0
        # Linhas douradas horizontais estilo Elden Ring / Dark Souls
        line_w = 540.0
        self.draw_rect(title_x - line_w * 0.5, title_y - 44, line_w, 1.5, (0.72, 0.58, 0.32, 0.75))
        self.draw_rect(title_x - line_w * 0.5, title_y + 38, line_w, 2.0, (0.78, 0.62, 0.34, 0.85))
        self.draw_rect(title_x - line_w * 0.35, title_y + 43, line_w * 0.70, 1.0, (0.58, 0.45, 0.25, 0.60))

        self.draw_text(
            "A S H E N   S O U L S",
            title_x,
            title_y - 4,
            font_key="title_logo",
            color=(245, 226, 178),
            center=True,
        )
        self.draw_text(
            "O   E C L I P S E   D E   M A L A K O R",
            title_x,
            title_y + 62,
            font_key="ui",
            color=(215, 175, 115),
            center=True,
        )

        # 2. Painel de Menu no Canto Inferior Esquerdo (deixando a paisagem 3D livre no centro/direita!)
        menu_x = 58.0
        menu_y = self.height - 295.0
        btn_w = 370.0
        btn_h = 42.0
        gap = 52.0

        cur_cls = classes_data[class_idx]
        labels = [
            "INICIAR JORNADA",
            f"CLASSE: < {cur_cls['name'].upper()} >",
            "GUIA DE COMBATE & CONTROLES",
            "SAIR DO JOGO",
        ]

        button_rects: list[tuple[float, float, float, float]] = []
        pulse = 0.5 + 0.5 * math.sin(time_accum * 4.5)

        for i, label in enumerate(labels):
            by = menu_y + i * gap
            button_rects.append((menu_x, by, btn_w, btn_h))
            is_sel = i == selected_idx

            if is_sel:
                bg_col = (0.18, 0.12, 0.08, 0.88)
                border_col = (0.92, 0.74, 0.36, 0.98)
                txt_col = (255, 232, 165)
                # Indicador de brasa/losango dourado à esquerda da opção selecionada
                self.draw_rect(
                    menu_x - 16,
                    by + btn_h * 0.5 - 5,
                    10,
                    10,
                    (1.0, 0.75 + 0.2 * pulse, 0.25, 0.95),
                )
            else:
                bg_col = (0.05, 0.05, 0.07, 0.74)
                border_col = (0.42, 0.36, 0.25, 0.70)
                txt_col = (205, 198, 185)

            self.draw_rect(menu_x, by, btn_w, btn_h, bg_col)
            self.draw_rect_border(menu_x, by, btn_w, btn_h, border_col, 2.0 if is_sel else 1.2)
            self.draw_text(
                label,
                menu_x + 22,
                by + btn_h * 0.5,
                font_key="ui",
                color=txt_col,
                center=False,
            )

        # 3. Cartão de Atributos da Classe Selecionada (ao lado do menu quando aplicável)
        card_x = menu_x + btn_w + 26.0
        card_y = menu_y
        card_w = 335.0
        card_h = 196.0
        self.draw_rect(card_x, card_y, card_w, card_h, (0.05, 0.05, 0.07, 0.78))
        self.draw_rect_border(card_x, card_y, card_w, card_h, (0.58, 0.48, 0.30, 0.85), 1.5)

        self.draw_text(
            f"ORIGEM: {cur_cls['name']}",
            card_x + 18,
            card_y + 16,
            font_key="ui",
            color=(245, 215, 140),
        )
        self.draw_text(
            cur_cls["desc"],
            card_x + 18,
            card_y + 46,
            font_key="small",
            color=(210, 200, 185),
        )
        stat_lines = [
            f"Vigor (Vida Máxima): {cur_cls['vigor']}",
            f"Endurance (Stamina): {cur_cls['endurance']}",
            f"Força (Dano Físico): {cur_cls['strength']}",
            f"Frascos de Estus Iniciais: {cur_cls['estus']}",
        ]
        for s_i, s_txt in enumerate(stat_lines):
            self.draw_text(
                s_txt,
                card_x + 18,
                card_y + 82 + s_i * 25,
                font_key="small",
                color=(235, 228, 210),
            )

        # Rodapé de dica de navegação
        self.draw_text(
            "[W/S ou Mouse] Navegar   |   [A/D] Trocar Classe   |   [ENTER ou Clique] Confirmar",
            self.width * 0.5,
            self.height - 26.0,
            font_key="small",
            color=(195, 185, 165),
            center=True,
        )

        # 4. Modal de Guia de Combate (se aberto)
        if show_help_modal:
            mw, mh = 620.0, 390.0
            mx = (self.width - mw) * 0.5
            my = (self.height - mh) * 0.5
            self.draw_rect(mx, my, mw, mh, (0.04, 0.04, 0.06, 0.95))
            self.draw_rect_border(mx, my, mw, mh, (0.82, 0.66, 0.34, 0.98), 2.5)
            self.draw_text(
                "MANUAL DE COMBATE SOULSLIKE",
                self.width * 0.5,
                my + 32,
                font_key="boss",
                color=(255, 215, 130),
                center=True,
            )
            help_lines = [
                "• MOVIMENTO & CÂMERA: WASD move o Cavaleiro; Mouse gira a câmera 3D.",
                "• ESQUIVA COM I-FRAMES (Espaço): Durante o rolamento você fica invencível",
                "  e pode atravessar espadas e ondas de choque sem sofrer dano.",
                "• COMBO DE ATAQUES (Botão Esq. Mouse): Clique até 3 vezes para um combo.",
                "• GOLPE PESADO (Tecla F ou Q+Clique): Causa alto dano de Postura (Poise).",
                "• DEFESA (Botão Dir. Mouse) & PARRY (Tecla C): Apertar C no instante do",
                "  ataque inimigo deflete o golpe e abre guarda para DANO CRÍTICO!",
                "• LOCK-ON (Tab ou Botão do Meio): Trava a câmera no inimigo ou no Boss.",
                "• FOGUEIRA (Tecla E): Restaura Vida/Estus e usa Almas para subir de nível.",
                "",
                "Pressione [ESC], [ENTER] ou Clique para fechar este guia.",
            ]
            for h_i, h_ln in enumerate(help_lines):
                col = (245, 215, 140) if h_i == len(help_lines) - 1 else (230, 222, 208)
                self.draw_text(h_ln, mx + 32, my + 72 + h_i * 26, font_key="small", color=col)

        # 5. Fade-out cinematográfico ao iniciar o jogo
        if fade_alpha > 0.0:
            self.draw_rect(0, 0, self.width, self.height, (0.0, 0.0, 0.0, clamp(fade_alpha, 0.0, 1.0)))

        gl.glDisable(gl.GL_BLEND)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()

        return button_rects

