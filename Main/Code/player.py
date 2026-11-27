from .settings import pygame

class Player(pygame.sprite.Sprite):
    def __init__(self, frames: list[pygame.Surface], pos, groups, collision_sprites):
        super().__init__(groups)
        self.frames = frames
        # self.hitbox_rect = self.get_hit_rect(self.frames[0]).get_frect(midbottom = pos).inflate(-60,0)
        self.mask = pygame.mask.from_surface(self.get_hit_rect(self.frames[0]))
        self.speed_frames = self.frames[3:]
        self.frames = self.frames[:3]
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_frect(center = pos)
        self.life = 5
        self.level = 0
        self.mouse = False

        # movement
        self.direction = pygame.Vector2()
        self.speed = 500
        self.collision_sprites = collision_sprites

        # cooldowm
        self.can_shoot = True
        self.laser_shoot_time = 0
        self.cooldown_duration = 600

    def laser_timer(self,current_tim ):
        if not self.can_shoot:
            current_time = current_tim
            if current_time - self.laser_shoot_time >= self.cooldown_duration:
                self.can_shoot = True

    def get_hit_rect(self, original_surface: pygame.Surface) -> pygame.Surface:
        # 1. Get the dimensions of your original surface
        width = original_surface.get_width()
        full_height = original_surface.get_height()

        # 2. Divide the height by 2 using integer division (//) to avoid decimal errors
        half_height = full_height // 2 - 40

        # 3. Create a rectangle tracking the TOP part: (X_start, Y_start, width, height)
        top_half_rect = pygame.Rect(0, 0, width, half_height)

        # 4. Extract the subsurface slice
        return original_surface.subsurface(top_half_rect)

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a]) # mx, _ = pygame.mouse.get_pos()
        self.direction = self.direction.normalize() if self.direction else self.direction

    def move(self, dt):
        mouse = pygame.mouse.get_pos()[0]# - 30
        if self.direction.x: self.mouse = False
        elif round(mouse * 2, -2) == round(self.rect.x * 2, -2): self.mouse = True
        if self.mouse: self.rect.centerx = mouse
        else: self.rect.centerx += self.direction.x * self.speed * dt
        # self.hitbox_rect.x = min(self.hitbox_rect.x, pygame.display.get_window_size()[0]) if self.hitbox_rect.x > 0 else 0
        # self.rect.centerx = self.hitbox_rect.midbottom[0]
        self.rect.centerx = max(0, min(self.rect.centerx, pygame.display.get_window_size()[0]))


    def animate(self, dt):
        # animate
        self.frame_index += 10 * dt
        keys = pygame.key.get_pressed()
        self.image = self.frames[int(self.frame_index) % len(self.frames)] if not (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or pygame.mouse.get_pressed()[2]) else self.speed_frames[int(self.frame_index) % len(self.speed_frames)]

    def update(self, dt, current_time):
        self.input()
        self.move(dt)
        self.animate(dt)
        self.laser_timer(current_time)

            # alternative logic (not tested):
            # self.shoot_timer -= dt
            # if pygame.mouse.get_pressed()[0] and self.shoot_timer <= 0:
            #     .append([ship_x, ship_y - 30])
            #     self.shoot_timer = 0.12
            #  = [[x, y - 900 * dt] for x, y in  if y > -20]