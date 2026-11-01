import pygame 
from os.path import join 
from os import walk
from pathlib import Path

path = Path(Path(__file__).parent).parent

WINDOW_WIDTH, WINDOW_HEIGHT = 1280,720 
TILE_SIZE = 64