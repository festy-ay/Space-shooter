from .settings import pygame, randint

class Meteor(pygame.sprite.Sprite):
    def __init__(self, frames, pos, groups):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_frect(center = pos)
        self.speed = randint(400,500)

    def update(self, dt, _):
        self.frame_index += 8 * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]
        self.rect.centery += 1 * self.speed * dt
        
        if self.rect.bottom < 0:
            self.kill()

class Orb(pygame.sprite.Sprite):
    def __init__(self, frames, pos, groups):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.mask = pygame.mask.from_surface(self.frames[2])
        self.rect = self.image.get_frect(center = pos)
        self.speed = randint(100,250)

    def update(self, dt, _):
        self.frame_index += 8 * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]
        self.rect.centery += 1 * self.speed * dt
        
        if self.rect.bottom < 0:
            self.kill()

class Laser(pygame.sprite.Sprite):
    def __init__(self, surf, pos, groups, speed, current_time):
        super().__init__(groups)
        self.image = surf
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_frect(midbottom = pos)
        self.start_time = current_time
        self.lifetime = 3000
        self.speed = speed

    def update(self, dt, current_time):
        self.rect.y -= self.speed * dt
        if current_time - self.start_time >= self.lifetime:
            self.kill()

class AnimatedExplosion(pygame.sprite.Sprite):
    def __init__(self, frames, pos, groups):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_frect(center = pos)

    def update(self, dt, _):
        self.frame_index += 10 * dt
        try: self.image = self.frames[int(self.frame_index)]
        except IndexError: self.kill()

class LevelUpIndicator(pygame.sprite.Sprite):
    def __init__(self, font, groups, current_time, level):
        super().__init__(groups)
        self.font = font
        self.text = f'LEVEL {level}!!!'
        self.extra_text_colour = '#ff0000'
        self.frame_index = 0
        self.image = self.font.render('LEVEL UP!!!', True, self.extra_text_colour)
        self.pos = pygame.display.get_window_size()[0] // 2, pygame.display.get_window_size()[1] // 2
        self.rect = self.image.get_frect(center = self.pos)
        self.duration = 1500
        self.start_time = current_time

    def update(self, dt, current_time):
        self.frame_index += 8 * dt
        self.extra_text_colour = '#ffff00' if int(self.frame_index) % 2 else '#ff0000'
        self.image = self.font.render(self.text, True, self.extra_text_colour)
        if current_time - self.start_time >= self.duration:
            self.kill()
