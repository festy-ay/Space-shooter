# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///

from Code.settings import *
from Code.player import Player
from Code.sprites import *
from Code.func import *
import os, tempfile

class Game():
    def __init__(self):
        self.IS_WEB = sys.platform == "emscripten"
        pygame.init()

        icon = pygame.image.load(join(path, "Images", "icon.png"))
        pygame.display.set_icon(icon)

        if self.IS_WEB:
            self.tile_files = TILE_FILES

            self.screen = pygame.display.set_mode((WINDOW_WIDTH_INIT, WINDOW_HEIGHT_INIT))
            self.clock = pygame.time.Clock()
            self.font = log_font
            self.running = False
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)

            self.scroll = 220
            self.offset = 0.0

        else:
            self.seed = int(sys.argv[1]) if len(sys.argv) > 1 else randrange(1, 2 ** 31 - 1) # this determines the random seed for the background shader, so you can have a different background each time you run the game, or use a specific seed to get the same background again
            print("seed:", self.seed)

            # ---------------------------------------------------------------- window + GL context
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

            self.scroll = [0.0, 0.0]
            self.mouse_rel_movement = 0

        pygame.display.set_caption("Space Shooter by festy-Ay")

        # ---------------------------------------------------------------- game-ish state
        self.time_spent = 0
        self.dificulty = 1
        self.accelerated = False
        self.reference_time = 0
        self.kills = 0; self.laser_speed = 600
        self.high_score = 0
        self.next_level = 20
        self.extra_text = None
        self.extra_text_font = pygame.font.Font(join(path,'Font', 'DejaVuSans.ttf'), 70)
        self.extra_text_duration = 0
        self.extra_text_colour = '#ffff00'
        self.WINDOW_WIDTH = WINDOW_WIDTH_INIT; self.WINDOW_HEIGHT = WINDOW_HEIGHT_INIT

        # sprites
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.orb_sprites = pygame.sprite.Group()

        self.player_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'Spaceship', f'{i + 1}.png')).convert_alpha(), 0, 0.6) for i in range(6)]
        self.player_life_frames = pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'heart.png')).convert_alpha(), 0, 0.2)
        self.player = Player(self.player_frames, (WINDOW_WIDTH_INIT / 2, WINDOW_HEIGHT_INIT - 30), self.all_sprites, self.meteor_sprites)
        self.meteor_surfs = (
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.8) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 0.9) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.0) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.1) for i in range(8)],
            [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'Meteor', f'0{i+1}.png')).convert_alpha(), 23, 1.2) for i in range(8)],
        )
        self.meteor_explosoin_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'Sun', f'0{i+1}.png')).convert_alpha(), 0, 0.45) for i in range(8)]
        self.orb_frames = [pygame.transform.rotozoom(pygame.image.load(join(path, 'Images' , 'orb_frames', f'orb_0{i+1}.png')).convert_alpha(), 23, 0.7) for i in range(12)]

        # custom events -> meteor event
        self.meteor_event = pygame.event.custom_type()
        self.meteor_time = 1100
        self.orb_event = pygame.event.custom_type()
        self.orb_time = 30000
        pygame.time.set_timer(self.meteor_event, self.meteor_time)
        pygame.time.set_timer(self.orb_event, self.orb_time)

        self.pause_surf = self.extra_text_font.render("     GAME PAUSED!!!\nPress 'ENTER' to resume or esc to exit!", True, (255,150,150), '#003030')
        self.count_surfs = {n: self.extra_text_font.render(str(n), True, (255,150,150), '#003030') for n in (3, 2, 1)}
        self.welcome_frame = [
            pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'festy_frame2.png')).convert_alpha(), 0, 1.2),
            pygame.transform.rotozoom(pygame.image.load(join(path, 'Images', 'festy_frame1.png')).convert_alpha(), 0, 1.2)
        ]

        if not self.IS_WEB: self.setup()

    @property
    def layer(self):
        """The surface that normal pygame drawing goes onto: the screen on web, the overlay on desktop."""
        return self.screen if self.IS_WEB else self.overlay

    async def after_init(self):
        await self.imports()
        if not hasattr(self, 'laser_surf'): self.laser_surf = pygame.Surface((8, 50), pygame.SRCALPHA); self.laser_surf.fill("#f0a0f0")
        if hasattr(self, 'game_music'): self.game_music.play(-1)

        # display about game
        info = """ 
____________Welcome to Space Shooter by festy-Ay!____________

Controls:
- Move the mouse pointer or use 'A'-'D' or < > arrow keys to move the spaceship sideways
- Press W, Up Arrow, Left Ctrl or Left Click to accelerate
- Press Space or Left click to shoot
- Press Esc to exit the game
*** NOTE that after using keys to move the spaceship, to use the mouse pointer, you have to 
move the pointer to where the spaceship is horizontally!!!***

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
"""

        current_time = pygame.time.get_ticks()
        info_end = '\n\n        Loading.'
        clear_log()
        log(info + info_end, self, True)
        exp = 100
        while not self.running:
            if (pygame.time.get_ticks() - current_time > 2000) and 'Loading' in info_end:
                clear_log(); info_end = '\n\nClick anywhere or press space to continue...'
                log(info + info_end, self, True)
            elif pygame.time.get_ticks() - current_time >= exp and 'Loading' in info_end:
                exp += 100; clear_log(); info_end += '.'
                log(info + info_end, self, True)
            for event in pygame.event.get():
                if not self.IS_WEB and (event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)): pygame.quit(); sys.exit()
                if (pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed())) and (pygame.time.get_ticks() - current_time > 2000):
                    self.clock.tick(); self.running = True; return
            await asyncio.sleep(0)              # required by pygbag; harmless on desktop

    def setup(self, width=WINDOW_WIDTH_INIT):
        if self.IS_WEB:
            """Load the background tile and scale it to the window width (once, at start-up)."""
            tile = pygame.image.load(choice(self.tile_files)).convert()           # convert() makes blitting much faster
            if tile.get_width() != width:
                scale = width / tile.get_width()
                tile = pygame.transform.smoothscale(tile, (width, round(tile.get_height() * scale)))
            self.tile = tile

        else:
            # ---------------------------------------------------------------- render targets
            self.WINDOW_WIDTH, self.WINDOW_HEIGHT = pygame.display.get_window_size()
            # never render more shader pixels than the original window had
            scale = min(RENDER_SCALE, (SHADER_MAX_PIXELS / (self.WINDOW_WIDTH * self.WINDOW_HEIGHT)) ** 0.5)
            rw, rh = max(1, int(self.WINDOW_WIDTH * scale)), max(1, int(self.WINDOW_HEIGHT * scale))
            # rw, rh = int(self.WINDOW_WIDTH * RENDER_SCALE), int(self.WINDOW_HEIGHT * RENDER_SCALE)

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
            self.bg_prog["unit"].value = SHADER_UNIT * scale

            # Last line: tell the real window's framebuffer its new size
            self.ctx.screen.viewport = (0, 0, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    async def url_get(self, url:str):
        if self.IS_WEB:
            file_name = url.split('/')[-1]
            file_type = file_name.split('.')[-1]
            audio, photo = ['wav', 'ogg'], ['png', 'jpeg']

            buffer = await get_assets(url, self)
            if hasattr(buffer, "seek"):
                buffer.seek(0)
            data = buffer.read() if hasattr(buffer, "read") else bytes(buffer)
            log(f"bytes: {len(data)}", self)

            path = os.path.join(tempfile.gettempdir(), file_name)
            with open(path, "wb") as f:
                f.write(data)
            log(f"saved to {path}", self)

            try:
                if file_type in audio:
                    return pygame.mixer.Sound(path)
                elif file_type in photo:
                    surf = pygame.image.load(path)
                    log(f"image loaded {surf.get_size()}", self)
                    return surf.convert_alpha()
                else:
                    return io.BytesIO(data)
            except Exception as e:
                log(f"load failed: {type(e).__name__} {e}", self)
                raise

        else:
            file_name = url.split('/')[-1]
            file_type = file_name.split('.')[-1]
            audio, photo = ['wav', 'ogg', '.mp3'], ['png', 'jpeg']

            buffer = await get_assets(url, self)
            if file_type in audio: return pygame.mixer.Sound(buffer)
            elif file_type in photo: return pygame.image.load(buffer, file_name).convert_alpha()
            else: return buffer

    async def imports(self):
        error = False
        try:
            self.laser_surf = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/images/laser.png')
        except Exception as e:
            log(f'Error importing laser.png: {type(e).__name__}', self); error = True

        # Sounds
        log("Initializing pygame mixer...", self, False)
        pygame.mixer.init()

        try:
            self.laser_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/laser.wav')
        except Exception as e:
            log(f'Error importing laser.wav: {type(e).__name__}', self); error = True
        else: self.laser_sound.set_volume(0.5)

        try:
            self.explosion_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/explosion.wav')
        except Exception as e:
            log(f'Error importing explosion_sound.wav: {type(e).__name__}', self); error = True
        else: self.explosion_sound.set_volume(0.5)

        try:
            self.damage_sound = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/damage.ogg')
        except Exception as e:
            log(f'Error importing damage_sound.ogg: {type(e).__name__}', self); error = True
        else: self.damage_sound.set_volume(0.5)

        try:
            self.game_music = await self.url_get('https://raw.githubusercontent.com/clear-code-projects/5games/main/space%20shooter/audio/game_music.wav')
        except Exception as e:
            log(f"Error importing game_music.wav: {type(e).__name__}", self); error = True
        else: self.game_music.set_volume(0.3)

        if error: log("Restart the game to download assets or continue without some assets...", self)

        # After imports, let there be a response before the game starts
        log('Click or press space to begin...', self)
        while not self.running:
            for event in pygame.event.get():
                if not self.IS_WEB and event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): pygame.quit(); sys.exit()
                if pygame.key.get_pressed()[pygame.K_SPACE] or any(pygame.mouse.get_pressed()): self.clock.tick(); return
            await asyncio.sleep(0)              # required by pygbag; harmless on desktop

    def draw_background(self, dt, blank: pygame.Color | None = None):
        if self.IS_WEB:
            if not blank:
                """Draw the tile scrolled down by `offset` pixels. The tile repeats, so any offset works.

                The tile must be at least as tall as the window (the supplied one is 3x taller)."""
                self.offset = (self.offset + self.scroll * dt) % self.tile.get_height()
                tile_h = self.tile.get_height()
                y = int(self.offset) % tile_h
                self.screen.blit(self.tile, (0, y - tile_h))      # the copy above: it fills the top part of the screen
                if y < self.screen.get_height():
                    self.screen.blit(self.tile, (0, y))           # the copy below: only needed while it is still on screen

                self.all_sprites.draw(self.screen)
            else: self.screen.fill(blank)

        else:
            if not blank:
                # ---- 1. run the background shader
                self.bg_prog["time"].value = self.time_spent / 1000
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
                self.all_sprites.draw(self.overlay)
            else: self.overlay.fill(blank)

    def displayer(
            self,
            text: pygame.Surface,
            rect: pygame.FRect,
            draw_rect: tuple[pygame.Color, tuple[int,int], tuple[int,int], int, int] | None = None
            ):
        if self.IS_WEB:
            if draw_rect: pygame.draw.rect(self.screen, draw_rect[0], rect.inflate(*draw_rect[1]).move(*draw_rect[2]), draw_rect[3], draw_rect[4])
            self.screen.blit(text, rect)
            pygame.display.flip()
        else:
            if draw_rect: pygame.draw.rect(self.overlay, draw_rect[0], rect.inflate(*draw_rect[1]).move(*draw_rect[2]), draw_rect[3], draw_rect[4])
            self.overlay.blit(text, rect)
            self.overlay_tex.write(pygame.image.tobytes(self.overlay, "RGBA", True))
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            self.overlay_tex.use(0)
            self.blit_vao.render(moderngl.TRIANGLE_STRIP)
            pygame.display.flip()

    async def pause_game(self):
        def poll():   # returns 'quit', 'resume' or None; also drains the timer events
            result = None
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return 'quit'
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    result = 'resume'
                if not self.IS_WEB and event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
                    self.setup(); self.player.rect.centery = self.WINDOW_HEIGHT - 30
            return result

        # 1. wait for ENTER
        surf = self.pause_surf
        rect = surf.get_frect(center=(self.WINDOW_WIDTH / 2, self.WINDOW_HEIGHT / 2))
        self.displayer(surf, rect, ('#003030', (20,15), (0,-1.5), 0, 20))
        while True:
            r = poll()
            if r == 'quit': return True
            if r == 'resume': break
            self.clock.tick(30)
            await asyncio.sleep(0)

        # 2. 3-second countdown
        end = pygame.time.get_ticks() + 3000
        while (remaining := end - pygame.time.get_ticks()) > 0:
            if poll() == 'quit': return True
            self.draw_background(0)
            surf = self.count_surfs[(remaining + 999) // 1000]
            rect = surf.get_frect(center=(self.WINDOW_WIDTH / 2, self.WINDOW_HEIGHT / 2))
            self.displayer(surf, rect, ('#003030', (20,15), (0,-1.5), 0, 20))
            self.clock.tick(30)
            await asyncio.sleep(0)

        self.reference_time = pygame.time.get_ticks() - self.time_spent
        self.clock.tick()          # avoids a dt jump on the first frame after resuming

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
                text = self.extra_text_font.render('     GAME OVER!!!\nPress space to restart or esc to exit!', True, (255, 150, 150), '#003030')
                rect = text.get_frect(center = (self.WINDOW_WIDTH / 2, self.WINDOW_HEIGHT / 2))
                self.displayer(text, rect, ('#003030', (20,15), (0,-1.5), 0, 20))

                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): return False
                        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                            self.clock.tick()       # this prevents the game from jumping after unpausing it
                            return True
                        if not self.IS_WEB and event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
                            self.setup(); self.player.rect.centery = self.WINDOW_HEIGHT - 30
                            self.displayer(text, rect, ('#003030', (20,15), (0,-1.5), 0, 20))

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

                        LevelUpIndicator(self.extra_text_font, self.all_sprites, self.time_spent, self.player.level, (self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2))

                AnimatedExplosion(self.meteor_explosoin_frames, laser.rect.midtop, self.all_sprites)
                if hasattr(self, 'explosion_sound'): self.explosion_sound.play()

    async def run(self):
        self.setup(); self.reference_time = pygame.time.get_ticks()
        if not self.IS_WEB: self.player.rect.centery = self.WINDOW_HEIGHT - 30
        while self.running:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            self.time_spent = pygame.time.get_ticks() - self.reference_time

            # set game dificulty
            dificulty_ = int(min(9, 1 + ((self.time_spent / 1000) // 60)))
            if self.dificulty != 'max' and dificulty_ != self.dificulty:
                self.dificulty = dificulty_
                self.meteor_time = (self.meteor_time + 100) * 2 / (self.dificulty + 1)
                pygame.time.set_timer(self.meteor_event, int(self.meteor_time))
                self.orb_time -= 5000 if self.dificulty < 5 else -10000
                pygame.time.set_timer(self.orb_event, int(self.orb_time))
                self.dificulty = self.dificulty if self.dificulty < 9 else 'max'

            # check game events
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): return True
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        gmns = await self.pause_game()
                        if gmns: return True
                if event.type == self.meteor_event:
                    x = randint(0, self.WINDOW_WIDTH)
                    Meteor(choice(self.meteor_surfs), (x,-100),  (self.all_sprites, self.meteor_sprites))
                if event.type == self.orb_event:
                    x = randint(0, self.WINDOW_WIDTH)
                    Orb(self.orb_frames, (x,-100),  (self.all_sprites, self.orb_sprites))
                if not self.IS_WEB and self.dificulty == 'max' and event.type == pygame.MOUSEMOTION: self.mouse_rel_movement = event.rel[0]
                if not self.IS_WEB and event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
                    self.setup(); self.player.rect.centery = self.WINDOW_HEIGHT - 30

            # set background shader movement
            keys = pygame.key.get_pressed()
            mouse = pygame.mouse.get_pressed()
            accelerate = keys[pygame.K_UP] or keys[pygame.K_LCTRL] or keys[pygame.K_w] or mouse[2]
            if self.IS_WEB:
                if accelerate and not self.accelerated: self.scroll = 500; self.accelerated = True; self.player.speed += 100
                elif not accelerate and self.accelerated: self.accelerated = False; self.player.speed -= 100; self.scroll = 220
            else:
                boost = 15.0 + 40.0 * (1 if accelerate else 0)
                if accelerate and not self.accelerated: self.accelerated = True; self.player.speed += 100
                elif not accelerate and self.accelerated: self.accelerated = False; self.player.speed -= 100

                self.scroll[1] += SCROLL_SPEED * boost * dt
                self.scroll[0] += ((1 if self.mouse_rel_movement > 0 else 0) - (1 if self.mouse_rel_movement < 0 else 0)) * dt if self.dificulty == 'max' else 0
                self.mouse_rel_movement = 0

            # player shooting
            if (keys[pygame.K_SPACE] or mouse[0]) and self.player.can_shoot:
                Laser(self.laser_surf, self.player.rect.center, (self.all_sprites, self.laser_sprites), self.laser_speed, self.time_spent)
                self.player.can_shoot = False
                self.player.laser_shoot_time = self.time_spent
                if hasattr(self, 'laser_sound'): self.laser_sound.play()

            self.all_sprites.update(dt, self.time_spent)

            gmns = await self.collisions()
            if gmns: return False
            elif gmns == False: return True

            game_text = f"""{self.clock.get_fps():.0f} fps   High Score {self.high_score}
Controls: SPACE or Left Click to shoot; W, Up Arrow, Left Ctrl or Right Click to accelerate, Press 'ENTER' to pause the game
Game time: {(self.time_spent / 1000) / 60:.2f}mins   Dificulty level: {self.dificulty}   Next Level: {self.next_level} Meteors
Player Level: {self.player.level if self.player.level != 10 else 'max'}   Score: {self.kills}
"""
            self.draw_background(dt)
            x = (self.WINDOW_WIDTH // 2) - (self.player.life * 10)
            for i in range(self.player.life):
                self.layer.blit(self.player_life_frames, (x + (i * 25), self.WINDOW_HEIGHT - 25))
            self.displayer(self.font.render(game_text, True, "#eaff00"), (12, 10))

            await asyncio.sleep(0) # required by pygbag; harmless on desktop

    def reset(self):
        self.all_sprites = pygame.sprite.Group()
        self.meteor_sprites = pygame.sprite.Group()
        self.laser_sprites = pygame.sprite.Group()
        self.orb_sprites = pygame.sprite.Group()

        self.player = Player(self.player_frames, (self.WINDOW_WIDTH / 2, self.WINDOW_HEIGHT - 30), self.all_sprites, self.meteor_sprites)
        self.running = True

        if self.IS_WEB:
            self.scroll = 220
            self.offset = 0.0
        else:
            self.seed = int(sys.argv[1]) if len(sys.argv) > 1 else randrange(1, 2 ** 31 - 1)
            self.bg_prog["seed"].value = self.seed
            self.scroll = [0.0, 0.0]
            self.mouse_rel_movement = 0

        self.time_spent = 0
        self.dificulty = 1
        self.accelerated = False
        self.high_score = self.kills if self.kills > self.high_score else self.high_score
        self.kills = 0; self.laser_speed = 600
        self.next_level = 20
        pygame.time.set_timer(self.meteor_event, 0)
        pygame.time.set_timer(self.orb_event, 0)
        self.meteor_time = 1100
        self.orb_time = 30000
        pygame.time.set_timer(self.meteor_event, self.meteor_time)
        pygame.time.set_timer(self.orb_event, self.orb_time)

async def main():
    if __name__ == '__main__':
        game = Game()
        await game.after_init()
        while True:
            if await game.run():
                if sys.platform == "emscripten":
                    game.stop_all_audio(); game.screen.fill("#000000"); pygame.display.update(); break
                else:
                    pygame.quit(); break
            game.draw_background(None, "#000000"); game.displayer(game.extra_text_font.render('Loading...', True, '#ffff00'), (game.WINDOW_WIDTH // 2, game.WINDOW_HEIGHT // 2))
            game.reset()
            pygame.time.wait(500)
            await asyncio.sleep(0.5)

asyncio.run(main())
