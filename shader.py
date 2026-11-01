"""
Random procedural space background (nebula, stars, big stars, planets) behind a tiny pygame shooter demo.

Install:  pip install pygame-ce moderngl numpy
Run:      python space_demo.py            (random seed)
          python space_demo.py 12345      (a specific seed, to get the same sky again)
Keep space_bg_blend.frag in the same folder as this file (the other two shader files are optional).

Controls:
  Mouse            move the ship, hold left button to shoot
  W / Up           fly faster (background scrolls faster)
  A, D / Left, Right   drift the camera sideways
  R                new random sky
  [ and ]          less / more cartoon (needs space_bg_blend.frag)
  S                save the current background as space_bg_<seed>.png (without the ship)
  Esc              quit
"""
import random
import sys
from pathlib import Path

import moderngl
import pygame

W, H = 1280, 720
RENDER_SCALE = 1.0      # lower (for example 0.6) if the frame rate is poor; the picture is just stretched
SCROLL_SPEED = 0.05     # background scroll in screen heights per second
SHADER_FILE = "space_bg_blend.frag"   # between cartoon and realistic. Others: "space_bg_toon.frag" (full cartoon), "space_bg.frag" (realistic)

seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randrange(1, 2 ** 31 - 1)
print("seed:", seed)

# ---------------------------------------------------------------- window + GL context
pygame.init()
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
pygame.display.set_mode((W, H), pygame.OPENGL | pygame.DOUBLEBUF)
pygame.display.set_caption("Random space background")
ctx = moderngl.create_context()
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 26)

# ---------------------------------------------------------------- shaders
VERT = """
#version 330
in vec2 in_pos;
out vec2 uv;
void main() {
    uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

BLIT_FRAG = """
#version 330
uniform sampler2D tex;
in vec2 uv;
out vec4 fragColor;
void main() { fragColor = texture(tex, uv); }
"""

bg_prog = ctx.program(vertex_shader=VERT, fragment_shader=Path(__file__).with_name(SHADER_FILE).read_text())
blit_prog = ctx.program(vertex_shader=VERT, fragment_shader=BLIT_FRAG)

import numpy as np  # noqa: E402  (only needed for the quad vertices)

quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
bg_vao = ctx.vertex_array(bg_prog, [(quad, "2f", "in_pos")])
blit_vao = ctx.vertex_array(blit_prog, [(quad, "2f", "in_pos")])

# ---------------------------------------------------------------- render targets
rw, rh = int(W * RENDER_SCALE), int(H * RENDER_SCALE)
scene_tex = ctx.texture((rw, rh), 3)
scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
scene_fbo = ctx.framebuffer(color_attachments=[scene_tex])

overlay = pygame.Surface((W, H), pygame.SRCALPHA)       # normal pygame drawing goes here
overlay_tex = ctx.texture((W, H), 4)
overlay_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

bg_prog["resolution"].value = (rw, rh)
blit_prog["tex"].value = 0

# ---------------------------------------------------------------- game-ish state
scroll = [0.0, 0.0]
bullets = []            # [x, y]
shoot_timer = 0.0
save_requested = False
toon = 0.4              # 0 = realistic-ish, 1 = full cartoon (change live with [ and ])
running = True

while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            seed = random.randrange(1, 2 ** 31 - 1)
            print("seed:", seed)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_s:
            save_requested = True
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            step = 0.05 if event.key == pygame.K_RIGHTBRACKET else -0.05
            toon = max(0.0, min(1.0, toon + step))

    keys = pygame.key.get_pressed()
    boost = 1.0 + 50.0 * (1 if (keys[pygame.K_UP] or keys[pygame.K_w]) else 0)
    scroll[1] += SCROLL_SPEED * boost * dt
    scroll[0] += ((1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0)
                  - (1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else 0)) * dt

    # ---- 1. run the background shader
    bg_prog["time"].value = pygame.time.get_ticks() / 1000.0
    bg_prog["seed"].value = seed
    bg_prog["scroll"].value = (scroll[0], scroll[1])
    if "toon" in bg_prog:
        bg_prog["toon"].value = toon

    scene_fbo.use()
    ctx.disable(moderngl.BLEND)
    bg_vao.render(moderngl.TRIANGLE_STRIP)

    if save_requested:
        data = scene_fbo.read(components=3)
        img = pygame.image.frombytes(data, (rw, rh), "RGB", True)    # True = flip, OpenGL rows start at the bottom
        filename = f"space_bg_{seed}.png"
        pygame.image.save(img, filename)
        print("saved", filename)
        save_requested = False

    # ---- 2. stretch it over the window
    ctx.screen.use()
    scene_tex.use(0)
    blit_vao.render(moderngl.TRIANGLE_STRIP)

    # ---- 3. draw the "game" with normal pygame calls on a transparent layer
    mx, _ = pygame.mouse.get_pos()
    ship_x, ship_y = mx, H - 80
    shoot_timer -= dt
    if pygame.mouse.get_pressed()[0] and shoot_timer <= 0:
        bullets.append([ship_x, ship_y - 30])
        shoot_timer = 0.12
    bullets = [[x, y - 900 * dt] for x, y in bullets if y > -20]

    overlay.fill((0, 0, 0, 0))
    for x, y in bullets:
        pygame.draw.line(overlay, (255, 240, 120, 255), (x, y), (x, y + 14), 3)
    pygame.draw.polygon(overlay, (200, 220, 255, 255),
                        [(ship_x, ship_y - 30), (ship_x - 22, ship_y + 24), (ship_x, ship_y + 10), (ship_x + 22, ship_y + 24)])
    hud = font.render(f"seed {seed}   {clock.get_fps():.0f} fps   R = new sky   S = save PNG   [ ] = cartoon level {toon:.2f}",
                      True, (255, 255, 255, 255))
    overlay.blit(hud, (12, 10))

    overlay_tex.write(pygame.image.tobytes(overlay, "RGBA", True))
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
    overlay_tex.use(0)
    blit_vao.render(moderngl.TRIANGLE_STRIP)

    pygame.display.flip()

pygame.quit()