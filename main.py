# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///

import asyncio
import pygame

from func import *
from os.path import join
import zipfile
from random import randint, choice

async def main():

    class Turret(pygame.sprite.Sprite):
        def __init__(self, groups, parent):
            super().__init__(groups)
            self.overlay = parent
            self.original = pygame.transform.rotozoom(pygame.image.load(join('Spaceship', 'turret.png')).convert_alpha(), 90, 0.6)
            self.image = self.original
            self.rect = self.image.get_frect(center = parent.rect.center)
            self.direction = pygame.Vector2()
            self.angle = 0

        def shoot(self):
            shoot = self.rect.center
            Laser(laser_surf, shoot, (all_sprites, laser_sprites), self.direction, self.angle)

        def update(self, dt):
            # 1. Get the current mouse coordinates on the screen
            mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
            # 3. Calculate the distance (delta) between the mouse and the player
            self.direction = mouse_pos - pygame.Vector2(self.rect.center)
            self.direction = self.direction.normalize() if self.direction else self.direction
            # (The negative sign corrects for Pygame's inverted Y-axis where down is positive)
            _, angle_degrees = self.direction.as_polar()
            self.angle = -angle_degrees - 90
            self.image = pygame.transform.rotozoom(self.original, self.angle, 1)
            self.rect = self.image.get_frect(center = self.overlay.rect.center)

    class Player(pygame.sprite.Sprite):
        def __init__(self, groups):
            super().__init__(groups)
            self.image = pygame.transform.rotozoom(pygame.image.load(join('Spaceship', '1.png')).convert_alpha(), 0, 0.6)
            self.rect = self.image.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT))
            self.turret = Turret(groups, self)
            self.direction = pygame.math.Vector2()
            self.speed = 300
            self.boost = False
            self.life = 5

            # cooldowm
            self.can_shoot = True
            self.laser_shoot_time = 0
            self.cooldown_duration = 400

        def laser_timer(self):
            if not self.can_shoot:
                current_time = pygame.time.get_ticks()
                if current_time - self.laser_shoot_time >= self.cooldown_duration:
                    self.can_shoot = True

        def update(self, dt):
            keys = pygame.key.get_pressed()
            self.direction.x = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a]) if 0 <= self.rect.centerx <= WINDOW_WIDTH else 0
            self.direction.y = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w]) #if 0 >= self.rect.centery >= WINDOW_HEIGHT else 0
            self.direction = self.direction.normalize() if self.direction else self.direction
            self.rect.center += self.direction * self.speed * dt

            mouse = pygame.mouse.get_pressed()
            if (keys[pygame.K_SPACE] or mouse[0]) and self.can_shoot:
                self.turret.shoot()
                self.can_shoot = False
                self.laser_shoot_time = pygame.time.get_ticks()
                laser_sound.play()

            self.laser_timer()
            display_score(text=f'Life: {str(self.life)}', position=(200, 50), colour="#ffffff")

    class Star(pygame.sprite.Sprite):
        def __init__(self, groups, frames):
            super().__init__(groups)
            self.frames = frames
            self.frame_index = 0
            self.image = self.frames[0]
            self.rect = self.image.get_frect(center = (randint(0, WINDOW_WIDTH),randint(0, WINDOW_HEIGHT)))

        def update(self, dt):
            self.frame_index += 5 * dt
            self.image = self.frames[int(self.frame_index) % len(self.frames)]
            
    class Laser(pygame.sprite.Sprite):
        def __init__(self, surf, pos, groups, direction, angle):
            super().__init__(groups)
            self.image = pygame.transform.rotozoom(surf, angle, 1)
            self.direct = direction
            self.rect = self.image.get_frect(midbottom = pos)
            self.start_time = pygame.time.get_ticks()
            self.lifetime = 3000

        def update(self, dt):
            self.rect.center += self.direct * 400 * dt
            if pygame.time.get_ticks() - self.start_time >= self.lifetime:
                self.kill()

    class Meteor(pygame.sprite.Sprite):
        def __init__(self, frames, pos, groups):
            super().__init__(groups)
            self.frames = frames
            self.frame_index = 0
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_frect(center = pos)
            self.speed = randint(400,500)

        def update(self, dt):
            self.frame_index += 5 * dt
            self.image = self.frames[int(self.frame_index) % len(self.frames)]
            self.rect.centery += 1 * self.speed * dt
            
            if self.rect.bottom < 0:
                self.kill()

    class AnimatedExploaaion(pygame.sprite.Sprite):
        def __init__(self, frames, pos, groups):
            super().__init__(groups)
            self.frames = frames
            self.frame_index = 0
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_frect(center = pos)
            explosion_sound.play()

        def update(self, dt):
            self.frame_index += 5 * dt
            try: self.image = self.frames[int(self.frame_index)]
            except IndexError: self.kill()

    def collisions():
        collision_sprites = pygame.sprite.spritecollide(player, metero_sprites, True, pygame.sprite.collide_mask)
        if collision_sprites:
            damage_sound.play()
            player.life -= 1

            if player.life == 0:
                while True:
                    display_score('     GAME OVER!!!\nPress space or left click to exit!', (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2), '#ff5050', fontB)
                    pygame.display.flip()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()):
                            pygame.quit(); sys.exit(); break

        for laser in laser_sprites:
            collided_sprites = pygame.sprite.spritecollide(laser, metero_sprites, True, pygame.sprite.collide_mask)
            if collided_sprites: laser.kill(); AnimatedExploaaion(meteor_explosoin_frames, laser.rect.midtop, all_sprites)
        
    #general setup
    pygame.init()
    WINDOW_WIDTH, WINDOW_HEIGHT = 1368, 768
    display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption('Shooter')
    clock = pygame.time.Clock()

    def display_score(text='', position=(WINDOW_WIDTH / 2, WINDOW_HEIGHT - 50), colour=(240,240,240), Font=None):
        current_time = pygame.time.get_ticks()
        text = f'Current Time: {current_time // 1000}.{(str(current_time))[1:]}' if not text else text
        text_surf = font.render(text, True, colour) if Font is None else Font.render(text, True, colour)
        text_rect = text_surf.get_frect(midbottom = position)
        display_surface.blit(text_surf, text_rect)
        pygame.draw.rect(display_surface, colour, text_rect.inflate(20,15).move(0,-1.5), 5, 10 )

    async def url_get(url:str, display=display_surface):
        file_name = url.split('/')[-1]
        file_type = file_name.split('.')[-1]
        audio, photo = ['wav', 'ogg', '.mp3'], ['png', 'jpeg']

        buffer = await get_assets(url, display)
        if file_type in audio: return pygame.mixer.Sound(buffer)
        elif file_type in photo: return pygame.image.load(buffer, file_name).convert_alpha()
        else: return buffer

    def log_text(text, flush=False, disp=display_surface):
        log(text, disp, flush)

    # imports
    star_frames = [pygame.transform.rotozoom(pygame.image.load(join('orb_frames', f'orb_0{i+1}.png')).convert_alpha(), 0, 0.7) for i in range(12)]

    # Meteor and Laser
    meteor_surfs = (
        [pygame.transform.rotozoom(pygame.image.load(join('Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.7) for i in range(8)],
        [pygame.transform.rotozoom(pygame.image.load(join('Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.8) for i in range(8)],
        [pygame.transform.rotozoom(pygame.image.load(join('Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.9) for i in range(8)],
        [pygame.transform.rotozoom(pygame.image.load(join('Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.0) for i in range(8)],
    )
    meteor_explosoin_frames = [pygame.transform.rotozoom(pygame.image.load(join('Sun', f'0{i+1}.png')).convert_alpha(), 0, 0.4) for i in range(8)]
    laser_surf = await url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/images/laser.png')

    # Font
     # 1 Download Font
    try: zip_buffer = await url_get('https://font.download/dl/font/times-new-roman.zip')
    except Exception as e:
        log_text(e); sys.exit()
     # 2. Open the ZIP container entirely in memory
    with zipfile.ZipFile(zip_buffer) as archive:
        # 3. Read the specific .ttf file out of the zip archive as raw bytes
        log_text("Extracting font inside RAM...")
        font_bytes = archive.read('times.ttf')
     # 3 Make sure Pygame's font system is running
    if not pygame.font.get_init(): pygame.font.init()
     # 4. Wrap the extracted font bytes into a fresh BytesIO buffer for Pygame
    font = pygame.font.Font(io.BytesIO(font_bytes), 20)
    fontB = pygame.font.Font(io.BytesIO(font_bytes), 100)

    # Sounds
    log_text("Initializing pygame mixer...")
    pygame.mixer.init()

    game_music = await url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/game_music.wav')

    laser_sound = await url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/laser.wav')
    laser_sound.set_volume(0.5)

    explosion_sound = await url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/explosion.wav')
    explosion_sound.set_volume(0.5)

    damage_sound = await url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/damage.ogg')
    damage_sound.set_volume(0.5)

    game_music.play(loops= -1)

    # Sprites
    all_sprites = pygame.sprite.Group()
    metero_sprites = pygame.sprite.Group()
    laser_sprites = pygame.sprite.Group()
    for i in range(20):
        Star(all_sprites, star_frames)
    player = Player(all_sprites)


    # custom events -> meteor event
    meteor_event = pygame.event.custom_type()
    pygame.time.set_timer(meteor_event, 500)

    running = True
    while running:
        dt = clock.tick() / 1000
        # log_text(clock.get_fps())
        # event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == meteor_event:
                x = randint(0, WINDOW_WIDTH)
                Meteor(choice(meteor_surfs), (x,-100), (all_sprites, metero_sprites))


        #draw the game
        display_surface.fill('#000000')
        all_sprites.draw(display_surface)
        all_sprites.update(dt)
        collisions()
        display_score()

        pygame.display.update()
        await asyncio.sleep(0)  # required: lets the browser breathe

asyncio.run(main())
pygame.quit()