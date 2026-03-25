import os
import pygame

from audio_reader import SoundReader

# Variables
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

TEXT_COLOR = (235, 235, 235)

background_path = "" # Add background here
player_path = "images/Player_sprite.png" # Add player sprite here

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
    freq_min = 80.0
    freq_max = 800.0
    freq_range = freq_max - freq_min

    if freq < freq_min:
        freq = freq_min
    elif freq > freq_max:
        freq = freq_max

    return int((freq - freq_min) * (SCREEN_HEIGHT / freq_range))


class Player(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__()
        self.image = load_image_or_fallback(
            player_path,
            (10, 10),
            (220, 80, 80),
        )
        self.rect = self.image.get_rect(center=(x, y))
        self.y = float(self.rect.y)

    def update(self, new_y: float) -> None:
        speed = 0.08
        self.y += (new_y - self.y) * speed
        self.rect.y = int(self.y)


def run_game(screen: pygame.Surface, clock: pygame.time.Clock, microphone) -> bool:
    pygame.display.set_caption(f"Frequency game - {microphone['name']}")

    background = load_image_or_fallback(
        background_path,
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        (45, 60, 90),
    )

    player_group = pygame.sprite.Group()
    player = Player(int(SCREEN_WIDTH / 2), int(SCREEN_HEIGHT / 2))
    player_group.add(player)

    audio = SoundReader(
        device=microphone["index"],
        gate_db=-40.0,
        min_hz=20.0,
    )

    title_font = pygame.font.Font(None, 16)
    info_font = pygame.font.Font(None, 16)

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

            current_frequency = audio.get_latest_frequency()

            if current_frequency is not None:
                player_group.update(freq_to_y(current_frequency))
            else:
                player_group.update(SCREEN_HEIGHT / 2)

            screen.blit(background, (0, 0))
            player_group.draw(screen)

            draw_text(screen, f"Microphone: {microphone['name']}", title_font, TEXT_COLOR, 20, 45)
            draw_text(screen, "ESC = back to microphone menu", info_font, TEXT_COLOR, 20, 20)


            pygame.display.flip()

    finally:
        audio.stop()