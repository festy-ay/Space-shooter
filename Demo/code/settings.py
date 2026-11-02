import pygame 
from os.path import join 
from os import walk
from pathlib import Path
from random import randrange, uniform, choice, randint
import pygame
from random import randint, choice


path = Path(__file__).parent
TILE_FILE = join(path, "space_bg_tile.png")
WINDOW_WIDTH, WINDOW_HEIGHT = 1368, 768
SCROLL_SPEED = 220     # background scroll in screen heights per second
