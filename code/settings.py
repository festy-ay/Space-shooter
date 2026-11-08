import pygame 
from os.path import join 
from os import walk
from pathlib import Path
from random import randrange, uniform, choice, randint
import sys
import moderngl
import pygame


path = Path(Path(__file__).parent).parent

WINDOW_WIDTH_INIT, WINDOW_HEIGHT_INIT = 1368, 768
RENDER_SCALE = 1.0      # lower (for example 0.6) if the frame rate is poor; the picture is just stretched
SCROLL_SPEED = 0.05     # background scroll in screen heights per second
SHADER_FILE = "space_bg_blend.frag"   # between cartoon and realistic. Others: "space_bg_toon.frag" (full cartoon), "space_bg.frag" (realistic)



            # pygame.draw.polygon(self.overlay, (200, 220, 255, 255), [(ship_x, ship_y - 30), (ship_x - 22, ship_y + 24), (ship_x, ship_y + 10), (ship_x + 22, ship_y + 24)])