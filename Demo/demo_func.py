import io
import pygame
from os.path import join
import platform

if not pygame.font.get_init(): pygame.font.init()
log_font = pygame.font.Font(join('Font', 'DejaVuSans.ttf'), 20)
log_lines = []
end_prev_state = ''

# Generated using google.com/ai and modified
def log(text, display: pygame.Surface, flush=False, log_lines=log_lines):
    global end_prev_state
    end = '' if flush else '\n'
    print(text, end=end, flush=flush) # still goes to the console
    if flush and not end_prev_state: log_lines.pop()
    end_prev_state = end
    log_lines.append(text)
    if len(log_lines) > 8: log_lines = log_lines[-8:] # keep only the last 8 lines
    display.fill('#000000')
    draw_log(display)

def draw_log(screen: pygame.Surface, log_lines=log_lines):
    y = 10
    for line in log_lines:
        screen.blit(log_font.render(line.strip(), True, (255, 255, 255)), (10, y))
        y += 24
        for event in pygame.event.get():
            if event.type == pygame.QUIT: break
    pygame.display.update()

async def get_assets(url: str, display) -> pygame.Surface:
    file = url.split('/')[-1]
    try:
        log(f'Downloading {file}', display)
        async with platform.fopen(url, "rb") as source:
            data = source.read()
        log(f"Downloaded {len(data)} bytes from {url}", display)
        return io.BytesIO(data)
    except Exception as e:
        log(f"Downloading {file} failed!\n{e}", display)