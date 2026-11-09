from Code.settings import *
from Code.player import Player
from Code.sprites import *
from Code.func import *

class Game():
    def __init__(self):
        self.seed = int(sys.argv[1]) if len(sys.argv) > 1 else randrange(1, 2 ** 31 - 1) # this determines the random seed for the background shader, so you can have a different background each time you run the game, or use a specific seed to get the same background again
        print("seed:", self.seed)

        # ---------------------------------------------------------------- window + GL context
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.set_mode((WINDOW_WIDTH_INIT, WINDOW_HEIGHT_INIT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
        pygame.display.set_caption("Random space background")
        self.ctx = moderngl.create_context()
        self.clock = pygame.time.Clock()
        self.font = log_font
        self.running = False
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)

        # ---------------------------------------------------------------- shaders
        VERT = """
#version 330
in vec2 in_pos;
out vec2 uv;
void main() {
    uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
        """

        BLIT_FRAG = """
#version 330
uniform sampler2D tex;
in vec2 uv;
out vec4 fragColor;
void main() { fragColor = texture(tex, uv); }
        """

        self.bg_prog = self.ctx.program(vertex_shader=VERT, fragment_shader=Path(path / 'Shader/' / SHADER_FILE).read_text())
        self.blit_prog = self.ctx.program(vertex_shader=VERT, fragment_shader=BLIT_FRAG)
        self.blit_prog["tex"].value = 0

        import numpy as np  # noqa: E402  (only needed for the quad vertices)

        quad = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        self.bg_vao = self.ctx.vertex_array(self.bg_prog, [(quad, "2f", "in_pos")])
        self.blit_vao = self.ctx.vertex_array(self.blit_prog, [(quad, "2f", "in_pos")])

        # ---------------------------------------------------------------- game-ish state
        self.scroll = [0.0, 0.0]
        self.mouse_rel_movement = 0
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

        self.player = Player((WINDOW_WIDTH_INIT / 2, WINDOW_HEIGHT_INIT - 30), self.all_sprites, self.meteor_sprites)
        self.meteor_surfs = (
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.8) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.9) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.0) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.1) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.2) for i in range(8)],
        )
        self.meteor_explosoin_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Sun', f'0{i+1}.png')).convert_alpha(), 0, 0.45) for i in range(8)]
        self.orb_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'orb_frames', f'orb_0{i+1}.png')).convert_alpha(), 23, 0.7) for i in range(12)]

        # custom events -> meteor event
        self.meteor_event = pygame.event.custom_type()
        self.meteor_time = 1100
        self.orb_event = pygame.event.custom_type()
        self.orb_time = 30000
        pygame.time.set_timer(self.meteor_event, self.meteor_time)
        pygame.time.set_timer(self.orb_event, self.orb_time)

        self.setup()
        self.imports()
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
""", self)
        while not self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): pygame.quit(); sys.exit()
                if pygame.key.get_just_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_just_pressed()): self.running = True

    def setup(self):
        # ---------------------------------------------------------------- render targets
        self.WINDOW_WIDTH, self.WINDOW_HEIGHT = pygame.display.get_window_size()
        rw, rh = int(self.WINDOW_WIDTH * RENDER_SCALE), int(self.WINDOW_HEIGHT * RENDER_SCALE)

        # Free the old GPU objects first (they don't exist on the first call)
        for name in ("scene_fbo", "scene_tex", "overlay_tex"):
            old = getattr(self, name, None)
            if old is not None:
                old.release()

        self.scene_tex = self.ctx.texture((rw, rh), 3)
        self.scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.scene_fbo = self.ctx.framebuffer(color_attachments=[self.scene_tex])

        self.overlay = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.SRCALPHA) # normal pygame drawing goes here
        self.overlay_tex = self.ctx.texture((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), 4)
        self.overlay_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

        self.bg_prog["resolution"].value = (rw, rh)

        # Last line: tell the real window's framebuffer its new size
        self.ctx.screen.viewport = (0, 0, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    def url_get(self, url:str):
        file_name = url.split('/')[-1]
        file_type = file_name.split('.')[-1]
        audio, photo = ['wav', 'ogg', '.mp3'], ['png', 'jpeg']

        buffer = get_assets(url, self)
        if file_type in audio: return pygame.mixer.Sound(buffer)
        elif file_type in photo: return pygame.image.load(buffer, file_name).convert_alpha()
        else: return buffer

    def imports(self):
        try:
            self.laser_surf = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/images/laser.png')

            # Sounds
            log("Initializing pygame mixer...", self, False)
            pygame.mixer.init()

            self.laser_sound = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/laser.wav')
            self.laser_sound.set_volume(0.5)

            self.explosion_sound = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/explosion.wav')
            self.explosion_sound.set_volume(0.5)

            self.damage_sound = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/damage.ogg')
            self.damage_sound.set_volume(0.5)

            self.game_music = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/game_music.wav')
            self.game_music.set_volume(0.3)
        except Exception as e:
            log(f"Error importing assets: {e}", self, True)
            log("Restart the game to download assetse or continue without some assets...", self, True)

        # After imports, let there be a response before the game starts
        log('Click or press space to begin...', self)
        while not self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): pygame.quit(); sys.exit()
                if pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()): return

    def collisions(self):
        collision_sprites = pygame.sprite.spritecollide(self.player, self.meteor_sprites, True, pygame.sprite.collide_mask)
        if collision_sprites:
            if hasattr(self, 'damage_sound'): self.damage_sound.play()
            self.player.life -= 1

            if self.player.life == 0:
                text = pygame.font.Font(join(path,'Font', 'DejaVuSans.ttf'), 70).render('     GAME OVER!!!\nPress space to restart or esc to exit!', True, (255, 150, 150), '#003030')
                rect = text.get_frect(center = (self.WINDOW_WIDTH / 2, self.WINDOW_HEIGHT / 2))
                pygame.draw.rect(self.overlay, '#003030', rect.inflate(20,15).move(0,-1.5), 0, 20 )
                self.overlay.blit(text, rect)
                self.overlay_tex.write(pygame.image.tobytes(self.overlay, "RGBA", True))
                self.ctx.enable(moderngl.BLEND)
                self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
                self.overlay_tex.use(0)
                self.blit_vao.render(moderngl.TRIANGLE_STRIP)
                pygame.display.flip()
                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                            pygame.quit(); sys.exit(); break
                        keys = pygame.key.get_just_pressed()
                        if keys[pygame.K_SPACE]: return True

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

    def run(self):
        self.setup(); self.player.hitbox_rect.y = pygame.display.get_window_size()[1] - 170
        self.reference_time = pygame.time.get_ticks() / 1000
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
                    x = randint(0, self.WINDOW_WIDTH)
                    Meteor(choice(self.meteor_surfs), (x,-100),  (self.all_sprites, self.meteor_sprites))
                if event.type == self.orb_event:
                    x = randint(0, self.WINDOW_WIDTH)
                    Orb(self.orb_frames, (x,-100),  (self.all_sprites, self.orb_sprites))
                if event.type == pygame.MOUSEMOTION: self.mouse_rel_movement = event.rel[0]
                if event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED): self.setup(); self.player.hitbox_rect.y = pygame.display.get_window_size()[1] - 170

            # set background shader movement
            keys = pygame.key.get_pressed()
            mouse = pygame.mouse.get_pressed()
            boost = 15.0 + 40.0 * (1 if (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or mouse[2]) else 0)
            if (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or mouse[2]) and not self.accelerated:
                self.accelerated = True; self.player.speed += 100
            elif not (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or mouse[2]) and self.accelerated:
                self.accelerated = False; self.player.speed -= 100

            self.scroll[1] += SCROLL_SPEED * boost * dt
            self.scroll[0] += ((1 if self.mouse_rel_movement > 0 else 0) - (1 if self.mouse_rel_movement < 0 else 0)) * dt if self.dificulty is 'max' else 0
            self.mouse_rel_movement = 0
            self.all_sprites.update(dt)

            # player shooting
            if (keys[pygame.K_SPACE] or mouse[0]) and self.player.can_shoot:
                Laser(self.laser_surf, self.player.rect.center, (self.all_sprites, self.laser_sprites), self.laser_speed)
                self.player.can_shoot = False
                self.player.laser_shoot_time = pygame.time.get_ticks()
                if hasattr(self, 'laser_sound'): self.laser_sound.play()

            # ---- 1. run the background shader
            self.bg_prog["time"].value = pygame.time.get_ticks() / 1000.0
            self.bg_prog["scroll"].value = (self.scroll[0], self.scroll[1])

            self.scene_fbo.use()
            self.ctx.disable(moderngl.BLEND)
            self.bg_vao.render(moderngl.TRIANGLE_STRIP)

            # ---- 2. stretch it over the window
            self.ctx.screen.use()
            self.scene_tex.use(0)
            self.blit_vao.render(moderngl.TRIANGLE_STRIP)

            # ---- 3. draw the "game" with normal pygame calls on a transparent layer
            self.overlay.fill((0, 0, 0, 0))
            hud = self.font.render(f"""{self.clock.get_fps():.0f} fps   High Score {self.high_score}
