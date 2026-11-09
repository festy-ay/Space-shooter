# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///

import asyncio
import pygame
from Code.func import *
from Code.settings import *
from Code.player import Player
from Code.sprites import *
from random import randint, choice
import os, tempfile


class Game():
    def __init__(self):
        pygame.init()
        self.tile_files = TILE_FILES

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = log_font
        self.running = False
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)

        # ---------------------------------------------------------------- game-ish state
        self.scroll_speed = SCROLL_SPEED
        self.offset = 0.0
        self.time_spent = 0.0
        self.dificulty = 1
        self.accelerated = False
        self.reference_time = 0
        self.kills = 0; self.laser_speed = 600
        self.high_score = 0
        self.next_level = 20

        # sprites
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.orb_sprites = pygame.sprite.Group()

        self.player = Player((WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.meteor_surfs = (
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.8) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.9) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.0) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.1) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.2) for i in range(8)],
        )
        self.meteor_explosoin_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Sun', f'0{i+1}.png')).convert_alpha(), 0, 0.45) for i in range(8)]
        self.orb_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'orb_frames', f'orb_0{i+1}.png')).convert_alpha(), 23, 0.7) for i in range(12)]

        # custom events -> meteor event
        self.meteor_event = pygame.event.custom_type()
        self.meteor_time = 1100
        self.orb_event = pygame.event.custom_type()
        self.orb_time = 30000
        pygame.time.set_timer(self.meteor_event, self.meteor_time)
        pygame.time.set_timer(self.orb_event, self.orb_time)

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
        try:
            self.laser_surf = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/images/laser.png')

            # Sounds
            log("Initializing pygame mixer...", self.screen)
            pygame.mixer.init()

            self.laser_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/laser.wav')
            self.laser_sound.set_volume(0.5)

            self.explosion_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/explosion.wav')
            self.explosion_sound.set_volume(0.5)

            self.damage_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/damage.ogg')
            self.damage_sound.set_volume(0.5)

            self.game_music = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/game_music.wav')
            self.game_music.set_volume(0.3)
        except Exception as e:
            log(f"Error importing assets: {type(e).__name__} {e}", self.screen)
            log("Restart the game to download assets or continue without some assets...", self.screen)

        # After imports, let there be a response before the game starts
        log('Click or press space to begin...', self.screen)
        while not self.running:
            for _ in pygame.event.get():
                if pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()): return
            await asyncio.sleep(0)              # required by pygbag; harmless on desktop

    async def setup(self, width=WINDOW_WIDTH):
        """Load the background tile and scale it to the window width (once, at start-up)."""
        tile = pygame.image.load(choice(self.tile_files)).convert()           # convert() makes blitting much faster
        if tile.get_width() != width:
            scale = width / tile.get_width()
            tile = pygame.transform.smoothscale(tile, (width, round(tile.get_height() * scale)))
        self.tile = tile

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
            if hasattr(self, 'game_music'): self.game_music.stop()
        except Exception as e:
            print("music stop:", e)
        try:
            pygame.mixer.stop()   # stops every Sound that is playing
        except Exception as e:
            print("mixer stop:", e)

    async def collisions(self):
        collision_sprites = pygame.sprite.spritecollide(self.player, self.meteor_sprites, True, pygame.sprite.collide_mask)
        if collision_sprites:
            if hasattr(self, 'damage_sound'): self.damage_sound.play()
            self.player.life -= 1

            if self.player.life == 0:
                text = pygame.font.Font(join(path,'Font', 'DejaVuSans.ttf'), 70).render('     GAME OVER!!!\nPress space to restart or esc to exit!', True, (255, 150, 150), '#003030')
                rect = text.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
                pygame.draw.rect(self.screen, '#003030', rect.inflate(20,15).move(0,-1.5), 0, 20 )
                self.screen.blit(text, rect)
                pygame.display.flip()
                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): return False
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_SPACE]: return True
                    await asyncio.sleep(0)              # required by pygbag; harmless on desktop

        collision_sprites = pygame.sprite.spritecollide(self.player, self.orb_sprites, True, pygame.sprite.collide_mask)
        if collision_sprites:
            if hasattr(self, 'damage_sound'): self.damage_sound.play()
            self.player.life += 1
            self.player.life = min(self.player.life, 5)

        for laser in self.laser_sprites:
            collided_sprites = pygame.sprite.spritecollide(laser, self.meteor_sprites, True, pygame.sprite.collide_mask)
            if collided_sprites:
                laser.kill()
                self.kills += 1
                if self.kills == self.next_level:
                    new_level = self.player.level + 1
                    if new_level > self.player.level:
                        self.player.level = new_level
                        self.laser_speed = 600 + (self.player.level * 100)
                        self.player.cooldown_duration -= self.player.level * 10 if self.player.cooldown_duration > 100 else 0
                        self.next_level += 30 + (self.player.level * 5)
                AnimatedExplosion(self.meteor_explosoin_frames, laser.rect.midtop, self.all_sprites)
                if hasattr(self, 'explosion_sound'): self.explosion_sound.play()

    async def run(self, new=False):
        if new:
            await self.imports()
            if not hasattr(self, 'laser_surf'): self.laser_surf = pygame.Surface((8, 50), pygame.SRCALPHA); self.laser_surf.fill("#f0a0f0")
            if hasattr(self, 'game_music'): self.game_music.play(-1)


            # display about game
            clear_log()
            log("""         '__'


This is a space shooter game *_*

Controls:
- Move the mouse to move the spaceship sideways
- Press W, Up Arrow, Left Ctrl or Left Click to accelerate
- Press Space or Left click to shoot
- Press Esc to exit the game

Rules:
-The difficulty increases every minute and the max difficulty is 9
-The max health of the player is 5
-Shoot meteors and destroy them to score points
-There are health orbs that resembles a blue shining star, they add 1 health to the player,
    they fall slower than meteors when they appear but they are visually hard to recognise
    and can be mistaken for a blue star (part of the shader used as background for the game)
    the main difference is that the healing orb is animated while the shader's blue star isn't
-When the player level increases, the laser speed also increases
-The player level increases by destroying meteors and the requred number of meteors to be
    destroyed to enter the next level is indicated at the top left section of the screen under 'Next Level'
- The max player level is 10

Note that if you do not start scoring points from difficulty level 1, the laser speed and cooldown would remain
    slower that it should and the game becomes harder as the difficulty level increses every minute irrespective
    of the player's own level. Enjoy the Game!

Click anywhere or press space to continue...
    """, self.screen)
            current_time = pygame.time.get_ticks()
            while not self.running:
                for event in pygame.event.get():
                    if pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()) and pygame.time.get_ticks() - current_time > 2000: self.running = True
                await asyncio.sleep(0)              # required by pygbag; harmless on desktop

        await self.setup(); self.reference_time = pygame.time.get_ticks() / 1000
        while self.running:
            dt = self.clock.tick() / 1000.0
            self.time_spent = pygame.time.get_ticks() / 1000 - self.reference_time

            # set game dificulty
            self.dificulty_ = int(min(9, 1 + (self.time_spent // 60)))
            if self.dificulty is not 'max' and self.dificulty_ != self.dificulty:
                self.dificulty = self.dificulty_
                self.meteor_time = (self.meteor_time + 100) * 2 / (self.dificulty + 1)
                pygame.time.set_timer(self.meteor_event, int(self.meteor_time))
                self.orb_time -= 5000 if self.dificulty < 5 else -10000
                pygame.time.set_timer(self.orb_event, int(self.orb_time))
                self.dificulty = self.dificulty if self.dificulty < 9 else 'max'

            # check game events
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): return True
                if event.type == self.meteor_event:
                    x = randint(0, WINDOW_WIDTH)
                    Meteor(choice(self.meteor_surfs), (x,-100),  (self.all_sprites, self.meteor_sprites))
                if event.type == self.orb_event:
                    x = randint(0, WINDOW_WIDTH)
                    Orb(self.orb_frames, (x,-100),  (self.all_sprites, self.orb_sprites))

            # set background gif scroll speed based on player input
            keys = pygame.key.get_pressed()
            mouse = pygame.mouse.get_pressed()
            if (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or mouse[2]) and not self.accelerated:
                self.scroll_speed = 500; self.accelerated = True; self.player.speed += 100
            elif not (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or mouse[2]) and self.accelerated:
                self.accelerated = False; self.player.speed -= 100; self.scroll_speed = 220

            self.all_sprites.update(dt)

            # player shooting
            if (keys[pygame.K_SPACE] or mouse[0]) and self.player.can_shoot:
                Laser(self.laser_surf, self.player.rect.center, (self.all_sprites, self.laser_sprites), self.laser_speed)
                self.player.can_shoot = False
                self.player.laser_shoot_time = pygame.time.get_ticks()
                if hasattr(self, 'laser_sound'): self.laser_sound.play()

            self.offset = (self.offset + self.scroll_speed * dt) % self.tile.get_height()
            self.draw_background(self.screen, self.tile, self.offset)

            # ---- your game goes on top of the background (a tiny ship and self.bullets as a demo)
            self.screen.blit(self.font.render(f"""{self.clock.get_fps():.0f} fps   High Score {self.high_score}
Controls: SPACE or Left Click to shoot; W, Up Arrow, Left Ctrl or Right Click to accelerate, Press esc to close the game
Game time: {self.time_spent / 60:.2f}mins   Dificulty level: {self.dificulty}   Next Level: {self.next_level} Meteors
Player life: {self.player.life}  Player Level: {self.player.level if self.player.level != 10 else 'max'}   Score: {self.kills}
""", True, "#eaff00"), (12, 10))
            self.all_sprites.draw(self.screen)

            if await self.collisions() == True: return False
            elif await self.collisions() == False: return True
            if self.player.life <= 0: return True

            pygame.display.flip()
            await asyncio.sleep(0)              # required by pygbag; harmless on desktop

    def reset(self):
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.player = Player((WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.running = True
        self.scroll_speed = SCROLL_SPEED
        self.offset = 0.0
        self.time_spent = 0.0
        self.dificulty = 1
        self.accelerated = False
        self.reference_time = 0
        self.high_score = self.kills if self.kills > self.high_score else self.high_score
        self.kills = 0; self.laser_speed = 600
        self.next_level = 20
        self.meteor_event = pygame.event.custom_type()
        self.meteor_time = 900
        self.orb_event = pygame.event.custom_type()
        self.orb_time = 30000
        pygame.time.set_timer(self.meteor_event, self.meteor_time)
        pygame.time.set_timer(self.orb_event, self.orb_time)

async def main():
    if __name__ == '__main__':
        game = Game()
        new = True
        while True:
            if await game.run(new):
                game.stop_all_audio(); game.screen.fill("#000000"); pygame.display.update(); break
            if new: new = False
            game.reset()
            await asyncio.sleep(0)

asyncio.run(main())
