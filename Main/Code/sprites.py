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
        
        if self.rect.top > pygame.display.get_window_size()[1]:
            self.kill()

class Orb(Meteor):
    def __init__(self, frames, pos, groups):
        super().__init__(frames, pos, groups)
        self.mask = pygame.mask.from_surface(self.frames[2])
        self.speed = randint(100,250)

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

class WelcomeDisplay(pygame.sprite.Sprite):
    def __init__(self, groups, frames, current_time, pos):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_frect(center = pos)
        self.duration = 1500
        self.start_time = current_time

    def update(self, dt, current_time):
        self.frame_index += 8 * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]
        if current_time - self.start_time >= self.duration:
            self.kill()

class LevelUpIndicator(WelcomeDisplay):
    def __init__(self, font, groups, current_time, level, pos):
        self.font = font
        text = f'LEVEL {level}!!!'
        frames = [
            font.render(text, True, '#ff0000'),
            font.render(text, True, '#ffff00'),
        ]
        super().__init__(groups, frames, current_time, pos)
    #     self.frame_index = 0
    #     self.image = self.frames[self.frame_index]
    #     self.rect = self.image.get_frect(center = pos)
    #     self.duration = 1500
    #     self.start_time = current_time

    # def update(self, dt, current_time):
    #     self.frame_index += 8 * dt
    #     self.image = self.frames[int(self.frame_index) % len(self.frames)]
    #     if current_time - self.start_time >= self.duration:
    #         self.kill()
