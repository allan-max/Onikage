"""
Renderizador 3D em OpenGL puro (PyOpenGL + GLU).
Construído do zero sem engine pronta:
- Pipeline de Projeção Perspectiva 3D e Câmera (`gluPerspective`, `gluLookAt`)
- Iluminação Dinâmica 3D (`GL_LIGHT0` luar frio + `GL_LIGHT1` luz quente da Fogueira / Chamas do Boss)
- Neblina Atmosférica Exponencial (`GL_FOG`) estilo Dark Souls
- Malhas 3D Poligonais/Facetadas compiladas em Display Lists (`glGenLists`) para rodar a 60+ FPS
- Personagens com Anatomia Multi-Segmentada (Quadril, Coxa, Joelho dobrável, Canela, Bota, Abdômen, Peitoral em V, Ombreira Angular, Braço, Cotovelo, Antebraço, Manopla, Elmo Facetado com Viseira, Escudo Kite em V e Espada com Ponta e Chanfro)
"""

import math
import OpenGL.GL as gl
import OpenGL.GLU as glu
from engine.math3d import Vec3, clamp
from game.entities import (
    Player,
    PlayerState,
    HollowEnemy,
    EnemyState,
    BossMalakor,
    BossState,
)


class Renderer3D:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.time_accum = 0.0

        # IDs de Display Lists para geometria rápida e facetada
        self.dl_box = 0
        self.dl_pyramid = 0
        self.dl_octa_prism = 0
        self.dl_sword_blade = 0
        self.dl_kite_shield = 0
        self.dl_cylinder = 0
        self.dl_sphere_smooth = 0
        self.dl_cyl_smooth = 0
        self.dl_floor = 0
        self.dl_walls = 0
        self.dl_title_vista = 0

        self._init_opengl()
        self._compile_display_lists()
        self._compile_title_landscape_list()

    def _init_opengl(self) -> None:
        gl.glViewport(0, 0, self.width, self.height)
        gl.glClearColor(0.04, 0.045, 0.065, 1.0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glShadeModel(gl.GL_SMOOTH)
        gl.glEnable(gl.GL_NORMALIZE)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glColorMaterial(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE)

        # Neblina atmosférica estilo Dark Souls
        gl.glEnable(gl.GL_FOG)
        gl.glFogi(gl.GL_FOG_MODE, gl.GL_EXP2)
        gl.glFogfv(gl.GL_FOG_COLOR, (0.04, 0.045, 0.065, 1.0))
        gl.glFogf(gl.GL_FOG_DENSITY, 0.020)
        gl.glHint(gl.GL_FOG_HINT, gl.GL_NICEST)

        # Iluminação 3D com brilho especular metálico para destacar as faces das armaduras
        gl.glEnable(gl.GL_LIGHTING)
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT, (0.22, 0.23, 0.28, 1.0))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (0.45, 0.48, 0.52, 1.0))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 36.0)

        # Luz 0: Luar direcional frio vindo do alto da catedral
        gl.glEnable(gl.GL_LIGHT0)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (0.65, 0.72, 0.86, 1.0))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, (0.60, 0.65, 0.75, 1.0))

        # Luz 1: Luz pontual quente (Fogueira / Lâmina de fogo do Boss)
        gl.glEnable(gl.GL_LIGHT1)
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, (1.0, 0.58, 0.18, 1.0))
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_SPECULAR, (1.0, 0.50, 0.15, 1.0))
        gl.glLightf(gl.GL_LIGHT1, gl.GL_CONSTANT_ATTENUATION, 0.5)
        gl.glLightf(gl.GL_LIGHT1, gl.GL_LINEAR_ATTENUATION, 0.06)
        gl.glLightf(gl.GL_LIGHT1, gl.GL_QUADRATIC_ATTENUATION, 0.008)

    def _compile_display_lists(self) -> None:
        quadric = glu.gluNewQuadric()
        glu.gluQuadricNormals(quadric, glu.GLU_SMOOTH)

        # 1. Cubo unitário centrado na origem [-0.5, 0.5]
        self.dl_box = gl.glGenLists(1)
        gl.glNewList(self.dl_box, gl.GL_COMPILE)
        gl.glBegin(gl.GL_QUADS)
        # Frente (+Z)
        gl.glNormal3f(0, 0, 1)
        gl.glVertex3f(-0.5, -0.5, 0.5)
        gl.glVertex3f(0.5, -0.5, 0.5)
        gl.glVertex3f(0.5, 0.5, 0.5)
        gl.glVertex3f(-0.5, 0.5, 0.5)
        # Trás (-Z)
        gl.glNormal3f(0, 0, -1)
        gl.glVertex3f(0.5, -0.5, -0.5)
        gl.glVertex3f(-0.5, -0.5, -0.5)
        gl.glVertex3f(-0.5, 0.5, -0.5)
        gl.glVertex3f(0.5, 0.5, -0.5)
        # Topo (+Y)
        gl.glNormal3f(0, 1, 0)
        gl.glVertex3f(-0.5, 0.5, 0.5)
        gl.glVertex3f(0.5, 0.5, 0.5)
        gl.glVertex3f(0.5, 0.5, -0.5)
        gl.glVertex3f(-0.5, 0.5, -0.5)
        # Base (-Y)
        gl.glNormal3f(0, -1, 0)
        gl.glVertex3f(-0.5, -0.5, -0.5)
        gl.glVertex3f(0.5, -0.5, -0.5)
        gl.glVertex3f(0.5, -0.5, 0.5)
        gl.glVertex3f(-0.5, -0.5, 0.5)
        # Direita (+X)
        gl.glNormal3f(1, 0, 0)
        gl.glVertex3f(0.5, -0.5, 0.5)
        gl.glVertex3f(0.5, -0.5, -0.5)
        gl.glVertex3f(0.5, 0.5, -0.5)
        gl.glVertex3f(0.5, 0.5, 0.5)
        # Esquerda (-X)
        gl.glNormal3f(-1, 0, 0)
        gl.glVertex3f(-0.5, -0.5, -0.5)
        gl.glVertex3f(-0.5, -0.5, 0.5)
        gl.glVertex3f(-0.5, 0.5, 0.5)
        gl.glVertex3f(-0.5, 0.5, -0.5)
        gl.glEnd()
        gl.glEndList()

        # 2. Pirâmide / Espinho de 4 faces (base [-0.5, 0.5] em Y=0, ápice em Y=1)
        self.dl_pyramid = gl.glGenLists(1)
        gl.glNewList(self.dl_pyramid, gl.GL_COMPILE)
        gl.glBegin(gl.GL_TRIANGLES)
        # Frente
        gl.glNormal3f(0.0, 0.447, 0.894)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(-0.5, 0.0, 0.5)
        gl.glVertex3f(0.5, 0.0, 0.5)
        # Direita
        gl.glNormal3f(0.894, 0.447, 0.0)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(0.5, 0.0, 0.5)
        gl.glVertex3f(0.5, 0.0, -0.5)
        # Trás
        gl.glNormal3f(0.0, 0.447, -0.894)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(0.5, 0.0, -0.5)
        gl.glVertex3f(-0.5, 0.0, -0.5)
        # Esquerda
        gl.glNormal3f(-0.894, 0.447, 0.0)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(-0.5, 0.0, -0.5)
        gl.glVertex3f(-0.5, 0.0, 0.5)
        gl.glEnd()
        gl.glEndList()

        # 3. Prisma Octogonal Facetado (para elmos, braceletes, grevas — sem aspecto de bola!)
        self.dl_octa_prism = gl.glGenLists(1)
        gl.glNewList(self.dl_octa_prism, gl.GL_COMPILE)
        gl.glBegin(gl.GL_QUADS)
        for i in range(8):
            a0 = i * (2.0 * math.pi / 8.0) + (math.pi / 8.0)
            a1 = (i + 1) * (2.0 * math.pi / 8.0) + (math.pi / 8.0)
            am = (a0 + a1) * 0.5
            gl.glNormal3f(math.cos(am), 0.0, math.sin(am))
            x0, z0 = math.cos(a0) * 0.5, math.sin(a0) * 0.5
            x1, z1 = math.cos(a1) * 0.5, math.sin(a1) * 0.5
            gl.glVertex3f(x0, -0.5, z0)
            gl.glVertex3f(x1, -0.5, z1)
            gl.glVertex3f(x1, 0.5, z1)
            gl.glVertex3f(x0, 0.5, z0)
        gl.glEnd()
        # Tampas superior e inferior
        for y_val, ny in ((0.5, 1.0), (-0.5, -1.0)):
            gl.glBegin(gl.GL_TRIANGLE_FAN)
            gl.glNormal3f(0.0, ny, 0.0)
            gl.glVertex3f(0.0, y_val, 0.0)
            for i in range(9):
                a = i * (2.0 * math.pi / 8.0) + (math.pi / 8.0)
                gl.glVertex3f(math.cos(a) * 0.5, y_val, math.sin(a) * 0.5)
            gl.glEnd()
        gl.glEndList()

        # 4. Lâmina de Espada Facetada (seção de diamante + ponta afiada em V, comprimento 1 em +Y)
        self.dl_sword_blade = gl.glGenLists(1)
        gl.glNewList(self.dl_sword_blade, gl.GL_COMPILE)
        # Corpo da lâmina (Y=0 até Y=0.82)
        gl.glBegin(gl.GL_QUADS)
        # Frente-Direita
        gl.glNormal3f(0.6, 0.0, 0.8)
        gl.glVertex3f(0.0, 0.0, 0.5)
        gl.glVertex3f(0.5, 0.0, 0.0)
        gl.glVertex3f(0.38, 0.82, 0.0)
        gl.glVertex3f(0.0, 0.82, 0.4)
        # Frente-Esquerda
        gl.glNormal3f(-0.6, 0.0, 0.8)
        gl.glVertex3f(-0.5, 0.0, 0.0)
        gl.glVertex3f(0.0, 0.0, 0.5)
        gl.glVertex3f(0.0, 0.82, 0.4)
        gl.glVertex3f(-0.38, 0.82, 0.0)
        # Trás-Direita
        gl.glNormal3f(0.6, 0.0, -0.8)
        gl.glVertex3f(0.5, 0.0, 0.0)
        gl.glVertex3f(0.0, 0.0, -0.5)
        gl.glVertex3f(0.0, 0.82, -0.4)
        gl.glVertex3f(0.38, 0.82, 0.0)
        # Trás-Esquerda
        gl.glNormal3f(-0.6, 0.0, -0.8)
        gl.glVertex3f(0.0, 0.0, -0.5)
        gl.glVertex3f(-0.5, 0.0, 0.0)
        gl.glVertex3f(-0.38, 0.82, 0.0)
        gl.glVertex3f(0.0, 0.82, -0.4)
        gl.glEnd()

        # Ponta aguda da espada (Y=0.82 até Y=1.0)
        gl.glBegin(gl.GL_TRIANGLES)
        gl.glNormal3f(0.5, 0.3, 0.8)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(0.0, 0.82, 0.4)
        gl.glVertex3f(0.38, 0.82, 0.0)

        gl.glNormal3f(-0.5, 0.3, 0.8)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(-0.38, 0.82, 0.0)
        gl.glVertex3f(0.0, 0.82, 0.4)

        gl.glNormal3f(0.5, 0.3, -0.8)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(0.38, 0.82, 0.0)
        gl.glVertex3f(0.0, 0.82, -0.4)

        gl.glNormal3f(-0.5, 0.3, -0.8)
        gl.glVertex3f(0.0, 1.0, 0.0)
        gl.glVertex3f(0.0, 0.82, -0.4)
        gl.glVertex3f(-0.38, 0.82, 0.0)
        gl.glEnd()
        gl.glEndList()

        # 5. Escudo Heráldico (Kite Shield curvado em V e pontudo embaixo!)
        self.dl_kite_shield = gl.glGenLists(1)
        gl.glNewList(self.dl_kite_shield, gl.GL_COMPILE)
        gl.glBegin(gl.GL_TRIANGLES)
        # Metade superior esquerda (curvada em V)
        gl.glNormal3f(0.85, 0.0, 0.52)
        gl.glVertex3f(0.06, 0.36, 0.0)
        gl.glVertex3f(0.06, -0.05, 0.0)
        gl.glVertex3f(-0.02, 0.34, 0.25)

        gl.glVertex3f(-0.02, 0.34, 0.25)
        gl.glVertex3f(0.06, -0.05, 0.0)
        gl.glVertex3f(-0.02, -0.05, 0.22)

        # Metade superior direita
        gl.glNormal3f(0.85, 0.0, -0.52)
        gl.glVertex3f(0.06, 0.36, 0.0)
        gl.glVertex3f(-0.02, 0.34, -0.25)
        gl.glVertex3f(0.06, -0.05, 0.0)

        gl.glVertex3f(0.06, -0.05, 0.0)
        gl.glVertex3f(-0.02, 0.34, -0.25)
        gl.glVertex3f(-0.02, -0.05, -0.22)

        # Ponta inferior esquerda do escudo (afunila até Y = -0.42)
        gl.glNormal3f(0.85, -0.2, 0.5)
        gl.glVertex3f(0.06, -0.05, 0.0)
        gl.glVertex3f(0.04, -0.42, 0.0)
        gl.glVertex3f(-0.02, -0.05, 0.22)

        # Ponta inferior direita do escudo
        gl.glNormal3f(0.85, -0.2, -0.5)
        gl.glVertex3f(0.06, -0.05, 0.0)
        gl.glVertex3f(-0.02, -0.05, -0.22)
        gl.glVertex3f(0.04, -0.42, 0.0)
        gl.glEnd()
        gl.glEndList()

        # 6. Cilindro vertical unitário (para pilares do cenário)
        self.dl_cylinder = gl.glGenLists(1)
        gl.glNewList(self.dl_cylinder, gl.GL_COMPILE)
        gl.glPushMatrix()
        gl.glRotatef(-90.0, 1.0, 0.0, 0.0)
        glu.gluCylinder(quadric, 1.0, 1.0, 1.0, 24, 1)
        gl.glTranslatef(0.0, 0.0, 1.0)
        glu.gluDisk(quadric, 0.0, 1.0, 24, 1)
        gl.glPopMatrix()
        gl.glEndList()

        # 6B. Esfera Suave de Alta Subdivisão (24x18 segmentos com GLU_SMOOTH)
        self.dl_sphere_smooth = gl.glGenLists(1)
        gl.glNewList(self.dl_sphere_smooth, gl.GL_COMPILE)
        glu.gluSphere(quadric, 0.5, 24, 18)
        gl.glEndList()

        # 6C. Cilindro Fechado Suave de 24 lados centrado na origem (Y de -0.5 a +0.5, diâmetro 1.0)
        self.dl_cyl_smooth = gl.glGenLists(1)
        gl.glNewList(self.dl_cyl_smooth, gl.GL_COMPILE)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.5, 0.0)
        gl.glRotatef(-90.0, 1.0, 0.0, 0.0)
        glu.gluCylinder(quadric, 0.5, 0.5, 1.0, 24, 2)
        gl.glPushMatrix()
        gl.glRotatef(180.0, 1.0, 0.0, 0.0)
        glu.gluDisk(quadric, 0.0, 0.5, 24, 1)
        gl.glPopMatrix()
        gl.glTranslatef(0.0, 0.0, 1.0)
        glu.gluDisk(quadric, 0.0, 0.5, 24, 1)
        gl.glPopMatrix()
        gl.glEndList()

        # 7. Piso de pedra gótica da Catedral
        self.dl_floor = gl.glGenLists(1)
        gl.glNewList(self.dl_floor, gl.GL_COMPILE)
        gl.glNormal3f(0.0, 1.0, 0.0)
        tile_size = 2.0
        half_n = 20
        gl.glBegin(gl.GL_QUADS)
        for ix in range(-half_n, half_n):
            for iz in range(-half_n, half_n):
                x0 = ix * tile_size
                z0 = iz * tile_size
                dist = math.sqrt((x0 + 1.0) ** 2 + (z0 + 1.0) ** 2)
                if dist > 40.0:
                    continue
                checker = (ix + iz) & 1
                if 15.8 <= dist <= 17.2:
                    gl.glColor3f(0.24, 0.21, 0.18)
                elif 7.6 <= dist <= 8.2:
                    gl.glColor3f(0.22, 0.18, 0.16)
                elif checker == 0:
                    gl.glColor3f(0.13, 0.14, 0.16)
                else:
                    gl.glColor3f(0.10, 0.11, 0.13)
                gl.glVertex3f(x0, 0.0, z0)
                gl.glVertex3f(x0, 0.0, z0 + tile_size)
                gl.glVertex3f(x0 + tile_size, 0.0, z0 + tile_size)
                gl.glVertex3f(x0 + tile_size, 0.0, z0)
        gl.glEnd()

        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(0.06, 0.065, 0.08)
        gl.glLineWidth(1.0)
        for ring_r in (8.0, 16.5, 28.0):
            gl.glBegin(gl.GL_LINE_LOOP)
            for s in range(64):
                a = s * (2.0 * math.pi / 64.0)
                gl.glVertex3f(math.cos(a) * ring_r, 0.02, math.sin(a) * ring_r)
            gl.glEnd()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEndList()

        # 8. Muralhas externas da Catedral
        self.dl_walls = gl.glGenLists(1)
        gl.glNewList(self.dl_walls, gl.GL_COMPILE)
        segs = 32
        r_wall = 38.2
        h_wall = 13.0
        gl.glBegin(gl.GL_QUADS)
        for i in range(segs):
            a0 = i * (2.0 * math.pi / segs)
            a1 = (i + 1) * (2.0 * math.pi / segs)
            x0, z0 = math.cos(a0) * r_wall, math.sin(a0) * r_wall
            x1, z1 = math.cos(a1) * r_wall, math.sin(a1) * r_wall
            nx, nz = -math.cos((a0 + a1) * 0.5), -math.sin((a0 + a1) * 0.5)
            gl.glNormal3f(nx, 0.0, nz)
            shade = 0.14 if (i & 1) == 0 else 0.11
            gl.glColor3f(shade, shade + 0.01, shade + 0.03)
            gl.glVertex3f(x0, 0.0, z0)
            gl.glVertex3f(x1, 0.0, z1)
            gl.glColor3f(shade * 0.6, shade * 0.65, shade * 0.8)
            gl.glVertex3f(x1, h_wall, z1)
            gl.glVertex3f(x0, h_wall, z0)
        gl.glEnd()
        gl.glEndList()

        glu.gluDeleteQuadric(quadric)

    def draw_box(self, sx: float, sy: float, sz: float) -> None:
        gl.glPushMatrix()
        gl.glScalef(sx, sy, sz)
        gl.glCallList(self.dl_box)
        gl.glPopMatrix()

    def draw_pyramid(self, sx: float, sy: float, sz: float) -> None:
        gl.glPushMatrix()
        gl.glScalef(sx, sy, sz)
        gl.glCallList(self.dl_pyramid)
        gl.glPopMatrix()

    def draw_octa(self, sx: float, sy: float, sz: float) -> None:
        gl.glPushMatrix()
        gl.glScalef(sx, sy, sz)
        gl.glCallList(self.dl_octa_prism)
        gl.glPopMatrix()

    def draw_sword_blade(self, width: float, length: float, thickness: float) -> None:
        gl.glPushMatrix()
        gl.glScalef(width, length, thickness)
        gl.glCallList(self.dl_sword_blade)
        gl.glPopMatrix()

    def draw_cylinder(self, radius: float, height: float) -> None:
        gl.glPushMatrix()
        gl.glScalef(radius, height, radius)
        gl.glCallList(self.dl_cylinder)
        gl.glPopMatrix()

    def draw_tapered_torso(
        self,
        bot_x: float,
        bot_z: float,
        top_x: float,
        top_z: float,
        height: float,
    ) -> None:
        """
        Desenha um tronco piramidal chanfrado (de Y=0 até Y=height).
        Ideal para peitorais em V (ombros largos, cintura fina), coxas, grevas e ombreiras!
        """
        bx, bz = bot_x * 0.5, bot_z * 0.5
        tx, tz = top_x * 0.5, top_z * 0.5
        h = height
        gl.glBegin(gl.GL_QUADS)
        # Frente (+Z)
        gl.glNormal3f(0.0, 0.15, 0.98)
        gl.glVertex3f(-bx, 0.0, bz)
        gl.glVertex3f(bx, 0.0, bz)
        gl.glVertex3f(tx, h, tz)
        gl.glVertex3f(-tx, h, tz)
        # Trás (-Z)
        gl.glNormal3f(0.0, 0.15, -0.98)
        gl.glVertex3f(bx, 0.0, -bz)
        gl.glVertex3f(-bx, 0.0, -bz)
        gl.glVertex3f(-tx, h, -tz)
        gl.glVertex3f(tx, h, -tz)
        # Direita (+X)
        gl.glNormal3f(0.98, 0.15, 0.0)
        gl.glVertex3f(bx, 0.0, bz)
        gl.glVertex3f(bx, 0.0, -bz)
        gl.glVertex3f(tx, h, -tz)
        gl.glVertex3f(tx, h, tz)
        # Esquerda (-X)
        gl.glNormal3f(-0.98, 0.15, 0.0)
        gl.glVertex3f(-bx, 0.0, -bz)
        gl.glVertex3f(-bx, 0.0, bz)
        gl.glVertex3f(-tx, h, tz)
        gl.glVertex3f(-tx, h, -tz)
        # Topo (+Y)
        gl.glNormal3f(0.0, 1.0, 0.0)
        gl.glVertex3f(-tx, h, tz)
        gl.glVertex3f(tx, h, tz)
        gl.glVertex3f(tx, h, -tz)
        gl.glVertex3f(-tx, h, -tz)
        # Base (-Y)
        gl.glNormal3f(0.0, -1.0, 0.0)
        gl.glVertex3f(-bx, 0.0, -bz)
        gl.glVertex3f(bx, 0.0, -bz)
        gl.glVertex3f(bx, 0.0, bz)
        gl.glVertex3f(-bx, 0.0, bz)
        gl.glEnd()

    def _set_material_forged_metal(self) -> None:
        """Ativa reflexo nítido de metal batido/forjado nas facetas planas."""
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (0.62, 0.64, 0.70, 1.0))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 42.0)

    def _set_material_heavy_cloth(self) -> None:
        """Ativa material de tecido pesado com facetas secas (Hakama, Haori, Obi)."""
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_SPECULAR, (0.08, 0.08, 0.09, 1.0))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK, gl.GL_SHININESS, 10.0)

    @staticmethod
    def _emit_flat_quad(
        p0: tuple[float, float, float],
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        p3: tuple[float, float, float],
    ) -> None:
        """Emite um quadrilátero com sua própria normal plana exata (Flat Shading por face)."""
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > 1e-7:
            nx /= length
            ny /= length
            nz /= length
        gl.glNormal3f(nx, ny, nz)
        gl.glVertex3f(*p0)
        gl.glVertex3f(*p1)
        gl.glVertex3f(*p2)
        gl.glVertex3f(*p3)

    @staticmethod
    def _emit_flat_tri(
        p0: tuple[float, float, float],
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
    ) -> None:
        """Emite um triângulo com sua própria normal plana exata (Flat Shading por face)."""
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > 1e-7:
            nx /= length
            ny /= length
            nz /= length
        gl.glNormal3f(nx, ny, nz)
        gl.glVertex3f(*p0)
        gl.glVertex3f(*p1)
        gl.glVertex3f(*p2)

    def draw_chiseled_prism(
        self,
        rx_bot: float,
        rz_bot: float,
        rx_top: float,
        rz_top: float,
        height: float,
        sides: int = 8,
        cap_bot: bool = False,
        cap_top: bool = False,
    ) -> None:
        """
        Desenha um prisma afunilado chanfrado de 6 ou 8 lados (Chiseled Low-Poly)
        de Y=0 até Y=height, com normais planas por face (Flat Shading).
        """
        offset_rad = math.pi / sides
        gl.glBegin(gl.GL_QUADS)
        for i in range(sides):
            a0 = (i / sides) * (2.0 * math.pi) + offset_rad
            a1 = ((i + 1) / sides) * (2.0 * math.pi) + offset_rad
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)

            # Ordenação anti-horária olhando de fora para que a normal aponte para fora
            p0 = (c1 * rx_bot, 0.0, s1 * rz_bot)
            p1 = (c0 * rx_bot, 0.0, s0 * rz_bot)
            p2 = (c0 * rx_top, height, s0 * rz_top)
            p3 = (c1 * rx_top, height, s1 * rz_top)
            self._emit_flat_quad(p0, p1, p2, p3)
        gl.glEnd()

        if cap_top and rx_top > 0.002:
            gl.glBegin(gl.GL_TRIANGLE_FAN)
            gl.glNormal3f(0.0, 1.0, 0.0)
            gl.glVertex3f(0.0, height, 0.0)
            for i in range(sides, -1, -1):
                a = (i / sides) * (2.0 * math.pi) + offset_rad
                gl.glVertex3f(math.cos(a) * rx_top, height, math.sin(a) * rz_top)
            gl.glEnd()

        if cap_bot and rx_bot > 0.002:
            gl.glBegin(gl.GL_TRIANGLE_FAN)
            gl.glNormal3f(0.0, -1.0, 0.0)
            gl.glVertex3f(0.0, 0.0, 0.0)
            for i in range(sides + 1):
                a = (i / sides) * (2.0 * math.pi) + offset_rad
                gl.glVertex3f(math.cos(a) * rx_bot, 0.0, math.sin(a) * rz_bot)
            gl.glEnd()

    def draw_trapezoid_plate(
        self,
        bot_w: float,
        top_w: float,
        height: float,
        thickness: float,
    ) -> None:
        """
        Desenha uma placa trapezoidal chanfrada (6 faces planas com quinas anguladas,
        não um cubo reto de 90 graus) para placas de Shikoro, Sode e Kusazuri.
        """
        bw = bot_w * 0.5
        tw = top_w * 0.5
        th = thickness * 0.5
        # Leve chanfro nas bordas para refletir luz nas quinas
        bev = min(bw, tw) * 0.14
        gl.glBegin(gl.GL_QUADS)
        # Face Frontal (+Z)
        self._emit_flat_quad((-bw + bev, 0.0, th), (bw - bev, 0.0, th), (tw - bev, height, th), (-tw + bev, height, th))
        # Face Traseira (-Z)
        self._emit_flat_quad((bw - bev, 0.0, -th), (-bw + bev, 0.0, -th), (-tw + bev, height, -th), (tw - bev, height, -th))
        # Chanfro Lateral Direito (+X)
        self._emit_flat_quad((bw - bev, 0.0, th), (bw, 0.0, 0.0), (tw, height, 0.0), (tw - bev, height, th))
        self._emit_flat_quad((bw, 0.0, 0.0), (bw - bev, 0.0, -th), (tw - bev, height, -th), (tw, height, 0.0))
        # Chanfro Lateral Esquerdo (-X)
        self._emit_flat_quad((-bw, 0.0, 0.0), (-bw + bev, 0.0, th), (-tw + bev, height, th), (-tw, height, 0.0))
        self._emit_flat_quad((-bw + bev, 0.0, -th), (-bw, 0.0, 0.0), (-tw, height, 0.0), (-tw + bev, height, -th))
        # Topo e Base
        self._emit_flat_quad((-tw + bev, height, th), (tw - bev, height, th), (tw - bev, height, -th), (-tw + bev, height, -th))
        self._emit_flat_quad((-bw + bev, 0.0, -th), (bw - bev, 0.0, -th), (bw - bev, 0.0, th), (-bw + bev, 0.0, th))
        gl.glEnd()

    def _draw_samurai_sode(self, side_sign: float) -> None:
        """
        Desenha a ombreira samurai (Sode) no estilo Stylized Hard-Surface:
        3 placas trapezoidais finas sobrepostas em degraus, dobradas em ângulo obtuso (135°)
        sobre os ombros, com bordas douradas (#C59B27).
        """
        self._set_material_forged_metal()
        obsidian = (0.133, 0.141, 0.157)  # #222428
        lead_grey = (0.20, 0.22, 0.27)
        old_gold = (0.773, 0.608, 0.153)   # #C59B27
        crimson = (0.545, 0.118, 0.118)    # #8B1E1E

        gl.glPushMatrix()
        gl.glTranslatef(side_sign * 0.03, 0.02, 0.0)

        # Seção 1 (Topo do ombro): Placa superior inclinada a -20°
        gl.glPushMatrix()
        gl.glRotatef(side_sign * -20.0, 0.0, 0.0, 1.0)
        gl.glRotatef(90.0, 0.0, 1.0, 0.0)
        gl.glColor3f(*old_gold)
        self.draw_trapezoid_plate(0.24, 0.20, 0.11, 0.022)
        gl.glColor3f(*obsidian)
        self.draw_trapezoid_plate(0.22, 0.18, 0.095, 0.028)
        gl.glPopMatrix()

        # Dobra em ângulo obtuso de 135° (mudança de 45° a partir de -20° -> -65° na lateral do braço!)
        # Construída com 3 placas sobrepostas em degraus (stepped lames)
        gl.glTranslatef(side_sign * 0.055, -0.02, 0.0)
        gl.glRotatef(side_sign * -65.0, 0.0, 0.0, 1.0)
        gl.glRotatef(90.0, 0.0, 1.0, 0.0)

        for step_i in range(3):
            y_step = -0.09 - step_i * 0.075
            z_step = step_i * 0.012 * side_sign
            w_b = 0.25 - step_i * 0.012
            w_t = 0.23 - step_i * 0.012
            gl.glPushMatrix()
            gl.glTranslatef(0.0, y_step, z_step)
            # Borda chanfrada em ouro velho
            gl.glColor3f(*old_gold)
            self.draw_trapezoid_plate(w_b + 0.02, w_t + 0.02, 0.082, 0.020)
            # Face de ferro forjado
            gl.glColor3f(*(obsidian if step_i % 2 == 0 else lead_grey))
            self.draw_trapezoid_plate(w_b, w_t, 0.072, 0.026)
            # Amarração carmesim central
            gl.glColor3f(*crimson)
            self.draw_trapezoid_plate(0.05, 0.05, 0.045, 0.032)
            gl.glPopMatrix()

        gl.glPopMatrix()

    def _draw_samurai_helmet(self, visor_glow: tuple[float, float, float] | None = None) -> None:
        """
        Desenha a cabeça e o Elmo (Kabuto) em proporção heroica (-20% menor que os ombros)
        e estética Chiseled Hard-Surface:
        - Topo do Kabuto facetado (cone/domo de 8 lados com quinas vivas em #222428)
        - Aba protetora de nuca (Shikoro) feita com placa trapezoidal angulada em 3 faces planas
        - Chifres dourados (Kuwagata) em lâminas planas chanfradas e pontiagudas em 'V' agressivo (#C59B27)
        - Máscara Menpo facetada de 6 lados com queixeira aguda e detalhes em #8B1E1E
        """
        self._set_material_forged_metal()
        obsidian_helm = (0.133, 0.141, 0.157)  # #222428
        old_gold = (0.773, 0.608, 0.153)       # #C59B27
        crimson = (0.545, 0.118, 0.118)        # #8B1E1E

        # 1. Rosto e Máscara Samurai (Menpo): Prisma Hexagonal Afunilado com Queixeira Esculpida
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.07, 0.01)
        gl.glColor3f(0.08, 0.085, 0.10)
        # Mandíbula afunilada em 6 lados (quinas vivas no queixo e maçãs do rosto)
        self.draw_chiseled_prism(0.055, 0.065, 0.082, 0.090, 0.11, sides=6, cap_bot=True)
        # Detalhe chanfrado vermelho-escuro (#8B1E1E) na guarda bucal do Menpo
        gl.glColor3f(*crimson)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.025, 0.072)
        gl.glRotatef(-12.0, 1.0, 0.0, 0.0)
        self.draw_trapezoid_plate(0.09, 0.11, 0.032, 0.022)
        gl.glPopMatrix()
        gl.glPopMatrix()

        # 2. Topo do Kabuto (Domo/Cone Facetado de 8 Lados com Quinas Vivas!)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.02, 0.0)
        gl.glColor3f(*obsidian_helm)
        # Banda inferior de 8 lados
        self.draw_chiseled_prism(0.102, 0.110, 0.092, 0.100, 0.062, sides=8)
        # Cone superior chanfrado de 8 lados fechando no topo
        gl.glTranslatef(0.0, 0.062, 0.0)
        self.draw_chiseled_prism(0.092, 0.100, 0.028, 0.032, 0.065, sides=8, cap_top=True)
        # Crista central chanfrada em ouro velho
        gl.glColor3f(*old_gold)
        gl.glTranslatef(0.0, -0.04, 0.0)
        self.draw_chiseled_prism(0.016, 0.105, 0.012, 0.085, 0.055, sides=6, cap_top=True)
        gl.glPopMatrix()

        # Viseira Frontal Angulada (Mabisashi)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.025, 0.095)
        gl.glRotatef(68.0, 1.0, 0.0, 0.0)
        gl.glColor3f(*obsidian_helm)
        self.draw_trapezoid_plate(0.16, 0.13, 0.055, 0.018)
        gl.glColor3f(*old_gold)
        self.draw_trapezoid_plate(0.168, 0.160, 0.016, 0.022)
        gl.glPopMatrix()

        # 3. Shikoro: Placa Trapezoidal Angulada em 3 Faces Planas (Traseira + 2 Laterais Dobradas)
        # Face Traseira Central
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.10, -0.115)
        gl.glRotatef(-24.0, 1.0, 0.0, 0.0)
        gl.glColor3f(*obsidian_helm)
        self.draw_trapezoid_plate(0.19, 0.14, 0.14, 0.020)
        gl.glColor3f(*crimson)
        self.draw_trapezoid_plate(0.175, 0.155, 0.045, 0.024)
        gl.glColor3f(*old_gold)
        self.draw_trapezoid_plate(0.198, 0.190, 0.020, 0.025)
        gl.glPopMatrix()

        # 2 Faces Laterais Planas do Shikoro (dobradas em ângulo de 52° em relação à face traseira)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.095, -0.10, -0.045)
            gl.glRotatef(s * 58.0, 0.0, 1.0, 0.0)
            gl.glRotatef(-24.0, 1.0, 0.0, 0.0)
            gl.glColor3f(*obsidian_helm)
            self.draw_trapezoid_plate(0.15, 0.11, 0.14, 0.020)
            gl.glColor3f(*crimson)
            self.draw_trapezoid_plate(0.14, 0.12, 0.045, 0.024)
            gl.glColor3f(*old_gold)
            self.draw_trapezoid_plate(0.158, 0.150, 0.020, 0.025)
            gl.glPopMatrix()

        # 4. Kuwagata: Lâminas Planas Chanfradas e Pontiagudas em Formato de 'V' Agressivo (#C59B27)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.065, 0.112)
        gl.glRotatef(-10.0, 1.0, 0.0, 0.0)
        # Brasão central hexagonal (Maedate)
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glRotatef(90.0, 1.0, 0.0, 0.0)
        self.draw_chiseled_prism(0.036, 0.036, 0.028, 0.028, 0.020, sides=6, cap_top=True)
        gl.glPopMatrix()

        # Duas Lâminas em 'V' Agressivo com Seção em Diamante (reflete luz em facetas nítidas)
        gl.glColor3f(*old_gold)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.022, 0.0, 0.005)
            gl.glRotatef(s * -33.0, 0.0, 0.0, 1.0)
            # Tramo inferior da lâmina do chifre
            self.draw_chiseled_prism(0.018, 0.008, 0.026, 0.010, 0.11, sides=6)
            # Tramo superior pontiagudo dobrando agressivamente para cima
            gl.glTranslatef(0.0, 0.11, 0.0)
            gl.glRotatef(s * 15.0, 0.0, 0.0, 1.0)
            self.draw_chiseled_prism(0.026, 0.010, 0.002, 0.002, 0.13, sides=6, cap_top=True)
            gl.glPopMatrix()
        gl.glPopMatrix()

        # 5. Fenda Ocular Afiada sob a Viseira
        gl.glDisable(gl.GL_LIGHTING)
        eye_col = visor_glow if visor_glow is not None else (0.95, 0.28, 0.16)
        gl.glColor3f(*eye_col)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.034, 0.006, 0.092)
            gl.glRotatef(s * -12.0, 0.0, 0.0, 1.0)
            self.draw_trapezoid_plate(0.028, 0.022, 0.012, 0.010)
            gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)

    def _draw_samurai_leg(
        self,
        hip_x: float,
        hip_swing_deg: float,
        knee_bend_deg: float,
        ib: float = 0.0,
    ) -> None:
        """
        Desenha a perna alongada (+25% proporção heroica) sem esferas:
        - Hakama: Prisma de 6 lados (hexagonal) que começa junto na cintura, abre levemente até o joelho
          com vincos retos (simulando pregas de tecido pesado) e fecha de forma justa no joelho.
        - Suneate: Caneleira metálica octogonal (8 lados) justa e esguia com reflexos facetados.
        """
        hakama_col = (0.10 + ib, 0.11 + ib, 0.14 + ib)
        suneate_col = (0.18 + ib, 0.20 + ib, 0.25 + ib)
        old_gold = (0.773, 0.608, 0.153)
        crimson = (0.545, 0.118, 0.118)

        gl.glPushMatrix()
        gl.glTranslatef(hip_x, 0.98, 0.0)
        gl.glRotatef(hip_swing_deg, 1.0, 0.0, 0.0)

        # 1. Calça Hakama (Prisma Hexagonal de 6 lados com vincos retos:
        # começa estreito na cintura, abre até acima do joelho e fecha abruptamente no joelho!)
        self._set_material_heavy_cloth()
        gl.glColor3f(*hakama_col)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.40, 0.0)
        # Parte principal do Hakama abrindo da cintura (top=0.095) até a coxa baixa (bot=0.128)
        self.draw_chiseled_prism(0.128, 0.136, 0.095, 0.105, 0.40, sides=6)
        # Fechamento chanfrado abrupto do tecido do Hakama logo acima da caneleira (-0.40 a -0.47)
        gl.glTranslatef(0.0, -0.07, 0.0)
        self.draw_chiseled_prism(0.062, 0.066, 0.128, 0.136, 0.07, sides=6)
        gl.glPopMatrix()

        # 2. Joelheira Facetada (Kikko) + Dobra do Joelho (em Y = -0.47)
        gl.glTranslatef(0.0, -0.47, 0.0)
        self._set_material_forged_metal()
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.02, 0.058)
        gl.glRotatef(10.0, 1.0, 0.0, 0.0)
        self.draw_trapezoid_plate(0.055, 0.075, 0.075, 0.022)
        gl.glPopMatrix()

        gl.glRotatef(knee_bend_deg, 1.0, 0.0, 0.0)

        # 3. Caneleira Metálica Justa Octogonal (Suneate de 8 lados esguia: 0.44m de comprimento)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.44, 0.0)
        gl.glColor3f(*suneate_col)
        self.draw_chiseled_prism(0.042, 0.046, 0.060, 0.065, 0.44, sides=8)
        # Crista frontal chanfrada em Ouro Velho ao longo da caneleira
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.04, 0.052)
        self.draw_trapezoid_plate(0.022, 0.028, 0.36, 0.016)
        gl.glPopMatrix()
        # 2 Amarrações octogonais carmesim
        gl.glColor3f(*crimson)
        for sy, sr in ((0.12, 0.050), (0.30, 0.060)):
            gl.glPushMatrix()
            gl.glTranslatef(0.0, sy, 0.0)
            self.draw_chiseled_prism(sr, sr * 1.06, sr, sr * 1.06, 0.024, sides=8)
            gl.glPopMatrix()
        gl.glPopMatrix()

        # 4. Calçado Samurai Chanfrado de 6 lados (Tabi / Waraji)
        gl.glTranslatef(0.0, -0.50, 0.035)
        gl.glColor3f(0.12, 0.13, 0.16)
        gl.glPushMatrix()
        gl.glRotatef(90.0, 1.0, 0.0, 0.0)
        self.draw_chiseled_prism(0.058, 0.042, 0.042, 0.032, 0.19, sides=6, cap_top=True, cap_bot=True)
        gl.glPopMatrix()

        gl.glPopMatrix()

    def _draw_torn_haori_cloth(self, leg_swing: float) -> None:
        """
        Desenha a Capa / Haori Rasgado nas Costas usando uma malha de planos triangulados
        (Low-Poly Triangulated Cloth com Flat Shading por triângulo) que cai dos ombros
        em linhas retas e termina em pontas triangulares irregulares de batalha (#8B1E1E).
        """
        self._set_material_heavy_cloth()
        crimson = (0.545, 0.118, 0.118)       # #8B1E1E
        crimson_shade = (0.43, 0.09, 0.095)
        old_gold = (0.773, 0.608, 0.153)      # #C59B27

        # Gola chanfrada de 6 lados nos ombros/nuca
        gl.glColor3f(*crimson)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.64, -0.02)
        self.draw_chiseled_prism(0.18, 0.13, 0.15, 0.11, 0.08, sides=6)
        gl.glPopMatrix()

        # Malha de planos triangulados caindo em linhas retas (5 colunas x 3 fileiras + pontas irregulares)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.64, -0.145)
        swing_lean = 10.0 + abs(leg_swing) * 0.42
        gl.glRotatef(swing_lean, 1.0, 0.0, 0.0)

        # Coordenadas X das 5 colunas (alternando cristas e vales em Z para criar vincos retos de tecido dobrado!)
        xs_top = [-0.19, -0.095, 0.0, 0.095, 0.19]
        xs_mid = [-0.23, -0.115, 0.0, 0.115, 0.23]
        xs_bot = [-0.26, -0.13, 0.0, 0.13, 0.26]
        z_pleat = [-0.01, -0.045, 0.0, -0.045, -0.01]

        y0, y1, y2 = 0.0, -0.45, -0.88

        gl.glBegin(gl.GL_TRIANGLES)
        for col in range(4):
            # Fileira Superior (de y0 até y1) dividida em 2 triângulos planos nítidos
            A = (xs_top[col], y0, z_pleat[col] * 0.4)
            B = (xs_top[col + 1], y0, z_pleat[col + 1] * 0.4)
            C = (xs_mid[col + 1], y1, z_pleat[col + 1])
            D = (xs_mid[col], y1, z_pleat[col])

            gl.glColor3f(*(crimson if col % 2 == 0 else crimson_shade))
            self._emit_flat_tri(A, D, C)
            gl.glColor3f(*(crimson_shade if col % 2 == 0 else crimson))
            self._emit_flat_tri(A, C, B)

            # Fileira Inferior (de y1 até y2) dividida em 2 triângulos planos nítidos
            E = (xs_bot[col + 1], y2, z_pleat[col + 1] * 1.35)
            F = (xs_bot[col], y2, z_pleat[col] * 1.35)

            gl.glColor3f(*(crimson if col % 2 == 0 else crimson_shade))
            self._emit_flat_tri(D, F, E)
            gl.glColor3f(*(crimson_shade if col % 2 == 0 else crimson))
            self._emit_flat_tri(D, E, C)

            # Pontas Triangulares Irregulares na Barra (Aspecto Rasgado de Batalha!)
            jag_lengths = (-0.24, -0.14, -0.29, -0.18)
            jag_x_shift = (-0.02, 0.015, -0.01, 0.025)
            tip_pt = (
                (xs_bot[col] + xs_bot[col + 1]) * 0.5 + jag_x_shift[col],
                y2 + jag_lengths[col],
                -0.035,
            )
            gl.glColor3f(*crimson)
            self._emit_flat_tri(F, tip_pt, E)
        gl.glEnd()

        # Filete geométrico dourado acima das pontas rasgadas
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, y2 + 0.04, -0.025)
        self.draw_trapezoid_plate(0.50, 0.48, 0.022, 0.035)
        gl.glPopMatrix()

        gl.glPopMatrix()

    def _draw_chiseled_saya(self, length: float = 1.02) -> None:
        """Desenha a bainha (Saya) chanfrada de 6 lados na cintura com ponteira dourada."""
        self._set_material_forged_metal()
        old_gold = (0.773, 0.608, 0.153)
        crimson = (0.545, 0.118, 0.118)

        gl.glPushMatrix()
        gl.glRotatef(90.0, 1.0, 0.0, 0.0)
        gl.glTranslatef(0.0, -length * 0.5, 0.0)
        # Bocal dourado (Koiguchi)
        gl.glColor3f(*old_gold)
        self.draw_chiseled_prism(0.024, 0.034, 0.024, 0.034, 0.06, sides=6, cap_bot=True)
        # Tramo laqueado carmesim e preto (com leve angulação de 6 graus no meio)
        gl.glTranslatef(0.0, 0.06, 0.0)
        gl.glColor3f(*crimson)
        self.draw_chiseled_prism(0.021, 0.030, 0.020, 0.028, length * 0.45, sides=6)
        gl.glTranslatef(0.0, length * 0.45, 0.0)
        gl.glRotatef(-6.0, 1.0, 0.0, 0.0)
        gl.glColor3f(0.09, 0.09, 0.11)
        self.draw_chiseled_prism(0.020, 0.028, 0.017, 0.024, length * 0.43, sides=6)
        # Ponteira dourada (Kojiri)
        gl.glTranslatef(0.0, length * 0.43, 0.0)
        gl.glColor3f(*old_gold)
        self.draw_chiseled_prism(0.018, 0.025, 0.008, 0.012, 0.06, sides=6, cap_top=True)
        gl.glPopMatrix()

    def _draw_katana(self, blade_len: float = 1.44, handle_len: float = 0.34, is_wakizashi: bool = False) -> None:
        """
        Desenha a Katana em Tamanho Realista (-25% de comprimento = 1.44m) e estética Hard-Surface:
        - Cabo (Tsuka) hexagonal chanfrado de 6 lados com anéis carmesim (#8B1E1E)
        - Guarda (Tsuba) octogonal de 8 lados em ouro velho (#C59B27)
        - Lâmina com seção transversal em diamante (chanfrada em 4 faces planas nítidas)
          para refletir a luz em duas faces nítidas de cada lado (dorso escuro + bisel prateado #E2E8F0)
        """
        old_gold = (0.773, 0.608, 0.153)      # #C59B27
        crimson = (0.545, 0.118, 0.118)       # #8B1E1E
        dark_spine = (0.14, 0.16, 0.20)       # Face do dorso (Shinogi-ji)
        bright_bevel = (0.886, 0.910, 0.941)  # Face chanfrada do fio (#E2E8F0)

        # 1. Cabo (Tsuka) Hexagonal de 6 Lados
        self._set_material_heavy_cloth()
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -handle_len, 0.0)
        gl.glColor3f(0.10, 0.11, 0.13)
        self.draw_chiseled_prism(0.017, 0.024, 0.018, 0.025, handle_len, sides=6, cap_bot=True)
        gl.glColor3f(*crimson)
        steps = 2 if is_wakizashi else 4
        for i in range(steps):
            ty = handle_len * (0.15 + 0.65 * (i / max(1, steps - 1)))
            gl.glPushMatrix()
            gl.glTranslatef(0.0, ty, 0.0)
            self.draw_chiseled_prism(0.020, 0.028, 0.020, 0.028, 0.025, sides=6)
            gl.glPopMatrix()
        self._set_material_forged_metal()
        gl.glColor3f(*old_gold)
        self.draw_chiseled_prism(0.021, 0.029, 0.021, 0.029, 0.032, sides=6, cap_bot=True)
        gl.glPopMatrix()

        # 2. Guarda Octogonal (Tsuba de 8 lados chanfrados) em Ouro Velho (#C59B27)
        self._set_material_forged_metal()
        gl.glColor3f(*old_gold)
        r_tsuba = 0.068 if not is_wakizashi else 0.052
        self.draw_chiseled_prism(r_tsuba, r_tsuba, r_tsuba * 0.92, r_tsuba * 0.92, 0.018, sides=8, cap_bot=True, cap_top=True)
        # Colarinho Habaki hexagonal
        self.draw_chiseled_prism(0.016, 0.026, 0.015, 0.024, 0.042, sides=6)

        # 3. Lâmina Chanfrada com Seção em Diamante (3 tramos angulados + Ponta Kissaki)
        # Cada tramo tem uma crista central (Shinogi) em X = +-w, dorso traseiro em Z = -z_back,
        # e fio cortante agudo em Z = +z_edge, formando 2 faces planas nítidas de cada lado!
        seg_len = (blade_len * 0.88) / 3.0
        tip_len = blade_len * 0.12
        curve_angles = (-1.8, -2.6, -3.2)

        gl.glPushMatrix()
        for seg_idx, c_ang in enumerate(curve_angles):
            gl.glRotatef(c_ang, 1.0, 0.0, 0.0)
            t0 = 1.0 - seg_idx * 0.08
            t1 = 1.0 - (seg_idx + 1) * 0.08

            w0, w1 = 0.011 * t0, 0.011 * t1
            zb0, zb1 = -0.022 * t0, -0.022 * t1
            zm0, zm1 = -0.002 * t0, -0.002 * t1
            ze0, ze1 = 0.024 * t0, 0.024 * t1

            gl.glBegin(gl.GL_QUADS)
            # Face 1 (Traseira/Dorso Direita e Esquerda) - Escura Metálica
            gl.glColor3f(*dark_spine)
            self._emit_flat_quad((0.0, 0.0, zb0), (-w0, 0.0, zm0), (-w1, seg_len, zm1), (0.0, seg_len, zb1))
            self._emit_flat_quad((w0, 0.0, zm0), (0.0, 0.0, zb0), (0.0, seg_len, zb1), (w1, seg_len, zm1))

            # Face 2 (Bisel Frontal do Fio Direita e Esquerda) - Prateado Brilhante (#E2E8F0)
            gl.glColor3f(*bright_bevel)
            self._emit_flat_quad((-w0, 0.0, zm0), (0.0, 0.0, ze0), (0.0, seg_len, ze1), (-w1, seg_len, zm1))
            self._emit_flat_quad((0.0, 0.0, ze0), (w0, 0.0, zm0), (w1, seg_len, zm1), (0.0, seg_len, ze1))
            gl.glEnd()

            gl.glTranslatef(0.0, seg_len, 0.0)
            if seg_idx == 2:
                # Ponta Chanfrada em Diamante (Kissaki)
                tip_pt = (0.0, tip_len, -0.006)
                gl.glBegin(gl.GL_TRIANGLES)
                gl.glColor3f(*dark_spine)
                self._emit_flat_tri((0.0, 0.0, zb1), (-w1, 0.0, zm1), tip_pt)
                self._emit_flat_tri((w1, 0.0, zm1), (0.0, 0.0, zb1), tip_pt)
                gl.glColor3f(*bright_bevel)
                self._emit_flat_tri((-w1, 0.0, zm1), (0.0, 0.0, ze1), tip_pt)
                self._emit_flat_tri((0.0, 0.0, ze1), (w1, 0.0, zm1), tip_pt)
                gl.glEnd()
        gl.glPopMatrix()

    def _draw_knight_pauldron(self, side_sign: float, scale: float = 1.0) -> None:
        """Desenha uma Ombreira (Pauldron) medieval angular em placas sobrepostas (nada de bola!)."""
        gl.glPushMatrix()
        gl.glScalef(scale, scale, scale)
        gl.glRotatef(side_sign * -18.0, 0.0, 0.0, 1.0)
        # Placa superior angulada com rebordo
        self.draw_tapered_torso(0.24, 0.26, 0.16, 0.20, 0.14)
        # Placa lateral de descida
        gl.glPushMatrix()
        gl.glTranslatef(side_sign * 0.04, -0.08, 0.0)
        gl.glRotatef(side_sign * -12.0, 0.0, 0.0, 1.0)
        self.draw_box(0.22, 0.10, 0.24)
        gl.glPopMatrix()
        # Crista de aço vertical na ombreira
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.14, 0.0)
        self.draw_box(0.04, 0.06, 0.22)
        gl.glPopMatrix()
        gl.glPopMatrix()

    def _draw_knight_helmet(self, visor_glow: tuple[float, float, float] | None = None) -> None:
        """
        Desenha um Elmo de Cavaleiro Facetado (estilo Dark Souls Elite Knight / Lothric):
        Crânio octogonal chanfrado, máscara/viseira pontuda em V (Hounskull), queixeira, crista e pluma.
        """
        # Crânio octogonal de aço
        self.draw_octa(0.23, 0.25, 0.25)

        # Crista central metálica no topo do elmo
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.14, -0.01)
        self.draw_box(0.04, 0.07, 0.24)
        gl.glPopMatrix()

        # Viseira Pontuda em Cunha (V-Shaped Visor Bevor) na frente (+Z)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.02, 0.11)
        gl.glRotatef(85.0, 1.0, 0.0, 0.0)
        self.draw_pyramid(0.22, 0.12, 0.18)
        gl.glPopMatrix()

        # Fenda escura do visor (Eye Slit)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(0.05, 0.05, 0.07)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.04, 0.14)
        self.draw_box(0.19, 0.032, 0.06)
        gl.glPopMatrix()

        if visor_glow is not None:
            gl.glColor3f(*visor_glow)
            for s in (-1.0, 1.0):
                gl.glPushMatrix()
                gl.glTranslatef(s * 0.05, 0.04, 0.165)
                self.draw_box(0.03, 0.022, 0.02)
                gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)

    def _draw_articulated_leg(
        self,
        hip_x: float,
        hip_swing_deg: float,
        knee_bend_deg: float,
        armor_col: tuple[float, float, float],
        joint_col: tuple[float, float, float],
        boot_col: tuple[float, float, float],
    ) -> None:
        """
        Desenha uma perna completa com Coxa afunilada, Joelheira em losango/espinho,
        Canela/Greva chanfrada e Bota de Aço (Sabaton) pontiaguda.
        """
        gl.glPushMatrix()
        gl.glTranslatef(hip_x, 0.78, 0.0)
        gl.glRotatef(hip_swing_deg, 1.0, 0.0, 0.0)

        # 1. Coxa (Thigh Plate afunilada para o joelho)
        gl.glColor3f(*armor_col)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.36, 0.0)
        self.draw_tapered_torso(0.14, 0.15, 0.19, 0.19, 0.36)
        gl.glPopMatrix()

        # 2. Articulação do Joelho + Joelheira Angular (Poleyn)
        gl.glTranslatef(0.0, -0.36, 0.0)
        gl.glColor3f(*joint_col)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.0, 0.08)
        gl.glRotatef(45.0, 0.0, 0.0, 1.0)
        self.draw_box(0.09, 0.09, 0.05)
        gl.glPopMatrix()

        # Dobra do Joelho
        gl.glRotatef(knee_bend_deg, 1.0, 0.0, 0.0)

        # 3. Canela / Greva (Shin Greave)
        gl.glColor3f(*armor_col)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.34, 0.0)
        self.draw_tapered_torso(0.11, 0.12, 0.14, 0.15, 0.34)
        # Crista frontal da caneleira
        gl.glTranslatef(0.0, 0.17, 0.07)
        self.draw_box(0.03, 0.32, 0.04)
        gl.glPopMatrix()

        # 4. Bota de Aço (Sabaton com biqueira angulada para frente +Z)
        gl.glTranslatef(0.0, -0.38, 0.04)
        gl.glColor3f(*boot_col)
        self.draw_box(0.13, 0.09, 0.24)
        # Biqueira pontuda do pé
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.02, 0.12)
        gl.glRotatef(90.0, 1.0, 0.0, 0.0)
        self.draw_pyramid(0.12, 0.08, 0.08)
        gl.glPopMatrix()

        gl.glPopMatrix()

    def begin_frame_3d(self, dt: float, camera, world, boss: BossMalakor) -> None:
        self.time_accum += dt
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(camera.fovy, self.width / max(1, self.height), 0.25, 110.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        glu.gluLookAt(
            camera.position.x,
            camera.position.y,
            camera.position.z,
            camera.target.x,
            camera.target.y,
            camera.target.z,
            camera.up.x,
            camera.up.y,
            camera.up.z,
        )

        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_FOG)

        # Posiciona luz direcional do luar
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (0.35, 1.0, 0.25, 0.0))

        # Posiciona luz quente: na Fase 2 do Boss ilumina ao redor da espada flamejante, senão na Fogueira!
        flicker = 0.92 + 0.14 * math.sin(self.time_accum * 17.0)
        if boss.alive and boss.phase == 2 and boss.state != BossState.DORMANT:
            gl.glLightfv(gl.GL_LIGHT1, gl.GL_POSITION, (boss.pos.x, boss.pos.y + 2.2, boss.pos.z, 1.0))
            gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, (1.0 * flicker, 0.42 * flicker, 0.12, 1.0))
        else:
            bf = world.bonfire.pos
            gl.glLightfv(gl.GL_LIGHT1, gl.GL_POSITION, (bf.x, bf.y + 1.4, bf.z, 1.0))
            gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, (1.0 * flicker, 0.58 * flicker, 0.18, 1.0))

    def project_to_screen(self, pos: Vec3) -> tuple[float, float, bool]:
        """Converte uma coordenada 3D do mundo para pixels 2D da tela (origem no canto superior esquerdo)."""
        try:
            model = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
            proj = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
            view = gl.glGetIntegerv(gl.GL_VIEWPORT)
            sx, sy, sz = glu.gluProject(pos.x, pos.y, pos.z, model, proj, view)
            if 0.0 <= sz <= 1.0:
                return float(sx), float(self.height - sy), True
        except Exception:
            pass
        return 0.0, 0.0, False

    def render_world(self, world) -> None:
        gl.glCallList(self.dl_floor)
        gl.glCallList(self.dl_walls)

        # Pilares Góticos
        for p in world.pillars:
            gl.glPushMatrix()
            gl.glTranslatef(p.pos.x, p.pos.y, p.pos.z)
            gl.glColor3f(0.20, 0.21, 0.24)
            gl.glPushMatrix()
            gl.glTranslatef(0.0, 0.35, 0.0)
            self.draw_box(p.radius * 2.3, 0.7, p.radius * 2.3)
            gl.glPopMatrix()
            gl.glColor3f(0.25, 0.26, 0.30)
            self.draw_cylinder(p.radius, p.height)
            if not p.broken:
                gl.glColor3f(0.22, 0.23, 0.27)
                gl.glPushMatrix()
                gl.glTranslatef(0.0, p.height, 0.0)
                self.draw_box(p.radius * 2.4, 0.6, p.radius * 2.4)
                gl.glPopMatrix()
            gl.glPopMatrix()

        # Tochas nos pilares (chama facetada em pirâmide)
        for torch in world.torches:
            gl.glPushMatrix()
            gl.glTranslatef(torch.pos.x, torch.pos.y, torch.pos.z)
            gl.glColor3f(0.25, 0.18, 0.12)
            self.draw_cylinder(0.08, 0.55)
            gl.glDisable(gl.GL_LIGHTING)
            pulse = 0.26 + 0.06 * math.sin(self.time_accum * 14.0 + torch.pos.x)
            gl.glColor3f(1.0, 0.62, 0.15)
            gl.glTranslatef(0.0, 0.55, 0.0)
            self.draw_pyramid(0.22, pulse, 0.22)
            gl.glEnable(gl.GL_LIGHTING)
            gl.glPopMatrix()

        # Fogueira (Bonfire) com Espada Espiral Cravada!
        bf = world.bonfire.pos
        gl.glPushMatrix()
        gl.glTranslatef(bf.x, bf.y, bf.z)
        gl.glColor3f(0.22, 0.20, 0.19)
        self.draw_cylinder(0.75, 0.22)
        gl.glColor3f(0.16, 0.16, 0.18)
        for i in range(8):
            ang = i * (2.0 * math.pi / 8.0)
            gl.glPushMatrix()
            gl.glTranslatef(math.cos(ang) * 0.68, 0.15, math.sin(ang) * 0.68)
            gl.glRotatef(ang * 57.3, 0.0, 1.0, 0.0)
            self.draw_box(0.28, 0.25, 0.28)
            gl.glPopMatrix()

        # Espada Cravada na Fogueira
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.2, 0.0)
        gl.glRotatef(14.0, 0.0, 0.0, 1.0)
        gl.glColor3f(0.52, 0.48, 0.44)
        self.draw_sword_blade(0.12, 1.35, 0.05)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 1.15, 0.0)
        gl.glColor3f(0.62, 0.46, 0.22)
        self.draw_box(0.44, 0.07, 0.09)
        gl.glPopMatrix()
        gl.glPopMatrix()

        # Chamas poligonais dançantes da fogueira
        gl.glDisable(gl.GL_LIGHTING)
        flame_h = 0.65 + 0.16 * math.sin(self.time_accum * 12.0)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.22, 0.0)
        gl.glRotatef(self.time_accum * 45.0, 0.0, 1.0, 0.0)
        gl.glColor4f(1.0, 0.48, 0.10, 0.9)
        self.draw_pyramid(0.45, flame_h, 0.45)
        gl.glRotatef(45.0, 0.0, 1.0, 0.0)
        gl.glColor4f(1.0, 0.85, 0.25, 0.9)
        self.draw_pyramid(0.28, flame_h * 0.85, 0.28)
        gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()

        # Poça de Almas (Bloodstain) em formato de Cristal de Alma Octogonal!
        if world.bloodstain.active:
            bs = world.bloodstain.pos
            gl.glDisable(gl.GL_LIGHTING)
            gl.glPushMatrix()
            gl.glTranslatef(bs.x, 0.45 + 0.1 * math.sin(self.time_accum * 4.0), bs.z)
            gl.glRotatef(self.time_accum * 90.0, 0.0, 1.0, 0.0)
            gl.glColor3f(0.30, 0.95, 0.72)
            self.draw_pyramid(0.28, 0.45, 0.28)
            gl.glRotatef(180.0, 1.0, 0.0, 0.0)
            self.draw_pyramid(0.28, 0.30, 0.28)
            gl.glEnable(gl.GL_LIGHTING)
            gl.glPopMatrix()

    def render_player(self, player: Player) -> None:
        """
        Renderiza o Jogador na estética CHISELED LOW-POLY / STYLIZED HARD-SURFACE (estilo Ashen / Absolver):
        - Flat Shading (GL_FLAT + normais por face) sobre prismas chanfrados de 6 a 8 lados (sem esferas lisas,
          sem cilindros de 24 lados e sem cubos retos de 90 graus).
        - Proporções Heroicas (+25% mais alto e esguio, pernas e braços alongados, cabeça 20% menor).
        - Torso em 'V' (Trapézio Invertido reto e firme da cintura estreita ao peito largo).
        - Kabuto de 8 lados com quinas vivas, Shikoro trapezoidal em 3 faces planas e Kuwagata em lâminas 'V' chanfradas.
        - Sode em 3 placas sobrepostas em degraus dobradas em ângulo obtuso (135°).
        - Hakama em prismas de 6 lados com vincos retos e Suneate octogonais justos.
        - Capa / Haori em malha de planos triangulados (low-poly cloth) com pontas rasgadas irregulares.
        - Katana em tamanho realista (-25% = 1.44m) com seção transversal em diamante (4 faces chanfradas).
        """
        gl.glShadeModel(gl.GL_FLAT)
        gl.glPushMatrix()
        gl.glTranslatef(player.pos.x, player.pos.y, player.pos.z)
        self._draw_ground_shadow(0.58)

        gl.glRotatef(math.degrees(player.facing_yaw), 0.0, 1.0, 0.0)

        if not player.alive:
            fall_ang = min(90.0, player.state_timer * 140.0)
            gl.glRotatef(fall_ang, 1.0, 0.0, 0.0)

        if player.state == PlayerState.ROLL:
            t_roll = clamp(player.state_timer / max(0.001, player.state_duration), 0.0, 1.0)
            gl.glTranslatef(0.0, 0.96, 0.0)
            gl.glRotatef(t_roll * 360.0, 1.0, 0.0, 0.0)
            gl.glTranslatef(0.0, -0.96, 0.0)

        # Paleta de cores exata do Samurai Dark Fantasy (+ brilho de I-Frames)
        ib = 0.20 if player.is_invulnerable() else 0.0
        do_dark = (0.102 + ib, 0.114 + ib, 0.141 + ib)       # #1A1D24 (Peitoral Do escuro)
        lead_grey = (0.188 + ib, 0.208 + ib, 0.251 + ib)     # Placas cinza-chumbo
        obsidian = (0.133 + ib, 0.141 + ib, 0.157 + ib)      # #222428 (Cinza-obsidiana)
        crimson = (0.545, 0.118, 0.118)                      # #8B1E1E (Vermelho-carmesim queimado)
        old_gold = (0.773, 0.608, 0.153)                     # #C59B27 (Ouro velho)

        # Ciclo de caminhada e corrida
        leg_swing = 0.0
        left_knee = 5.0
        right_knee = 5.0
        torso_lean = 0.0
        if player.state in (PlayerState.MOVE, PlayerState.SPRINT):
            amp = 38.0 if player.state == PlayerState.SPRINT else 25.0
            phase = player.walk_cycle * 2.5
            leg_swing = math.sin(phase) * amp
            left_knee = max(5.0, -math.cos(phase) * 32.0 + 14.0)
            right_knee = max(5.0, math.cos(phase) * 32.0 + 14.0)
            torso_lean = 12.0 if player.state == PlayerState.SPRINT else 5.5

        # 1. Pernas Alongadas (+25% altura: quadril em Y=0.98) com Hakama Hexagonal e Suneate Octogonal
        self._draw_samurai_leg(0.115, leg_swing, left_knee, ib)
        self._draw_samurai_leg(-0.115, -leg_swing, right_knee, ib)

        # 2. Cintura Estreita (Faixa Obi Octogonal + 4 Placas Trapezoidais de Kusazuri + Bainha Saya Chanfrada)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.98, 0.0)
        if player.state == PlayerState.STAGGER:
            gl.glRotatef(-22.0, 1.0, 0.0, 0.0)
        else:
            gl.glRotatef(torso_lean, 1.0, 0.0, 0.0)

        # Faixa da cintura (Obi) como prisma octogonal justo em Vermelho-Carmesim (#8B1E1E)
        self._set_material_heavy_cloth()
        gl.glColor3f(*crimson)
        self.draw_chiseled_prism(0.155, 0.112, 0.142, 0.105, 0.09, sides=8, cap_bot=True)
        # Nó chanfrado do Obi nas costas
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.01, -0.118)
        self.draw_trapezoid_plate(0.13, 0.11, 0.08, 0.045)
        gl.glPopMatrix()
        # Fivela/fecho chanfrado em Ouro Velho na frente do Obi
        self._set_material_forged_metal()
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.025, 0.112)
        self.draw_trapezoid_plate(0.09, 0.07, 0.035, 0.018)
        gl.glPopMatrix()

        # Kusazuri: 4 Placas Trapezoidais Chanfradas ao redor da cintura
        # Placa Frontal e Traseira
        for z_sign, z_off in ((1.0, 0.112), (-1.0, -0.112)):
            gl.glPushMatrix()
            gl.glTranslatef(0.0, -0.19, z_off)
            gl.glRotatef(z_sign * -15.0, 1.0, 0.0, 0.0)
            gl.glColor3f(*obsidian)
            self.draw_trapezoid_plate(0.28, 0.22, 0.20, 0.024)
            gl.glColor3f(*lead_grey)
            self.draw_trapezoid_plate(0.26, 0.24, 0.06, 0.028)
            gl.glColor3f(*old_gold)
            self.draw_trapezoid_plate(0.29, 0.28, 0.022, 0.028)
            gl.glPopMatrix()

        # Placas Laterais Esquerda e Direita do Kusazuri
        for x_sign in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(x_sign * 0.165, -0.19, 0.0)
            gl.glRotatef(x_sign * 90.0, 0.0, 1.0, 0.0)
            gl.glRotatef(-16.0, 1.0, 0.0, 0.0)
            gl.glColor3f(*obsidian)
            self.draw_trapezoid_plate(0.21, 0.16, 0.20, 0.024)
            gl.glColor3f(*lead_grey)
            self.draw_trapezoid_plate(0.19, 0.17, 0.06, 0.028)
            gl.glColor3f(*old_gold)
            self.draw_trapezoid_plate(0.22, 0.21, 0.022, 0.028)
            gl.glPopMatrix()

        # Bainha Chanfrada (Saya de 6 lados) presa no lado esquerdo da cintura
        gl.glPushMatrix()
        gl.glTranslatef(0.18, 0.02, -0.03)
        gl.glRotatef(-32.0, 1.0, 0.0, 0.0)
        gl.glRotatef(8.0, 0.0, 0.0, 1.0)
        self._draw_chiseled_saya(length=1.02)
        gl.glPopMatrix()

        # 3. Torso em 'V' (Trapézio Invertido Reto e Firme: da cintura estreita ao peito largo!)
        gl.glTranslatef(0.0, 0.08, 0.0)
        self._set_material_forged_metal()
        # Seção abdominal inferior firme (sem anéis redondos!)
        gl.glColor3f(*do_dark)
        self.draw_chiseled_prism(0.140, 0.102, 0.178, 0.122, 0.24, sides=8)

        # Peitoral Superior (Do) em Trapézio Invertido Forte (abre de 0.178 até 0.258 nos ombros!)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.24, 0.0)
        gl.glColor3f(*do_dark)
        self.draw_chiseled_prism(0.178, 0.122, 0.258, 0.152, 0.42, sides=8, cap_top=True)

        # Placas peitorais frontais e traseiras chanfradas em Cinza-Chumbo (facetas planas de metal batido)
        for z_s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(0.0, 0.06, z_s * 0.132)
            gl.glRotatef(z_s * 11.0, 1.0, 0.0, 0.0)
            gl.glColor3f(*lead_grey)
            self.draw_trapezoid_plate(0.24, 0.36, 0.30, 0.024)
            # Borda peitoral superior em Ouro Velho (#C59B27)
            gl.glTranslatef(0.0, 0.28, 0.0)
            gl.glColor3f(*old_gold)
            self.draw_trapezoid_plate(0.35, 0.37, 0.028, 0.028)
            gl.glPopMatrix()
        gl.glPopMatrix()

        # Pescoço Blindado Hexagonal Esguio
        gl.glColor3f(*obsidian)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.66, 0.0)
        self.draw_chiseled_prism(0.072, 0.072, 0.062, 0.062, 0.10, sides=6)
        gl.glPopMatrix()

        # 4. Costas: Capa / Haori Rasgado em Malha de Planos Triangulados (Low-Poly Cloth)
        self._draw_torn_haori_cloth(leg_swing)

        # 5. Cabeça Menor (-20% em relação aos ombros) para Proporção Heroica e Ameaçadora
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.81, 0.01)
        self._draw_samurai_helmet(
            visor_glow=(0.45, 0.88, 1.0) if player.is_invulnerable() else None
        )
        gl.glPopMatrix()

        # 6. Braço Esquerdo Alongado (Prismas Chanfrados de 6/8 lados + Sode em 135° + Wakizashi)
        gl.glPushMatrix()
        gl.glTranslatef(0.265, 0.62, 0.0)
        elbow_l = -24.0
        if player.state == PlayerState.BLOCK:
            gl.glRotatef(-68.0, 1.0, 0.0, 0.0)
            gl.glRotatef(-36.0, 0.0, 1.0, 0.0)
            gl.glRotatef(-25.0, 0.0, 0.0, 1.0)
            elbow_l = -48.0
        elif player.state == PlayerState.PARRY:
            t_p = clamp(player.state_timer / max(0.001, player.state_duration), 0.0, 1.0)
            sweep = math.sin(t_p * math.pi) * 85.0
            gl.glRotatef(-72.0, 1.0, 0.0, 0.0)
            gl.glRotatef(-30.0 + sweep, 0.0, 1.0, 0.0)
            elbow_l = -32.0
        elif player.state == PlayerState.ESTUS:
            gl.glRotatef(-85.0, 1.0, 0.0, 0.0)
            gl.glRotatef(-25.0, 0.0, 0.0, 1.0)
            elbow_l = -65.0
        else:
            gl.glRotatef(-leg_swing * 0.55, 1.0, 0.0, 0.0)

        # Ombreira Sode Esquerda (3 placas em degraus dobradas em ângulo obtuso de 135°)
        self._draw_samurai_sode(1.0)

        # Braço Superior Esguio (Prisma Hexagonal de 6 lados, sem esferas!)
        self._set_material_heavy_cloth()
        gl.glColor3f(*do_dark)
        gl.glTranslatef(0.02, -0.31, 0.0)
        self.draw_chiseled_prism(0.048, 0.048, 0.062, 0.062, 0.31, sides=6, cap_top=True)

        # Cotovelo + Antebraço Blindado Octogonal (Kote de 8 lados: 0.30m de comprimento)
        self._set_material_forged_metal()
        gl.glRotatef(elbow_l, 1.0, 0.0, 0.0)
        gl.glColor3f(*obsidian)
        gl.glTranslatef(0.0, -0.30, 0.0)
        self.draw_chiseled_prism(0.038, 0.042, 0.052, 0.055, 0.30, sides=8)
        # Placa externa chanfrada em Ouro Velho no Kote
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glTranslatef(0.044, 0.05, 0.0)
        gl.glRotatef(90.0, 0.0, 1.0, 0.0)
        self.draw_trapezoid_plate(0.045, 0.055, 0.21, 0.015)
        gl.glPopMatrix()

        # Manopla Hexagonal Chanfrada (Tekko)
        gl.glColor3f(*obsidian)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.07, 0.0)
        self.draw_chiseled_prism(0.035, 0.042, 0.042, 0.046, 0.07, sides=6, cap_bot=True)
        gl.glPopMatrix()

        # Mão Esquerda: Frasco de Cura Octogonal ou Wakizashi em Guarda Reversa / Deflexão Cruzada
        if player.state == PlayerState.ESTUS:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glColor3f(1.0, 0.78, 0.18)
            gl.glTranslatef(0.0, -0.12, 0.06)
            self.draw_chiseled_prism(0.045, 0.045, 0.065, 0.065, 0.16, sides=8, cap_bot=True, cap_top=True)
            gl.glEnable(gl.GL_LIGHTING)
        else:
            gl.glPushMatrix()
            gl.glTranslatef(0.02, -0.04, 0.05)
            if player.state in (PlayerState.BLOCK, PlayerState.PARRY):
                gl.glRotatef(78.0, 1.0, 0.0, 0.0)
                gl.glRotatef(52.0, 0.0, 0.0, 1.0)
            else:
                gl.glRotatef(-102.0, 1.0, 0.0, 0.0)
                gl.glRotatef(12.0, 0.0, 0.0, 1.0)
            self._draw_katana(blade_len=0.82, handle_len=0.22, is_wakizashi=True)
            gl.glPopMatrix()
        gl.glPopMatrix()  # Fim Braço Esquerdo

        # 7. Braço Direito Alongado (Prismas Chanfrados + Sode em 135° + Katana de 1.44m em Seção Diamante)
        gl.glPushMatrix()
        gl.glTranslatef(-0.265, 0.62, 0.0)
        t_atk = clamp(player.state_timer / max(0.001, player.state_duration), 0.0, 1.0)
        elbow_r = -22.0
        if player.state == PlayerState.LIGHT_1:
            gl.glRotatef(-75.0, 1.0, 0.0, 0.0)
            gl.glRotatef((0.5 - t_atk) * 140.0, 0.0, 1.0, 0.0)
            elbow_r = -15.0
        elif player.state == PlayerState.LIGHT_2:
            gl.glRotatef(-75.0, 1.0, 0.0, 0.0)
            gl.glRotatef((t_atk - 0.5) * 140.0, 0.0, 1.0, 0.0)
            elbow_r = -15.0
        elif player.state == PlayerState.LIGHT_3:
            gl.glRotatef(-90.0, 1.0, 0.0, 0.0)
            gl.glTranslatef(0.0, 0.0, math.sin(t_atk * math.pi) * 0.45)
            elbow_r = -5.0
        elif player.state == PlayerState.HEAVY:
            gl.glRotatef(-155.0 + t_atk * 135.0, 1.0, 0.0, 0.0)
            elbow_r = -12.0
        elif player.state == PlayerState.BLOCK:
            gl.glRotatef(-70.0, 1.0, 0.0, 0.0)
            gl.glRotatef(34.0, 0.0, 1.0, 0.0)
            gl.glRotatef(28.0, 0.0, 0.0, 1.0)
            elbow_r = -45.0
        elif player.state == PlayerState.PARRY:
            t_p = clamp(player.state_timer / max(0.001, player.state_duration), 0.0, 1.0)
            sweep = math.sin(t_p * math.pi) * 75.0
            gl.glRotatef(-75.0, 1.0, 0.0, 0.0)
            gl.glRotatef(30.0 - sweep, 0.0, 1.0, 0.0)
            elbow_r = -30.0
        else:
            gl.glRotatef(-18.0 + leg_swing * 0.5, 1.0, 0.0, 0.0)

        # Ombreira Sode Direita (3 placas em degraus dobradas em ângulo obtuso de 135°)
        self._draw_samurai_sode(-1.0)

        # Braço Superior Direito Esguio (Prisma Hexagonal de 6 lados)
        self._set_material_heavy_cloth()
        gl.glColor3f(*do_dark)
        gl.glTranslatef(-0.02, -0.31, 0.0)
        self.draw_chiseled_prism(0.048, 0.048, 0.062, 0.062, 0.31, sides=6, cap_top=True)

        # Cotovelo + Antebraço Direito Blindado Octogonal (Kote de 8 lados)
        self._set_material_forged_metal()
        gl.glRotatef(elbow_r, 1.0, 0.0, 0.0)
        gl.glColor3f(*obsidian)
        gl.glTranslatef(0.0, -0.30, 0.0)
        self.draw_chiseled_prism(0.038, 0.042, 0.052, 0.055, 0.30, sides=8)
        gl.glColor3f(*old_gold)
        gl.glPushMatrix()
        gl.glTranslatef(-0.044, 0.05, 0.0)
        gl.glRotatef(90.0, 0.0, 1.0, 0.0)
        self.draw_trapezoid_plate(0.045, 0.055, 0.21, 0.015)
        gl.glPopMatrix()

        # Manopla Hexagonal Chanfrada (Tekko)
        gl.glColor3f(*obsidian)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.07, 0.0)
        self.draw_chiseled_prism(0.035, 0.042, 0.042, 0.046, 0.07, sides=6, cap_bot=True)
        gl.glPopMatrix()

        # Katana Principal em Tamanho Realista (1.44m, -25%) e Seção em Diamante na Mão Direita
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.04, 0.05)
        if player.state in (PlayerState.BLOCK, PlayerState.PARRY):
            gl.glRotatef(78.0, 1.0, 0.0, 0.0)
            gl.glRotatef(-48.0, 0.0, 0.0, 1.0)
        else:
            gl.glRotatef(75.0, 1.0, 0.0, 0.0)
        self._draw_katana(blade_len=1.44, handle_len=0.34, is_wakizashi=False)
        gl.glPopMatrix()

        gl.glPopMatrix()  # Fim Braço Direito
        gl.glPopMatrix()  # Fim Torso/Pelvis
        gl.glPopMatrix()  # Fim Player
        gl.glShadeModel(gl.GL_SMOOTH)

    def render_hollow_enemy(self, enemy: HollowEnemy) -> None:
        if not enemy.alive and enemy.state_timer > 1.8:
            return

        gl.glPushMatrix()
        gl.glTranslatef(enemy.pos.x, enemy.pos.y, enemy.pos.z)
        self._draw_ground_shadow(0.55)

        gl.glRotatef(math.degrees(enemy.facing_yaw), 0.0, 1.0, 0.0)
        if not enemy.alive:
            gl.glRotatef(min(90.0, enemy.state_timer * 150.0), 1.0, 0.0, 0.0)
        elif enemy.state == EnemyState.STAGGER:
            gl.glRotatef(-25.0, 1.0, 0.0, 0.0)

        phase = enemy.walk_cycle * 2.2
        leg_ang = math.sin(phase) * 22.0 if enemy.state == EnemyState.CHASE else 0.0
        knee_l = max(8.0, -math.cos(phase) * 24.0 + 12.0) if enemy.state == EnemyState.CHASE else 10.0
        knee_r = max(8.0, math.cos(phase) * 24.0 + 12.0) if enemy.state == EnemyState.CHASE else 10.0

        rust_armor = (0.38, 0.28, 0.23)
        dark_iron = (0.22, 0.19, 0.17)
        hollow_skin = (0.30, 0.26, 0.22)

        # Pernas articuladas do Soldado Vazio
        self._draw_articulated_leg(0.15, leg_ang, knee_l, rust_armor, dark_iron, dark_iron)
        self._draw_articulated_leg(-0.15, -leg_ang, knee_r, rust_armor, dark_iron, dark_iron)

        # Quadril e Torso curvado em V de Soldado Vazio
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.76, 0.0)
        gl.glRotatef(9.0, 1.0, 0.0, 0.0)  # Postura curvada ameaçadora

        gl.glColor3f(*dark_iron)
        self.draw_box(0.34, 0.12, 0.22)
        # Abdômen magro de morto-vivo
        gl.glTranslatef(0.0, 0.06, 0.0)
        gl.glColor3f(*hollow_skin)
        self.draw_tapered_torso(0.28, 0.18, 0.36, 0.22, 0.22)
        # Couraça enferrujada peitoral em V
        gl.glTranslatef(0.0, 0.20, 0.0)
        gl.glColor3f(*rust_armor)
        self.draw_tapered_torso(0.36, 0.22, 0.48, 0.28, 0.34)

        # Cabeça: Rosto Angular Esquelético + Elmo Cônico de Infantaria (Kettle/Spangenhelm)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.46, 0.02)
        gl.glColor3f(*hollow_skin)
        self.draw_octa(0.18, 0.21, 0.19)
        # Aba e Topo Cônico do Elmo Enferrujado
        gl.glColor3f(*rust_armor)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.06, 0.0)
        self.draw_box(0.26, 0.04, 0.26)
        self.draw_pyramid(0.22, 0.20, 0.22)
        gl.glPopMatrix()
        # Olhos vermelhos brilhantes em fendas angulares
        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(1.0, 0.22, 0.10)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.05, 0.0, 0.10)
            self.draw_box(0.035, 0.022, 0.02)
            gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()

        # Braço Esquerdo do Guardião + Escudo Quebrado
        gl.glPushMatrix()
        gl.glTranslatef(0.28, 0.28, 0.0)
        gl.glColor3f(*rust_armor)
        self._draw_knight_pauldron(1.0, scale=0.85)
        gl.glRotatef(-25.0, 1.0, 0.0, 0.0)
        gl.glTranslatef(0.02, -0.38, 0.05)
        self.draw_tapered_torso(0.09, 0.09, 0.12, 0.12, 0.38)
        gl.glPushMatrix()
        gl.glTranslatef(0.07, 0.05, 0.06)
        gl.glColor3f(0.28, 0.20, 0.14)
        self.draw_octa(0.06, 0.48, 0.42)
        gl.glPopMatrix()
        gl.glPopMatrix()

        # Braço Direito + Espada Larga Chanfrada
        gl.glPushMatrix()
        gl.glTranslatef(-0.28, 0.28, 0.0)
        if enemy.state == EnemyState.WINDUP:
            gl.glRotatef(-140.0, 1.0, 0.0, 0.0)
        elif enemy.state == EnemyState.ATTACK:
            t_a = clamp(enemy.state_timer / 0.28, 0.0, 1.0)
            gl.glRotatef(-140.0 + t_a * 125.0, 1.0, 0.0, 0.0)
        else:
            gl.glRotatef(-28.0, 1.0, 0.0, 0.0)

        gl.glColor3f(*rust_armor)
        self._draw_knight_pauldron(-1.0, scale=0.85)
        gl.glTranslatef(-0.02, -0.40, 0.04)
        self.draw_tapered_torso(0.09, 0.09, 0.12, 0.12, 0.40)

        # Espada do Guardião
        gl.glTranslatef(0.0, -0.02, 0.06)
        gl.glRotatef(70.0, 1.0, 0.0, 0.0)
        gl.glColor3f(0.42, 0.32, 0.18)
        self.draw_box(0.32, 0.05, 0.07)
        if enemy.state == EnemyState.WINDUP:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glColor3f(1.0, 0.45, 0.15)
        else:
            gl.glColor3f(0.58, 0.54, 0.50)
        self.draw_sword_blade(0.11, 1.38, 0.04)
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()

        gl.glPopMatrix()
        gl.glPopMatrix()

    def render_boss(self, boss: BossMalakor) -> None:
        if not boss.alive and boss.state_timer > 2.6:
            return

        gl.glPushMatrix()
        gl.glTranslatef(boss.pos.x, boss.pos.y, boss.pos.z)
        self._draw_ground_shadow(1.30)

        gl.glRotatef(math.degrees(boss.facing_yaw), 0.0, 1.0, 0.0)

        if not boss.alive:
            kneel = min(1.2, boss.state_timer * 0.9)
            gl.glTranslatef(0.0, -kneel, 0.0)
            gl.glRotatef(min(45.0, boss.state_timer * 35.0), 1.0, 0.0, 0.0)
        elif boss.state == BossState.STAGGER:
            gl.glTranslatef(0.0, -0.45, 0.0)
            gl.glRotatef(24.0, 1.0, 0.0, 0.0)

        phase = boss.walk_cycle * 1.8
        leg_swing = 0.0
        knee_l = 6.0
        knee_r = 6.0
        if boss.state in (BossState.CHASE, BossState.IDLE_STRAFE):
            leg_swing = math.sin(phase) * 24.0
            knee_l = max(6.0, -math.cos(phase) * 26.0 + 12.0)
            knee_r = max(6.0, math.cos(phase) * 26.0 + 12.0)

        obsidian = (0.22, 0.16, 0.16) if boss.phase == 2 else (0.17, 0.18, 0.22)
        dark_plate = (0.12, 0.12, 0.15)
        ember_trim = (0.88, 0.45, 0.14) if boss.phase == 2 else (0.58, 0.48, 0.26)

        # 1. Pernas Colossais Articuladas de Malakor (Escala 1.65x)
        gl.glPushMatrix()
        gl.glScalef(1.65, 1.55, 1.65)
        self._draw_articulated_leg(0.21, leg_swing, knee_l, obsidian, ember_trim, dark_plate)
        self._draw_articulated_leg(-0.21, -leg_swing, knee_r, obsidian, ember_trim, dark_plate)
        gl.glPopMatrix()

        # 2. Quadril, Cintura Estreita e Faldões Góticos com Espinhos
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 1.22, 0.0)
        gl.glColor3f(*dark_plate)
        self.draw_box(0.68, 0.22, 0.44)

        # Faldões laterais pontiagudos (Tassets de Lorde das Cinzas)
        gl.glColor3f(*obsidian)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.38, -0.18, 0.0)
            gl.glRotatef(s * 16.0, 0.0, 0.0, 1.0)
            gl.glRotatef(180.0, 1.0, 0.0, 0.0)
            self.draw_pyramid(0.14, 0.45, 0.42)
            gl.glPopMatrix()

        # 3. Abdômen Afunilado + Peitoral Colossal em V Extremo
        gl.glTranslatef(0.0, 0.10, 0.0)
        gl.glColor3f(*dark_plate)
        self.draw_tapered_torso(0.56, 0.38, 0.76, 0.46, 0.42)

        gl.glTranslatef(0.0, 0.40, 0.0)
        gl.glColor3f(*obsidian)
        self.draw_tapered_torso(0.76, 0.46, 1.18, 0.62, 0.72)

        # Costelas de Armadura e Núcleo de Brasa Incandescente no Peito!
        gl.glColor3f(*ember_trim)
        for rib_y in (0.18, 0.36, 0.54):
            gl.glPushMatrix()
            gl.glTranslatef(0.0, rib_y, 0.0)
            self.draw_box(0.82 + rib_y * 0.4, 0.06, 0.64)
            gl.glPopMatrix()

        if boss.phase == 2:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glColor3f(1.0, 0.48, 0.12)
            gl.glPushMatrix()
            gl.glTranslatef(0.0, 0.38, 0.30)
            self.draw_octa(0.28, 0.34, 0.10)
            gl.glPopMatrix()
            gl.glEnable(gl.GL_LIGHTING)

        # 4. Manto Real Rasgado em 3 Tiras Pontiagudas nas Costas
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.65, -0.32)
        gl.glRotatef(15.0 + abs(leg_swing) * 0.4, 1.0, 0.0, 0.0)
        for px in (-0.34, 0.0, 0.34):
            gl.glPushMatrix()
            gl.glTranslatef(px, -0.95, 0.0)
            gl.glColor3f(0.36, 0.08, 0.09) if px == 0.0 else gl.glColor3f(0.24, 0.06, 0.07)
            self.draw_tapered_torso(0.44, 0.05, 0.32, 0.05, 1.85)
            gl.glPopMatrix()
        gl.glPopMatrix()

        # 5. Ombreiras Gigantes Facetadas com Espinhos Piramidais (Pauldrons)
        for sign in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(sign * 0.68, 0.64, 0.0)
            gl.glColor3f(*obsidian)
            self._draw_knight_pauldron(sign, scale=1.75)
            # Espinhos de ferro negro saindo das ombreiras
            gl.glColor3f(*ember_trim)
            for sp_x, sp_ang in ((0.0, 0.0), (sign * 0.14, sign * -28.0)):
                gl.glPushMatrix()
                gl.glTranslatef(sp_x, 0.24, 0.0)
                gl.glRotatef(sp_ang, 0.0, 0.0, 1.0)
                self.draw_pyramid(0.10, 0.32, 0.10)
                gl.glPopMatrix()
            gl.glPopMatrix()

        # 6. Elmo Coroado Facetado de Malakor (Estilo Sauron / Soul of Cinder)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.96, 0.04)
        gl.glColor3f(*obsidian)
        self.draw_octa(0.36, 0.42, 0.38)
        # Máscara facial angular em V
        gl.glColor3f(*dark_plate)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.04, 0.17)
        gl.glRotatef(85.0, 1.0, 0.0, 0.0)
        self.draw_pyramid(0.32, 0.16, 0.26)
        gl.glPopMatrix()

        # Coroa de 7 Espinhos Afiados
        gl.glColor3f(*ember_trim)
        for i in range(7):
            ang = (i - 3) * 0.42
            gl.glPushMatrix()
            gl.glTranslatef(math.sin(ang) * 0.18, 0.20, math.cos(ang) * 0.18)
            gl.glRotatef(math.degrees(ang) * 0.35, 0.0, 0.0, -1.0)
            self.draw_pyramid(0.06, 0.34 if i == 3 else 0.24, 0.06)
            gl.glPopMatrix()

        # Olhos Flamejantes em Fenda
        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(1.0, 0.32, 0.08) if boss.phase == 2 else gl.glColor3f(1.0, 0.68, 0.20)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.08, 0.04, 0.21)
            gl.glRotatef(s * -12.0, 0.0, 0.0, 1.0)
            self.draw_box(0.07, 0.028, 0.03)
            gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()

        # 7. Braço Esquerdo Articulado do Boss
        gl.glPushMatrix()
        gl.glTranslatef(0.68, 0.56, 0.0)
        gl.glRotatef(-25.0, 1.0, 0.0, 0.0)
        gl.glColor3f(*dark_plate)
        gl.glTranslatef(0.0, -0.44, 0.0)
        self.draw_tapered_torso(0.20, 0.20, 0.26, 0.26, 0.44)
        gl.glRotatef(-30.0, 1.0, 0.0, 0.0)
        gl.glColor3f(*obsidian)
        gl.glTranslatef(0.0, -0.44, 0.0)
        self.draw_tapered_torso(0.18, 0.18, 0.24, 0.24, 0.44)
        gl.glPopMatrix()

        # 8. Braço Direito Articulado do Boss (acompanha a direção da espada)
        gl.glPushMatrix()
        gl.glTranslatef(-0.68, 0.56, 0.0)
        gl.glRotatef(-45.0, 1.0, 0.0, 0.0)
        gl.glColor3f(*dark_plate)
        gl.glTranslatef(0.0, -0.44, 0.0)
        self.draw_tapered_torso(0.20, 0.20, 0.26, 0.26, 0.44)
        gl.glPopMatrix()

        gl.glPopMatrix()  # Fim Torso do Boss
        gl.glPopMatrix()  # Fim Transformação Base do Boss

        # Renderiza a Espada Colossal Facetada do Boss exatamente no segmento de hitbox
        b_pos, t_pos = boss.get_sword_segment()
        self._draw_boss_greatsword(b_pos, t_pos, boss)

    def _draw_boss_greatsword(self, base_pos: Vec3, tip_pos: Vec3, boss: BossMalakor) -> None:
        diff = tip_pos - base_pos
        length = diff.length()
        if length < 0.01:
            return
        dir_n = diff / length

        up = Vec3(0.0, 1.0, 0.0)
        axis = up.cross(dir_n)
        axis_len = axis.length()
        dot = clamp(up.dot(dir_n), -1.0, 1.0)
        angle_deg = math.degrees(math.acos(dot))

        gl.glPushMatrix()
        gl.glTranslatef(base_pos.x, base_pos.y, base_pos.z)
        if axis_len > 1e-5:
            gl.glRotatef(angle_deg, axis.x / axis_len, axis.y / axis_len, axis.z / axis_len)

        # Punho longo de duas mãos + Pomo em pirâmide invertida
        gl.glColor3f(0.25, 0.15, 0.10)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.30, 0.0)
        self.draw_box(0.09, 0.60, 0.09)
        gl.glTranslatef(0.0, -0.35, 0.0)
        gl.glColor3f(0.68, 0.50, 0.22)
        self.draw_octa(0.18, 0.18, 0.18)
        gl.glPopMatrix()

        # Guarda Colossal em V com Pontas Laterais
        gl.glColor3f(0.65, 0.48, 0.22)
        self.draw_box(0.95, 0.12, 0.18)
        for s in (-1.0, 1.0):
            gl.glPushMatrix()
            gl.glTranslatef(s * 0.48, 0.0, 0.0)
            gl.glRotatef(s * -90.0, 0.0, 0.0, 1.0)
            self.draw_pyramid(0.14, 0.26, 0.14)
            gl.glPopMatrix()

        # Ganchos de Parry (Parry Hooks de Zweihander) a 25% da lâmina
        gl.glPushMatrix()
        gl.glTranslatef(0.0, length * 0.22, 0.0)
        self.draw_box(0.56, 0.07, 0.10)
        gl.glPopMatrix()

        # Lâmina Colossal Facetada com Ponta Afiada
        if boss.phase == 2:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glColor3f(1.0, 0.42, 0.10)
            self.draw_sword_blade(0.34, length, 0.10)
            gl.glColor3f(1.0, 0.85, 0.30)
            self.draw_sword_blade(0.20, length * 0.97, 0.12)
            gl.glEnable(gl.GL_LIGHTING)
        elif boss.state == BossState.WINDUP:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glColor3f(0.92, 0.72, 0.42)
            self.draw_sword_blade(0.32, length, 0.09)
            gl.glEnable(gl.GL_LIGHTING)
        else:
            gl.glColor3f(0.48, 0.50, 0.56)
            self.draw_sword_blade(0.32, length, 0.09)

        gl.glPopMatrix()

    def _draw_ground_shadow(self, radius: float) -> None:
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glColor4f(0.02, 0.02, 0.03, 0.65)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex3f(0.0, 0.03, 0.0)
        for i in range(17):
            a = i * (2.0 * math.pi / 16.0)
            gl.glVertex3f(math.cos(a) * radius, 0.03, math.sin(a) * radius)
        gl.glEnd()
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_LIGHTING)

    def render_particles_and_effects(self, particle_sys) -> None:
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)

        # 1. Rastros de Lâmina (Weapon Swing Trails)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE)
        if len(particle_sys.trails) >= 2:
            gl.glBegin(gl.GL_QUAD_STRIP)
            for tr in particle_sys.trails:
                alpha = clamp(tr.life / max(0.001, tr.max_life), 0.0, 1.0) * 0.65
                gl.glColor4f(tr.color[0], tr.color[1], tr.color[2], alpha)
                gl.glVertex3f(tr.base_pos.x, tr.base_pos.y, tr.base_pos.z)
                gl.glVertex3f(tr.tip_pos.x, tr.tip_pos.y, tr.tip_pos.z)
            gl.glEnd()

        # 2. Ondas de Choque no chão (Boss Shockwaves)
        gl.glLineWidth(3.5)
        for w in particle_sys.shockwaves:
            alpha = clamp(w.life / max(0.001, w.max_life), 0.0, 1.0)
            gl.glColor4f(w.color[0], w.color[1], w.color[2], alpha)
            gl.glBegin(gl.GL_LINE_LOOP)
            for s in range(48):
                a = s * (2.0 * math.pi / 48.0)
                gl.glVertex3f(
                    w.center.x + math.cos(a) * w.radius,
                    0.12,
                    w.center.z + math.sin(a) * w.radius,
                )
            gl.glEnd()

        # 3. Partículas 3D
        for p in particle_sys.particles:
            alpha = clamp(p.life / max(0.001, p.max_life), 0.0, 1.0)
            if p.additive:
                gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE)
            else:
                gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glColor4f(p.color[0], p.color[1], p.color[2], alpha)
            gl.glPushMatrix()
            gl.glTranslatef(p.pos.x, p.pos.y, p.pos.z)
            self.draw_box(p.size, p.size, p.size)
            gl.glPopMatrix()

        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_LIGHTING)

    def _compile_title_landscape_list(self) -> None:
        """
        Compila a paisagem 3D épica da Tela Inicial:
        - Penhasco rochoso facetado à beira do abismo
        - Cemitério de espadas antigas e ruínas góticas no penhasco
        - Cordilheira de montanhas escarpadas ao redor do vale
        - Ponte de arcos quebrados atravessando o abismo de neblina
        - Cidadela Gótica Colossal no topo da montanha distante com vitrais acesos
        """
        self.dl_title_vista = gl.glGenLists(1)
        gl.glNewList(self.dl_title_vista, gl.GL_COMPILE)

        # 1. Penhasco Rochoso do Primeiro Plano (Plataforma em camadas de rocha chanfrada)
        gl.glColor3f(0.14, 0.14, 0.17)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -1.2, 1.0)
        self.draw_tapered_torso(9.5, 8.0, 12.5, 10.0, 1.2)
        gl.glPopMatrix()

        # Lajes de pedra irregulares na beira do precipício
        cliff_slabs = [
            (-2.8, -0.35, -2.2, 4.2, 0.7, 3.8, 12.0),
            (0.4, -0.30, -2.8, 4.8, 0.6, 3.6, -8.0),
            (3.4, -0.40, -1.8, 3.8, 0.8, 3.5, 18.0),
            (-4.5, 0.15, 0.8, 2.8, 1.1, 3.2, -22.0),
            (4.8, 0.25, 1.2, 2.6, 1.3, 3.0, 15.0),
        ]
        for cx, cy, cz, sx, sy, sz, rot_y in cliff_slabs:
            gl.glPushMatrix()
            gl.glTranslatef(cx, cy, cz)
            gl.glRotatef(rot_y, 0.0, 1.0, 0.0)
            gl.glColor3f(0.16, 0.16, 0.19)
            self.draw_box(sx, sy, sz)
            gl.glPopMatrix()

        # Ruína de Arco Gótico Quebrado na esquerda do penhasco
        gl.glColor3f(0.20, 0.20, 0.24)
        gl.glPushMatrix()
        gl.glTranslatef(-3.8, 0.0, -1.2)
        gl.glRotatef(14.0, 0.0, 1.0, 0.0)
        self.draw_box(0.85, 0.6, 0.85)
        self.draw_cylinder(0.36, 3.4)
        gl.glTranslatef(0.0, 3.4, 0.0)
        self.draw_box(0.95, 0.35, 0.95)
        gl.glPopMatrix()

        # Cemitério de Espadas Antigas cravadas na rocha do penhasco!
        graveyard_swords = [
            (-2.6, 0.0, -1.8, -12.0, 8.0, 1.45),
            (-3.2, 0.0, -0.4, 15.0, -10.0, 1.25),
            (-1.9, 0.0, -2.9, 6.0, 14.0, 1.60),
            (2.9, 0.0, -2.1, -18.0, -6.0, 1.50),
            (3.7, 0.0, -0.8, 9.0, 12.0, 1.30),
            (0.6, 0.0, -3.5, -8.0, 16.0, 1.35),
        ]
        for sx, sy, sz, rx, rz, slen in graveyard_swords:
            gl.glPushMatrix()
            gl.glTranslatef(sx, sy, sz)
            gl.glRotatef(rx, 1.0, 0.0, 0.0)
            gl.glRotatef(rz, 0.0, 0.0, 1.0)
            gl.glColor3f(0.36, 0.37, 0.42)
            self.draw_sword_blade(0.10, slen, 0.04)
            gl.glTranslatef(0.0, slen * 0.78, 0.0)
            gl.glColor3f(0.45, 0.36, 0.22)
            self.draw_box(0.38, 0.05, 0.07)
            gl.glTranslatef(0.0, 0.22, 0.0)
            self.draw_octa(0.07, 0.07, 0.07)
            gl.glPopMatrix()

        # 2. Cordilheira de Montanhas Escarpadas ao Fundo (Picos Piramidais Gigantes)
        mountains = [
            # (x, y, z, largura_base, altura, rot_y, cor_rgb)
            (-42.0, -14.0, -65.0, 38.0, 42.0, 15.0, (0.09, 0.09, 0.13)),
            (-22.0, -14.0, -72.0, 34.0, 36.0, -20.0, (0.11, 0.10, 0.15)),
            (26.0, -14.0, -68.0, 36.0, 39.0, 28.0, (0.10, 0.10, 0.14)),
            (46.0, -14.0, -58.0, 34.0, 44.0, -12.0, (0.08, 0.08, 0.12)),
            (-16.0, -12.0, -42.0, 22.0, 22.0, 35.0, (0.12, 0.12, 0.16)),
            (20.0, -12.0, -45.0, 24.0, 25.0, -30.0, (0.12, 0.12, 0.16)),
            # Montanha Central onde se ergue a Cidadela de Malakor!
            (3.5, -14.0, -64.0, 28.0, 29.0, 45.0, (0.13, 0.11, 0.15)),
        ]
        for mx, my, mz, mw, mh, mrot, mcol in mountains:
            gl.glPushMatrix()
            gl.glTranslatef(mx, my, mz)
            gl.glRotatef(mrot, 0.0, 1.0, 0.0)
            gl.glColor3f(*mcol)
            self.draw_pyramid(mw, mh, mw)
            gl.glPopMatrix()

        # 3. Viaduto / Ponte de Arcos Quebrados atravessando o Abismo até a Cidadela
        gl.glColor3f(0.15, 0.14, 0.18)
        for i in range(6):
            bz = -16.0 - i * 7.2
            bx = 0.5 + i * 0.45
            by = -2.5 + i * 1.65
            # Ruptura dramática no meio da ponte (arcos destruídos)
            if i == 2:
                continue
            gl.glPushMatrix()
            gl.glTranslatef(bx, by, bz)
            # Pilar do viaduto descendo até o abismo
            self.draw_box(1.6, 14.0, 1.8)
            # Tabuleiro superior da ponte
            gl.glTranslatef(0.0, 7.2, 0.0)
            self.draw_box(2.8, 0.9, 6.2)
            gl.glPopMatrix()

        # 4. Cidadela Gótica Colossal de Malakor no Topo da Montanha Distante!
        gl.glPushMatrix()
        gl.glTranslatef(3.5, 11.0, -64.0)
        # Corpo principal da Catedral
        gl.glColor3f(0.14, 0.12, 0.17)
        self.draw_box(11.0, 9.0, 8.0)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 5.5, 0.0)
        self.draw_box(6.5, 7.0, 6.0)
        gl.glPopMatrix()

        # 5 Torres Pontiagudas Góticas (Spires)
        spires = [
            (0.0, 9.0, 0.0, 3.2, 11.5),     # Grande Torre Central
            (-4.2, 4.5, 1.5, 2.0, 8.5),     # Torre Oeste
            (4.2, 4.5, 1.5, 2.0, 8.5),      # Torre Leste
            (-6.5, 2.0, -1.0, 1.6, 7.0),    # Contraforte Extremo Oeste
            (6.5, 2.0, -1.0, 1.6, 7.0),     # Contraforte Extremo Leste
        ]
        for sx, sy, sz, sw, sh in spires:
            gl.glPushMatrix()
            gl.glTranslatef(sx, sy, sz)
            gl.glColor3f(0.16, 0.13, 0.19)
            self.draw_box(sw, sh * 0.45, sw)
            gl.glTranslatef(0.0, sh * 0.22, 0.0)
            gl.glColor3f(0.11, 0.09, 0.14)
            self.draw_pyramid(sw * 1.15, sh * 0.78, sw * 1.15)
            gl.glPopMatrix()

        # Vitrais Góticos Acesos na Cidadela (brilho âmbar/fogo na distância)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glColor3f(1.0, 0.55, 0.18)
        for wx, wy in ((-2.2, 2.0), (0.0, 3.5), (2.2, 2.0), (0.0, 7.2)):
            gl.glPushMatrix()
            gl.glTranslatef(wx, wy, 4.1)
            self.draw_box(0.55, 1.6, 0.1)
            gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()  # Fim Cidadela

        gl.glEndList()

    def render_title_landscape(self, dt: float, player: Player, particle_sys) -> None:
        """
        Renderiza a cena 3D ao vivo da Tela Inicial:
        Céu Crepuscular + Eclipse Solar (Dark Sign) + Montanhas e Cidadela +
        Penhasco com Fogueira Acesa + Cavaleiro das Cinzas contemplando o horizonte.
        """
        self.time_accum += dt
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        # 1. Desenha o Céu Crepuscular e Estrelas em Projeção 2D de Fundo (sem gravar no Depth Buffer)
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_FOG)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, self.width, self.height, 0, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Gradiente vertical do céu: Noite Obsidiana no topo -> Rubro/Âmbar de Eclipse no horizonte
        gl.glBegin(gl.GL_QUADS)
        gl.glColor3f(0.03, 0.03, 0.06)
        gl.glVertex2f(0, 0)
        gl.glVertex2f(self.width, 0)
        gl.glColor3f(0.18, 0.07, 0.10)
        gl.glVertex2f(self.width, self.height * 0.58)
        gl.glVertex2f(0, self.height * 0.58)

        gl.glColor3f(0.18, 0.07, 0.10)
        gl.glVertex2f(0, self.height * 0.58)
        gl.glVertex2f(self.width, self.height * 0.58)
        gl.glColor3f(0.38, 0.14, 0.09)
        gl.glVertex2f(self.width, self.height)
        gl.glVertex2f(0, self.height)
        gl.glEnd()

        # Estrelas cintilantes no céu superior
        gl.glPointSize(2.0)
        gl.glBegin(gl.GL_POINTS)
        for i in range(90):
            sx = ((i * 197) % 997) / 997.0 * self.width
            sy = ((i * 353) % 613) / 613.0 * (self.height * 0.52)
            twinkle = 0.45 + 0.55 * math.sin(self.time_accum * 2.5 + i * 1.7)
            gl.glColor3f(0.9 * twinkle, 0.88 * twinkle, 1.0 * twinkle)
            gl.glVertex2f(sx, sy)
        gl.glEnd()

        # 2. Configura a Câmera 3D Cinematográfica com movimento suave de respiração/panorâmica
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(48.0, self.width / max(1, self.height), 0.25, 160.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        cam_sway_x = math.sin(self.time_accum * 0.35) * 0.65
        cam_sway_y = math.cos(self.time_accum * 0.28) * 0.18
        glu.gluLookAt(
            0.35 + cam_sway_x,
            2.15 + cam_sway_y,
            4.85,
            0.65,
            2.55,
            -18.0,
            0.0,
            1.0,
            0.0,
        )

        # 3. Desenha o ECLIPSE SOLAR ("DARK SIGN") no céu atrás da Cidadela!
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_FOG)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        gl.glPushMatrix()
        gl.glTranslatef(4.2, 26.5, -78.0)

        # Halo externo difuso de fogo rubro
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(1.0, 0.35, 0.08, 0.55)
        gl.glVertex3f(0.0, 0.0, 0.0)
        for i in range(49):
            a = i * (2.0 * math.pi / 48.0)
            pulse_r = 16.5 + 0.6 * math.sin(self.time_accum * 4.0 + i * 0.5)
            gl.glColor4f(0.85, 0.15, 0.05, 0.0)
            gl.glVertex3f(math.cos(a) * pulse_r, math.sin(a) * pulse_r, 0.0)
        gl.glEnd()

        # Coroa incandescente dourada/laranja do Eclipse
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glColor4f(1.0, 0.92, 0.55, 1.0)
        gl.glVertex3f(0.0, 0.0, 0.2)
        for i in range(49):
            a = i * (2.0 * math.pi / 48.0)
            r_corona = 9.4 + 0.35 * math.sin(self.time_accum * 7.0 + i * 1.1)
            gl.glColor4f(1.0, 0.52, 0.12, 0.95)
            gl.glVertex3f(math.cos(a) * r_corona, math.sin(a) * r_corona, 0.2)
        gl.glEnd()

        # Fluxo vertical de fogo escorrendo do Eclipse até a Cidadela (estilo Dark Souls III!)
        gl.glBegin(gl.GL_TRIANGLES)
        gl.glColor4f(1.0, 0.78, 0.28, 0.85)
        gl.glVertex3f(-1.2, -7.8, 0.15)
        gl.glVertex3f(1.2, -7.8, 0.15)
        gl.glColor4f(1.0, 0.25, 0.05, 0.0)
        gl.glVertex3f(-0.3, -24.0, 0.15)
        gl.glEnd()

        # Disco central negro da Lua ocultando o Sol
        gl.glColor4f(0.04, 0.03, 0.05, 1.0)
        gl.glBegin(gl.GL_TRIANGLE_FAN)
        gl.glVertex3f(0.0, 0.0, 0.4)
        for i in range(49):
            a = i * (2.0 * math.pi / 48.0)
            gl.glVertex3f(math.cos(a) * 7.8, math.sin(a) * 7.8, 0.4)
        gl.glEnd()
        gl.glPopMatrix()
        gl.glDisable(gl.GL_BLEND)

        # 4. Ativa Iluminação 3D e Neblina Suave para a Paisagem
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_FOG)
        gl.glFogfv(gl.GL_FOG_COLOR, (0.14, 0.07, 0.09, 1.0))
        gl.glFogf(gl.GL_FOG_DENSITY, 0.011)

        # Luz 0: Contraluz dramática vinda do Eclipse no horizonte
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (0.15, 0.55, -1.0, 0.0))
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (0.72, 0.45, 0.42, 1.0))

        # Luz 1: Luz quente crepitante da Fogueira no penhasco
        flicker = 0.92 + 0.15 * math.sin(self.time_accum * 16.0)
        bf_pos = Vec3(1.55, 0.0, 0.65)
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_POSITION, (bf_pos.x, bf_pos.y + 1.2, bf_pos.z, 1.0))
        gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, (1.0 * flicker, 0.58 * flicker, 0.18, 1.0))

        # Renderiza Montanhas, Viaduto, Cidadela e Penhasco Rochoso
        gl.glCallList(self.dl_title_vista)

        # Mar de Neblina no Fundo do Abismo
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        for layer_i, mist_y in enumerate((-5.5, -3.8)):
            gl.glColor4f(0.24, 0.11, 0.13, 0.36 - layer_i * 0.12)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex3f(-60.0, mist_y, -5.0)
            gl.glVertex3f(60.0, mist_y, -5.0)
            gl.glVertex3f(60.0, mist_y, -75.0)
            gl.glVertex3f(-60.0, mist_y, -75.0)
            gl.glEnd()
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_LIGHTING)

        # 5. Desenha a Fogueira Acesa no Penhasco
        gl.glPushMatrix()
        gl.glTranslatef(bf_pos.x, bf_pos.y, bf_pos.z)
        gl.glColor3f(0.22, 0.20, 0.19)
        self.draw_cylinder(0.68, 0.20)
        gl.glColor3f(0.16, 0.16, 0.18)
        for i in range(8):
            ang = i * (2.0 * math.pi / 8.0)
            gl.glPushMatrix()
            gl.glTranslatef(math.cos(ang) * 0.60, 0.14, math.sin(ang) * 0.60)
            self.draw_box(0.24, 0.22, 0.24)
            gl.glPopMatrix()
        # Espada Espiral Cravada na Fogueira
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.18, 0.0)
        gl.glRotatef(14.0, 0.0, 0.0, 1.0)
        gl.glColor3f(0.55, 0.50, 0.45)
        self.draw_sword_blade(0.11, 1.28, 0.05)
        gl.glTranslatef(0.0, 1.08, 0.0)
        gl.glColor3f(0.65, 0.48, 0.22)
        self.draw_box(0.40, 0.06, 0.08)
        gl.glPopMatrix()
        # Chamas poligonais dançantes
        gl.glDisable(gl.GL_LIGHTING)
        flame_h = 0.62 + 0.15 * math.sin(self.time_accum * 13.0)
        gl.glPushMatrix()
        gl.glTranslatef(0.0, 0.20, 0.0)
        gl.glRotatef(self.time_accum * 50.0, 0.0, 1.0, 0.0)
        gl.glColor3f(1.0, 0.48, 0.10)
        self.draw_pyramid(0.42, flame_h, 0.42)
        gl.glRotatef(45.0, 0.0, 1.0, 0.0)
        gl.glColor3f(1.0, 0.86, 0.28)
        self.draw_pyramid(0.26, flame_h * 0.82, 0.26)
        gl.glPopMatrix()
        gl.glEnable(gl.GL_LIGHTING)
        gl.glPopMatrix()

        # 6. O Cavaleiro das Cinzas na beira do penhasco contemplando o Eclipse e a Cidadela!
        saved_pos = player.pos.copy()
        saved_yaw = player.facing_yaw
        saved_state = player.state
        saved_walk = player.walk_cycle

        player.pos = Vec3(-1.15, 0.0, 0.55)
        player.facing_yaw = math.radians(162.0)  # Voltado para a Cidadela e o Eclipse
        player.state = PlayerState.IDLE
        # Faz a capa esvoaçar ao vento da montanha!
        player.walk_cycle = math.sin(self.time_accum * 3.2) * 0.45
        self.render_player(player)

        player.pos = saved_pos
        player.facing_yaw = saved_yaw
        player.state = saved_state
        player.walk_cycle = saved_walk

        # 7. Renderiza Brasas e Cinzas Voando pelo Penhasco
        self.render_particles_and_effects(particle_sys)

        # Restaura a neblina padrão da Catedral para quando o jogo começar
        gl.glFogfv(gl.GL_FOG_COLOR, (0.04, 0.045, 0.065, 1.0))
        gl.glFogf(gl.GL_FOG_DENSITY, 0.020)

