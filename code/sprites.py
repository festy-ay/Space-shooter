from settings import *

class CollisionSprites(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(center = pos)

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

class Laser(pygame.sprite.Sprite):
    def __init__(self, surf, pos, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(midbottom = pos)
        self.start_time = pygame.time.get_ticks()
        self.lifetime = 3000

    def update(self, dt):
        self.rect.y -= 800 * dt
        if pygame.time.get_ticks() - self.start_time >= self.lifetime:
            self.kill()

class AnimatedExploaaion(pygame.sprite.Sprite):
    def __init__(self, frames, pos, groups):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_frect(center = pos)

    def update(self, dt):
        self.frame_index += 5 * dt
        try: self.image = self.frames[int(self.frame_index)]
        except IndexError: self.kill()
