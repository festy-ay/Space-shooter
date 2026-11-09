import pygame 
from os.path import join 
from os import walk
from pathlib import Path
from random import randrange, uniform, choice, randint
import pygame
from random import randint, choice


path = Path(__file__).parent.parent
TILE_FILES = [x for x in walk(join(path, "Shader Gif Tiles"))][-1][-1]
TILE_FILES = [join(path, "Shader Gif Tiles", x) for x in TILE_FILES if x.endswith('.png')]
WINDOW_WIDTH, WINDOW_HEIGHT = 1368, 768
SCROLL_SPEED = 220     # background scroll in screen heights per second
