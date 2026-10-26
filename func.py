import io
import urllib.request
import urllib.error
import pygame
import sys

# Generated using google.com/ai and modified
def get_audio(url, audio=True):
    # 1. Real raw direct link to the audio file
    RAW_AUDIO_URL = url
    file_name = url.split('/')[-1]

    print(f"Getting {file_name}...")

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

            print(f"Downloading {file_name}...")
            
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
                    print(f"\r[{bar}] {percent*100:.1f}% ({downloaded / (1024*1024):.1f} MB)", end="", flush=True)
                else:
                    # Fallback if server doesn't provide file size
                    print(f"\rDownloaded: {downloaded / (1024*1024):.1f} MB...", end="", flush=True)
            
            print(f"\nSuccessfully loaded {file_name} into memeory!")
            audio_bytes = audio_byte_stream.getvalue()

    except urllib.error.URLError as e:
        print(f"\n❌ Network error occurred: {e.reason}")
        print("If you have an active network, try closing and reopening your browser and clear its network cache.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

    # 4. If bytes are safely stored in our variable, initialize and play
    if audio_bytes and audio:        
        # Wrap bytes inside an in-memory buffer array
        audio_buffer = io.BytesIO(audio_bytes)
        
        # Load into Sound object directly
        return pygame.mixer.Sound(audio_buffer)
    elif audio_bytes and not audio: return io.BytesIO(audio_bytes)
