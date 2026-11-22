from .settings import path, sys, pygame, join, asyncio
import io

IS_WEB = sys.platform == "emscripten"
if not IS_WEB:
    import urllib.request, urllib.error, ssl
    from .settings import moderngl
else: import platform


if not pygame.font.get_init(): pygame.font.init()
log_font = pygame.font.Font(join(path,'Font', 'DejaVuSans.ttf'), 20)
log_lines = []
end_prev_state = ''

def clear_log(logs=log_lines):
    logs.clear()

# Generated using google.com/ai and modified
def log(text, display, flush=False, log_lines=log_lines):
    global end_prev_state
    end = '' if flush else '\n'
    print(text, end=end, flush=flush) # still goes to the console
    if flush and not end_prev_state: log_lines.pop()
    end_prev_state = end
    log_lines.append(text)
    if IS_WEB: display.screen.fill('#000000')
    else: display.overlay.fill('#000000')
    draw_log(display)

def draw_log(screen: pygame.Surface, log_lines=log_lines):
    y = 10
    for line in log_lines:
        screen.displayer(log_font.render(line.strip(), True, (255, 255, 255)), (10, y), update=False)
        y += 24
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
    pygame.display.flip()

async def get_assets(url, display):
    if IS_WEB:
        file = url.split('/')[-1]
        try:
            log(f'Downloading {file}', display)
            async with asyncio.timeout(50):  # 50-second limit
                async with platform.fopen(url, "rb") as source:
                    data = source.read()
                log(f"Downloaded {len(data)} bytes from {url}", display)
                return io.BytesIO(data)
        except TimeoutError:
            log(f"Attempt {file} timed out for {url}", display)
        except Exception as e:
            log(f"Downloading {file} failed!\n{e}", display)
    else:
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
            with urllib.request.urlopen(req, timeout=15) as response:
                # Get the total file size from headers (in bytes)
                total_size = int(response.headers.get('Content-Length', 0))
                
                audio_byte_stream = io.BytesIO()
                downloaded = 0
                block_size = 65536  # Download in 64KB chunks


                log(f"Downloading {file_name}...", display)
                
                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: sys.exit()

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

            return io.BytesIO(audio_bytes)

        except urllib.error.URLError as e:
            # If it fails specifically due to missing Windows PyInstaller certs, bypass it
            if "CERTIFICATE_VERIFY_FAILED" in str(e.reason):
                log('Certificate verification failed, using unverified certificate!', display)
                unverified_context = ssl._create_unverified_context()
                with urllib.request.urlopen(req, context=unverified_context, timeout=15) as response:
                    # Get the total file size from headers (in bytes)
                    total_size = int(response.headers.get('Content-Length', 0))
                    
                    audio_byte_stream = io.BytesIO()
                    downloaded = 0
                    block_size = 65536  # Download in 64KB chunks


                    log(f"Downloading {file_name}...", display)
                    
                    while True:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT: sys.exit()

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

                return io.BytesIO(audio_bytes)

            log(f"\n❌ Network error occurred: {e.reason}", display)
            log("If you have an active network, try closing and reopening your browser and clear its network cache.", display)
        except Exception as e:
            log(f"\n❌ Unexpected error: {e}", display)
