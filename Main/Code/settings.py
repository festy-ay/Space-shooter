from os.path import join 
from os import walk
from pathlib import Path
from random import randrange, uniform, choice, randint
import sys
if not sys.platform == "emscripten": import moderngl
import pygame
import asyncio


path = Path(Path(__file__).parent).parent

TILE_FILES = [x for x in walk(join(path, "Shader"))][-1][-1]
TILE_FILES = [join(path, "Shader", x) for x in TILE_FILES if x.endswith('.png')]
WINDOW_WIDTH_INIT, WINDOW_HEIGHT_INIT = 1368, 768
RENDER_SCALE = 1.0      # lower (for example 0.6) if the frame rate is poor; the picture is just stretched
SCROLL_SPEED = 0.05     # background scroll in screen heights per second
SHADER_FILE = "space_bg_blend.frag"
SHADER_UNIT = WINDOW_HEIGHT_INIT   # window pixels that equal one shader unit
SHADER_MAX_PIXELS = WINDOW_WIDTH_INIT * WINDOW_HEIGHT_INIT
