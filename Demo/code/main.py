# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///

import asyncio
import pygame
from func import *
from settings import *
from player import Player
from sprites import *
from random import randint, choice
import os, tempfile


class Game():
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = log_font
        self.scroll_speed = SCROLL_SPEED
        self.tile = self.load_tile(WINDOW_WIDTH)
        self.offset = 0.0
        self.running = True

        # sprites
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.player = Player((WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.meteor_surfs = (
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.7) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.8) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.9) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.0) for i in range(8)],
        )
        self.meteor_explosoin_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'Sun', f'0{i+1}.png')).convert_alpha(), 0, 0.3) for i in range(8)]

        # custom events -> meteor event
        self.meteor_event = pygame.event.custom_type()
        pygame.time.set_timer(self.meteor_event, 500)

    async def url_get(self, url:str):
        file_name = url.split('/')[-1]
        file_type = file_name.split('.')[-1]
        audio, photo = ['wav', 'ogg', '.mp3'], ['png', 'jpeg']

        buffer = await get_assets(url, self.screen)
        if hasattr(buffer, "seek"):
            buffer.seek(0)
        data = buffer.read() if hasattr(buffer, "read") else bytes(buffer)
        log(f"bytes: {len(data)}", self.screen)

        path = os.path.join(tempfile.gettempdir(), file_name)
        with open(path, "wb") as f:
            f.write(data)
        log(f"saved to {path}", self.screen)

        try:
            if file_type in audio:
                return pygame.mixer.Sound(path)
            elif file_type in photo:
                surf = pygame.image.load(path)
                log(f"image loaded {surf.get_size()}", self.screen)
                return surf.convert_alpha()
            else:
                return io.BytesIO(data)
        except Exception as e:
            log(f"load failed: {type(e).__name__} {e}", self.screen)
            raise

    async def imports(self):
        self.laser_surf = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/images/laser.png')

        # Sounds
        log("Initializing pygame mixer...", self.screen)
        pygame.mixer.init()

        self.game_music = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/game_music.wav')
        self.game_music.set_volume(0.3)

        self.laser_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/laser.wav')
        self.laser_sound.set_volume(0.5)

        self.explosion_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/explosion.wav')
        self.explosion_sound.set_volume(0.5)

        self.damage_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/damage.ogg')
        self.damage_sound.set_volume(0.5)

        # After imports, let there be a response before the game starts
        log('Click or press space to begin...', self.screen)
        while not self.running:
            for event in pygame.event.get():
                if event.type == pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()): self.running = True

    def load_tile(self, width):
        """Load the background tile and scale it to the window width (once, at start-up)."""
        tile = pygame.image.load(TILE_FILE).convert()           # convert() makes blitting much faster
        if tile.get_width() != width:
            scale = width / tile.get_width()
            tile = pygame.transform.smoothscale(tile, (width, round(tile.get_height() * scale)))
        return tile

    def draw_background(self, screen, tile, offset):
        """Draw the tile scrolled down by `offset` pixels. The tile repeats, so any offset works.

        The tile must be at least as tall as the window (the supplied one is 3x taller)."""
        tile_h = tile.get_height()
        y = int(offset) % tile_h
        screen.blit(tile, (0, y - tile_h))      # the copy above: it fills the top part of the screen
        if y < screen.get_height():
            screen.blit(tile, (0, y))           # the copy below: only needed while it is still on screen

    def stop_all_audio(self):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.game_music.stop()
        except Exception as e:
            print("music stop:", e)
        try:
            pygame.mixer.stop()   # stops every Sound that is playing
        except Exception as e:
            print("mixer stop:", e)

    def collisions(self):
        collision_sprites = pygame.sprite.spritecollide(self.player, self.meteor_sprites, True, pygame.sprite.collide_mask)
        if collision_sprites:
            self.damage_sound.play()
            self.player.life -= 1

            if self.player.life == 0:
                text = pygame.font.Font(join(path,'Font', 'DejaVuSans.ttf'), 70).render('     GAME OVER!!!\nRestart to try again!!', True, (255, 150, 150), '#000000')
                rect = text.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
                self.screen.blit(text, rect)
                pygame.display.flip()
                return True

        for laser in self.laser_sprites:
            collided_sprites = pygame.sprite.spritecollide(laser, self.meteor_sprites, True, pygame.sprite.collide_mask)
            if collided_sprites: laser.kill(); AnimatedExploaaion(self.meteor_explosoin_frames, laser.rect.midtop, self.all_sprites); self.explosion_sound.play()

    async def run(self, new=False):
        if new:
            await self.imports()
            if hasattr(self, 'game_music'): self.game_music.play(-1)
        while self.running:
            dt = self.clock.tick() / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return True
                if event.type == self.meteor_event:
                    x = randint(0, WINDOW_WIDTH)
                    Meteor(choice(self.meteor_surfs), (x,-100),  (self.all_sprites, self.meteor_sprites))

            keys = pygame.key.get_pressed()
            if (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w]): self.scroll_speed = 500
            else: self.scroll_speed = 220

            mouse = pygame.mouse.get_pressed()
            self.all_sprites.update(dt)
            if (keys[pygame.K_SPACE] or mouse[0]) and self.player.can_shoot:
                Laser(self.laser_surf, self.player.rect.center, (self.all_sprites, self.laser_sprites))
                self.player.can_shoot = False
                self.player.laser_shoot_time = pygame.time.get_ticks()
                self.laser_sound.play()

            self.offset = (self.offset + self.scroll_speed * dt) % self.tile.get_height()
            self.draw_background(self.screen, self.tile, self.offset)

            # ---- your game goes on top of the background (a tiny ship and self.bullets as a demo)
            self.screen.blit(self.font.render(f"""{self.clock.get_fps():.0f} fps  Player life: {self.player.life}
Controls: SPACE or Left click to shoot, W Up Arrow or Left Ctrl to accelerate
""", True, (255, 255, 255, 255)), (12, 10))
            self.all_sprites.draw(self.screen)

            if self.collisions(): return

            pygame.display.flip()
            await asyncio.sleep(0)              # required by pygbag; harmless on desktop

    def reset(self):
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.player = Player((WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.running = True

async def main():
    if __name__ == '__main__':
        game = Game()
        new = True
        while True:
            await game.run(new); new = False
            game.screen.fill("#000000")
            game.screen.blit(game.font.render("Click or press space to continue"), (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
            while not (pygame.key.get_pressed()[pygame.K_SPACE] or pygame.mouse.get_just_pressed()): pass
            game.stop_all_audio()
            game.reset()
            await asyncio.sleep(0)

asyncio.run(main())
