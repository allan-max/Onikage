# Onikage — Ashen Souls 3D

Jogo **Soulslike 3D em terceira pessoa** escrito do zero em **Python + OpenGL**, sem engine comercial. Matemática 3D, colisões, câmera orbital com lock-on, máquina de estados de combate, i-frames, parry, poise/stagger, partículas, áudio sintetizado e HUD foram todos programados à mão.

## Destaques

- **Combate Soulslike**: ataques leves e pesados, rolamento com i-frames, bloqueio, parry, stamina e poise/stagger.
- **Câmera orbital** com **lock-on** em inimigos e chefe, e camera shake nos impactos.
- **Chefe Malakor** com duas fases (fica mais rápido e agressivo abaixo de 55% de vida), ataques variados e ondas de choque.
- **Guardiões Vazios** (inimigos comuns) que renascem ao descansar na fogueira.
- **Fogueira**: restaura vida e Estus, permite subir de nível (Vigor, Fôlego, Força) e restaurar o mundo.
- **Poça de almas**: ao morrer, as almas ficam no chão e podem ser recuperadas.
- **3 classes iniciais**: Cavaleiro Errante, Guerreiro Colossal e Lâmina das Cinzas.
- **Áudio procedural**: todos os efeitos sonoros são gerados matematicamente em tempo real com NumPy — nenhum arquivo `.wav`/`.ogg`.
- **Tela inicial** com paisagem 3D animada.

## Requisitos

- Python 3.10+
- [pygame](https://www.pygame.org/)
- [PyOpenGL](https://pypi.org/project/PyOpenGL/)
- [NumPy](https://numpy.org/)

```bash
pip install pygame PyOpenGL numpy
```

## Como jogar

```bash
git clone https://github.com/allan-max/Onikage.git
cd Onikage
python main.py
```

No Windows, também dá para dar dois cliques em `Jogar_Soulslike.bat`.

## Controles

| Ação | Tecla |
|---|---|
| Mover | `W` `A` `S` `D` |
| Câmera | Mouse |
| Ataque leve | Botão esquerdo |
| Ataque pesado | `F` ou `Q` + botão esquerdo |
| Bloquear | Botão direito (segurar) |
| Parry | `C` |
| Rolar / esquivar | `Espaço` |
| Correr | `Shift` |
| Lock-on | `Tab` ou botão do meio |
| Beber Estus | `R` |
| Interagir (fogueira / recuperar almas) | `E` |
| Liberar / capturar mouse | `Esc` |
| Mostrar controles | `F1` |
| Voltar à tela inicial | `F2` |

**Menu da fogueira:** `1` Vigor · `2` Fôlego · `3` Força · `4` Restaurar o mundo · `E`/`Esc` sair.

## Estrutura do projeto

```
Onikage/
├── main.py               # Loop principal, estados do jogo, entrada e colisões de combate
├── Jogar_Soulslike.bat   # Atalho para rodar no Windows
├── engine/
│   ├── math3d.py         # Vetores, colisores cilíndricos, interseções
│   ├── camera.py         # Câmera orbital em terceira pessoa + lock-on + shake
│   ├── renderer.py       # Renderizador OpenGL (personagens, arena, cenário)
│   ├── particles.py      # Sistema de partículas 3D e textos flutuantes
│   └── audio.py          # Sintetizador de efeitos sonoros procedural
├── game/
│   ├── entities.py       # Jogador, inimigos e o chefe Malakor (máquinas de estado)
│   └── world.py          # Arena, fogueira e poça de almas
└── ui/
    └── hud.py            # HUD: barras de vida/stamina, banners, menus
```
