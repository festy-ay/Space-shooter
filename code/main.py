from settings import *
from player import Player
from sprites import *
from func import *

class Game():
    def __init__(self):
        self.seed = int(sys.argv[1]) if len(sys.argv) > 1 else randrange(1, 2 ** 31 - 1)
        print("seed:", self.seed)

        # ---------------------------------------------------------------- window + GL context
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("Random space background")
        self.ctx = moderngl.create_context()
        self.clock = pygame.time.Clock()
        self.font = log_font
        self.running = False

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

        import numpy as np  # noqa: E402  (only needed for the quad vertices)

        quad = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        self.bg_vao = self.ctx.vertex_array(self.bg_prog, [(quad, "2f", "in_pos")])
        self.blit_vao = self.ctx.vertex_array(self.blit_prog, [(quad, "2f", "in_pos")])

        # ---------------------------------------------------------------- render targets
        rw, rh = int(WINDOW_WIDTH * RENDER_SCALE), int(WINDOW_HEIGHT * RENDER_SCALE)
        self.scene_tex = self.ctx.texture((rw, rh), 3)
        self.scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.scene_fbo = self.ctx.framebuffer(color_attachments=[self.scene_tex])

        self.overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA) # normal pygame drawing goes here
        self.overlay_tex = self.ctx.texture((WINDOW_WIDTH, WINDOW_HEIGHT), 4)
        self.overlay_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)


        self.bg_prog["resolution"].value = (rw, rh)
        self.blit_prog["tex"].value = 0

        # ---------------------------------------------------------------- game-ish state
        self.scroll = [0.0, 0.0]
        # self.mouse_rel_movement = 0

        # sprites
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.player = Player((WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.meteor_surfs = (
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.7) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.8) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.9) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.0) for i in range(8)],
        )
        self.meteor_explosoin_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'images' , 'Sun', f'0{i+1}.png')).convert_alpha(), 0, 0.3) for i in range(8)]

        # custom events -> meteor event
        self.meteor_event = pygame.event.custom_type()
        pygame.time.set_timer(self.meteor_event, 500)

        self.imports()
        if hasattr(self, 'game_music'): self.game_music.play(-1)

    def url_get(self, url:str):
        file_name = url.split('/')[-1]
        file_type = file_name.split('.')[-1]
        audio, photo = ['wav', 'ogg', '.mp3'], ['png', 'jpeg']

        buffer = get_assets(url, self)
        if file_type in audio: return pygame.mixer.Sound(buffer)
        elif file_type in photo: return pygame.image.load(buffer, file_name).convert_alpha()
        else: return buffer

    def imports(self):
        self.laser_surf = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/images/laser.png')

        # Sounds
        log("Initializing pygame mixer...", self, False)
        pygame.mixer.init()

        self.game_music = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/game_music.wav')
        self.game_music.set_volume(0.3)

        self.laser_sound = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/laser.wav')
        self.laser_sound.set_volume(0.5)

        self.explosion_sound = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/explosion.wav')
        self.explosion_sound.set_volume(0.5)

        self.damage_sound = self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/damage.ogg')
        self.damage_sound.set_volume(0.5)

        # After imports, let there be a response before the game starts
        log('Click or press space to begin...', self)
        while not self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): pygame.quit(); sys.exit()
                if event.type == pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()): self.running = True

    def collisions(self):
        collision_sprites = pygame.sprite.spritecollide(self.player, self.meteor_sprites, True, pygame.sprite.collide_mask)
        if collision_sprites:
            self.damage_sound.play()
            self.player.life -= 1

            if self.player.life == 0:
                text = pygame.font.Font(join(path,'Font', 'DejaVuSans.ttf'), 70).render('     GAME OVER!!!\nPress space to restart or esc to exit!', True, (255, 150, 150), '#000000')
                rect = text.get_frect(center = (WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
                while True:
                    self.overlay.blit(text, rect)
                    self.overlay_tex.write(pygame.image.tobytes(self.overlay, "RGBA", True))
                    self.ctx.enable(moderngl.BLEND)
                    self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
                    self.overlay_tex.use(0)
                    self.blit_vao.render(moderngl.TRIANGLE_STRIP)
                    pygame.display.flip()
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                            pygame.quit(); sys.exit(); break
                        keys = pygame.key.get_just_pressed()
                        if keys[pygame.K_SPACE]:
                            return True


        for laser in self.laser_sprites:
            collided_sprites = pygame.sprite.spritecollide(laser, self.meteor_sprites, True, pygame.sprite.collide_mask)
            if collided_sprites: laser.kill(); AnimatedExploaaion(self.meteor_explosoin_frames, laser.rect.midtop, self.all_sprites); self.explosion_sound.play()

    def run(self):
        while self.running:
            dt = self.clock.tick() / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return True
                if event.type == self.meteor_event:
                    x = randint(0, WINDOW_WIDTH)
                    Meteor(choice(self.meteor_surfs), (x,-100),  (self.all_sprites, self.meteor_sprites))


            keys = pygame.key.get_pressed()
            boost = 15.0 + 40.0 * (1 if (keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w]) else 0)
            self.scroll[1] += SCROLL_SPEED * boost * dt
            # self.scroll[0] += ((1 if self.mouse_rel_movement > 0 else 0) - (1 if self.mouse_rel_movement < 0 else 0)) * dt
            mouse = pygame.mouse.get_pressed()
            self.all_sprites.update(dt)

            if (keys[pygame.K_SPACE] or mouse[0]) and self.player.can_shoot:
                Laser(self.laser_surf, self.player.rect.center, (self.all_sprites, self.laser_sprites))
                self.player.can_shoot = False
                self.player.laser_shoot_time = pygame.time.get_ticks()
                self.laser_sound.play()

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
            hud = self.font.render(f"""seed {self.seed}   {self.clock.get_fps():.0f} fps  Player life: {self.player.life}
Controls: SPACE or Left click to shoot, W Up Arrow or Left Ctrl to accelerate
""", True, (255, 255, 255, 255)) #  [ ] = cartoon level {toon:.2f}
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
        self.player = Player((WINDOW_WIDTH / 2, WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.running = True
        self.seed = int(sys.argv[1]) if len(sys.argv) > 1 else randrange(1, 2 ** 31 - 1)
        self.bg_prog["seed"].value = self.seed


if __name__ == '__main__':
    game = Game()
    while True:
        if game.run(): pygame.quit(); break
        game.reset()