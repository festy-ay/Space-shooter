import io
import urllib.request
import urllib.error
import pygame
import sys
from os.path import join

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
    # if end == '\n' and not end_prev_state: log_lines.append('')
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
            if event.type == pygame.QUIT: sys.exit()
    pygame.display.update()

def get_assets(url, display):
    # 1. Real raw direct link to the audio file
    RAW_AUDIO_URL = url
    file_name = url.split('/')[-1]

    log(f"Getting {file_name}...", display)

    # 2. Add a standard User-Agent header so GitHub doesn't reject urllib
    req = urllib.request.Request(
        RAW_AUDIO_URL, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )

    audio_bytes = None

    try:
        # 3. Request data over the network with an explicit timeout limit
        with urllib.request.urlopen(req, timeout=30) as response:
            # Get the total file size from headers (in bytes)
            total_size = int(response.headers.get('Content-Length', 0))
            
            audio_byte_stream = io.BytesIO()
            downloaded = 0
            block_size = 65536  # Download in 64KB chunks


            log(f"Downloading {file_name}...", display)
            
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                
                downloaded += len(buffer)
                audio_byte_stream.write(buffer)
                
                # Calculate progress bar details if server provided total size
                if total_size > 0:
                    percent = downloaded / total_size
                    bar_length = 30
                    filled_length = int(bar_length * percent)
                    # Create visual progress bar layout: [████████░░░░░░░░] 50.0%
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    # \r forces the cursor to return to the start of the line
                    log(f"\r[{bar}] {percent*100:.1f}% ({downloaded / (1024*1024):.1f} MB/{total_size / (1024*1024):.1f} MB)", display, flush=True)
                else:
                    # Fallback if server doesn't provide file size
                    log(f"\rDownloaded: {downloaded / (1024*1024):.1f} MB...", display, flush=True)
            
            log(f"\nSuccessfully loaded {file_name} into memeory!", display)
            audio_bytes = audio_byte_stream.getvalue()

    except urllib.error.URLError as e:
        log(f"\n❌ Network error occurred: {e.reason}", display)
        log("If you have an active network, try closing and reopening your browser and clear its network cache.", display)
    except Exception as e:
        log(f"\n❌ Unexpected error: {e}", display)

    return io.BytesIO(audio_bytes)