Controls: SPACE or Left Click to shoot; W, Up Arrow, Left Ctrl or Right Click to accelerate, Press esc to close the game
Game time: {self.time_spent / 60:.2f}mins   Dificulty level: {self.dificulty}   Next Level: {self.next_level} Meteors
Player life: {self.player.life}  Player Level: {self.player.level if self.player.level != 10 else 'max'}   Score: {self.kills}
""", True, "#eaff00")
            self.overlay.blit(hud, (12, 10))
            self.all_sprites.draw(self.overlay)

            self.overlay_tex.write(pygame.image.tobytes(self.overlay, "RGBA", True))
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            self.overlay_tex.use(0)
            self.blit_vao.render(moderngl.TRIANGLE_STRIP)

            if self.collisions(): return False

            pygame.display.flip()

    def reset(self):
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.player = Player((self.WINDOW_WIDTH / 2, self.WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.running = True
        self.seed = int(sys.argv[1]) if len(sys.argv) > 1 else randrange(1, 2 ** 31 - 1)
        self.bg_prog["seed"].value = self.seed
        self.scroll = [0.0, 0.0]
        self.mouse_rel_movement = 0
        self.reference_time = 0
        self.time_spent = 0.0
        self.dificulty = 1
        self.accelerated = False
        self.high_score = self.kills if self.kills > self.high_score else self.high_score
        self.kills = 0; self.laser_speed = 600
        self.next_level = 20
        self.meteor_event = pygame.event.custom_type()
        self.meteor_time = 900
        self.orb_event = pygame.event.custom_type()
        self.orb_time = 30000
        pygame.time.set_timer(self.meteor_event, self.meteor_time)
        pygame.time.set_timer(self.orb_event, self.orb_time)

if __name__ == '__main__':
    game = Game()
    while True:
        if game.run(): pygame.quit(); break
        game.reset()