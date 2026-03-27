import os
import pygame

from audio_reader import SoundReader

# Variables
# Screen
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 120
background_path = "" # Add background here
TEXT_COLOR = (235, 235, 235)
BACKGROUND_COLOR = (0, 0, 0)

# Player
movement_smoothing = 30 # Higher value equals smoother movement
player_path = "" # Add player sprite here
player_size = 20
player_colour = (240, 240, 20)
ticks_until_invisible = 40

# Tone bar
movement_speed = 2
tone_bar_width = 300
tone_bar_height = 30
tone_bar_colour = (0, 204, 255)
tone_bar_alpha = 150

# Sound
minimum_frequency = 150.0
maximum_frequency = 500.0
dB_threshold = 50.0 # Higher = lower threshold


def load_image_or_fallback(
    path: str,
    size: tuple[int, int],
    fill_color: tuple[int, int, int],
) -> pygame.Surface:
    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(image, size)

    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(fill_color)
    return surface


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    x: int,
    y: int,
) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, (x, y))


def freq_to_y(freq: float) -> int:
    freq_range = maximum_frequency - minimum_frequency

    if freq < minimum_frequency:
        freq = minimum_frequency
    elif freq > maximum_frequency:
        freq = maximum_frequency

    return int(SCREEN_HEIGHT - ((freq - minimum_frequency) * (SCREEN_HEIGHT / freq_range)))


class Player(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__()
        self.image = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            player_colour,
            (player_size // 2, player_size // 2),
            player_size // 2
        )
        self.rect = self.image.get_rect(center=(x, y))
        self.y = float(self.rect.y)

    def update(self, new_y: float) -> None:
        speed = 1/movement_smoothing
        self.y += (new_y - self.y) * speed
        self.rect.y = round(self.y)

class PlayerGlow(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float):
        super().__init__()

        self.base_size = player_size
        self.base_image = pygame.Surface((self.base_size, self.base_size), pygame.SRCALPHA)

        pygame.draw.circle(
            self.base_image,
            (*player_colour, 200),
            (self.base_size // 2, self.base_size // 2),
            self.base_size // 2
        )

        self.x = float(x)
        self.y = float(y)

        self.scale = 1.0

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(round(self.x), round(self.y)))

    def update(self, player_y: float) -> None:
        self.x -= movement_speed

        # Krymp långsamt
        # self.scale *= 0.995
        # new_size = max(2, int(self.base_size * self.scale))
        # self.image = pygame.transform.smoothscale(self.base_image, (new_size, new_size))

        self.rect = self.image.get_rect(center=(round(self.x), round(self.y)))

        if self.rect.x <= 0:
            self.kill()

class ToneBar(pygame.sprite.Sprite):
    def __init__(self, y: int):
        super().__init__()

        border_radius = tone_bar_height // 2
        border_width = 2
        border_colour = (255, 255, 255)

        self.image = pygame.Surface((tone_bar_width, tone_bar_height), pygame.SRCALPHA)

        # Filled rounded bar
        pygame.draw.rect(
            self.image,
            (*tone_bar_colour, tone_bar_alpha),
            (0, 0, tone_bar_width, tone_bar_height),
            border_radius=border_radius
        )

        # Border
        pygame.draw.rect(
            self.image,
            (*border_colour, tone_bar_alpha),
            (0, 0, tone_bar_width, tone_bar_height),
            width=border_width,
            border_radius=border_radius
        )

        self.rect = self.image.get_rect(midleft=(SCREEN_WIDTH, y))

    def update(self):
        self.rect.x -= movement_speed

        if self.rect.right < 0:
            self.kill()




def run_game(screen: pygame.Surface, clock: pygame.time.Clock, microphone) -> bool:
    pygame.display.set_caption(f"Frequency game - {microphone['name']}")

    background = load_image_or_fallback(
        background_path,
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        BACKGROUND_COLOR,
    )

    player_group = pygame.sprite.Group()
    player = Player(int(SCREEN_WIDTH / 2), int(SCREEN_HEIGHT / 2))
    player_group.add(player)

    player_glow_group = pygame.sprite.Group()

    tone_bar_group = pygame.sprite.Group()

    audio = SoundReader(
        device=microphone["index"],
        gate_db=-dB_threshold,
        min_hz=20.0,
    )

    title_font = pygame.font.Font(None, 16)
    info_font = pygame.font.Font(None, 16)

    none_ticks = 0
    player_visible = True

    try:
        audio.start()
        audio.start_listening()

        while True:
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return True

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        tone_bar = ToneBar(300)
                        tone_bar_group.add(tone_bar)

            current_frequency = audio.get_latest_frequency()

            if current_frequency is None:
                none_ticks += 1

                if none_ticks >= ticks_until_invisible and player_visible:
                    player_group.remove(player)
                    player_glow_group.remove(player_glow)
                    player_visible = False

            else:
                none_ticks = 0

                if not player_visible:
                    player_group.add(player)
                    player_visible = True

                player.update(freq_to_y(current_frequency))



            if player_visible:
                player_glow = PlayerGlow(
                    int(SCREEN_WIDTH / 2),
                    int(player.rect.y + player.rect.height / 2)
                )
                player_glow_group.add(player_glow)

            player_glow_group.update(player.rect.y)
            tone_bar_group.update()
            screen.blit(background, (0, 0))
            tone_bar_group.draw(screen)
            player_glow_group.draw(screen)
            player_group.draw(screen)

            draw_text(screen, f"Microphone: {microphone['name']}", title_font, TEXT_COLOR, 20, 45)
            draw_text(screen, "ESC = back to microphone menu", info_font, TEXT_COLOR, 20, 20)
            if current_frequency is None:
                draw_text(screen, "Current frequency: None", info_font, TEXT_COLOR, 20, 90)
            else:
                draw_text(screen, f"Current frequency: {current_frequency:.1f} Hz", info_font, TEXT_COLOR, 20, 90)


            pygame.display.flip()

    finally:
        audio.stop()