import os
import random
import pygame

from audio_reader import SoundReader

# Variables
# Game variables
num_sounds_to_play = 3
mp3_seconds = 1.5  # Seconds sound is played for
between_mp3_seconds = 0.1  # Seconds between mp3 sounds
pre_game_seconds = 1  # Seconds before game starts

player_score = 0
player_max_score = 0
last_player_score = 0.0
last_note_is_hit = False

tone_delta_threshold = 10

# Screen
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 120
background_path = "" # Add background here
TEXT_COLOR = (235, 235, 235)
BACKGROUND_COLOR = (0, 0, 0)

# Player
movement_smoothing = 5 # Higher value equals smoother movement (1 = no smoothing)
player_path = "" # Add player sprite here
player_size = 20
player_colour = (240, 240, 20)
seconds_until_invisible = 0.1

# Tone bar
movement_speed = 1
tone_bar_width = mp3_seconds * FPS * movement_speed
tone_bar_height = 30
tone_bar_colour = (0, 204, 255)
tone_bar_alpha = 150

# Sound input
minimum_frequency = 180.0
maximum_frequency = 610.0
dB_threshold = 50.0 # Higher = lower threshold

# Sound output
AUDIO_FOLDER = "audio"
MP3_DURATION_FRAMES = FPS * 2  # 3 seconds

# Piano keys and their frequency (range: 80hz - 1000hz)
piano_frequencies = {
    "A3": 220,
    "A4": 440,

    "Ab3": 208,
    "Ab4": 415,

    "B3": 247,
    "B4": 494,

    "Bb3": 233,
    "Bb4": 466,

    "C4": 262,
    "C5": 523,

    "D4": 294,
    "D5": 587,

    "Db4": 277,
    "Db5": 554,

    "E4": 330,

    "Eb4": 311,

    "F4": 349,

    "G3": 196,
    "G4": 392,

    "Gb3": 185,
    "Gb4": 370
}

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

def seconds_to_ticks(seconds: float) -> int:
    return int(seconds * FPS)

def play_mp3(filename: str) -> None:
    path = os.path.join(AUDIO_FOLDER, filename)

    if not os.path.exists(path):
        print(f"Missing audio file: {path}")
        return

    pygame.mixer.music.load(path)
    pygame.mixer.music.play()

def stop_mp3() -> None:
    pygame.mixer.music.stop()


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
        self.center_y = float(self.rect.centery)

    def update(self, new_y: float) -> None:
        speed = 1 / movement_smoothing
        self.center_y += (new_y - self.center_y) * speed
        self.rect.centery = round(self.center_y)

class PlayerTrail(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float):
        super().__init__()

        self.base_size = player_size
        self.base_image = pygame.Surface((self.base_size, self.base_size), pygame.SRCALPHA)

        global last_note_is_hit
        if last_note_is_hit:
            trail_colour = (0, 255, 0)
        else:
            trail_colour = player_colour
        last_note_is_hit = False

        pygame.draw.circle(
            self.base_image,
            (*trail_colour, 200),
            (self.base_size // 2, self.base_size // 2),
            self.base_size // 2
        )

        self.x = float(x)
        self.y = float(y)

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(round(self.x), round(self.y)))

    def update(self, player_y: float) -> None:
        self.x -= movement_speed
        self.rect = self.image.get_rect(center=(round(self.x), round(self.y)))

        if self.rect.x <= 0:
            self.kill()

class ToneBar(pygame.sprite.Sprite):
    def __init__(self, y: int, note_name: str, frequency: float):
        super().__init__()

        border_radius = tone_bar_height // 2
        border_width = 2
        border_colour = (255, 255, 255)
        text_colour = (255, 255, 255)

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

        # Text inside bar
        font = pygame.font.Font(None, 22)
        label = f"{note_name} - {frequency} Hz"
        text_surface = font.render(label, True, text_colour)
        text_rect = text_surface.get_rect(center=(tone_bar_width // 2, tone_bar_height // 2))
        self.image.blit(text_surface, text_rect)

        self.rect = self.image.get_rect(midleft=(SCREEN_WIDTH, y))

    def update(self, player_y: float) -> None:
        self.rect.x -= movement_speed

        if SCREEN_WIDTH/2 >= self.rect.x >= SCREEN_WIDTH/2 - tone_bar_width:
            global player_max_score
            global player_score
            global last_note_is_hit
            player_max_score += 1
            if abs(player_y - self.rect.y) < tone_delta_threshold:
                player_score += 1
                last_note_is_hit = True
            else:
                last_note_is_hit = False

        if self.rect.right < 0:
            self.kill()

# create player guide line
guide_x = SCREEN_WIDTH // 2
guide_top = 0
guide_bottom = SCREEN_HEIGHT

guide_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
pygame.draw.line(
    guide_surface,
    (180, 180, 180, 100),   # transparent gray
    (guide_x, guide_top),
    (guide_x, guide_bottom),
    3,
)


def run_game(screen: pygame.Surface, clock: pygame.time.Clock, microphone) -> bool:
    pygame.display.set_caption(f"Frequency game - {microphone['name']}")

    background = load_image_or_fallback(
        background_path,
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        BACKGROUND_COLOR,
    )

    player_group = pygame.sprite.Group()
    player = Player(int(SCREEN_WIDTH/2), int(SCREEN_HEIGHT / 2))
    player_group.add(player)

    player_trail_group = pygame.sprite.Group()
    tone_bar_group = pygame.sprite.Group()

    audio = SoundReader()

    title_font = pygame.font.Font(None, 16)
    info_font = pygame.font.Font(None, 16)
    game_info_font = pygame.font.Font(None, 25)

    player_visible = True
    game_event_active = False

    none_ticks = 0
    mp3_ticks = 0
    between_mp3_ticks = 0
    pre_game_ticks = 0
    post_game_ticks = 0

    global player_score
    global player_max_score
    global last_player_score
    global last_note_is_hit

    ticks_until_invisible = seconds_to_ticks(seconds_until_invisible)

    available_sounds = list(piano_frequencies.keys())
    random.shuffle(available_sounds)

    current_note = None
    sounds_played = 0

    try:
        audio.start()
        audio.start_listening()

        while True:
            clock.tick(FPS)
            if mp3_ticks == 0 and between_mp3_ticks == 0:
                current_frequency = audio.get_latest_frequency()
            else:
                current_frequency = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return True

                    if event.key == pygame.K_SPACE and not game_event_active:
                        game_event_active = True
                        mp3_ticks = seconds_to_ticks(mp3_seconds)
                        between_mp3_ticks = seconds_to_ticks(between_mp3_seconds)
                        pre_game_ticks = seconds_to_ticks(pre_game_seconds)
                        post_game_ticks = ((SCREEN_WIDTH/2+tone_bar_width)/movement_speed)+5
                        sounds_played = 0
                        current_note = None

                        available_sounds = list(piano_frequencies.keys())
                        random.shuffle(available_sounds)

            if game_event_active:
                if pre_game_ticks > 0: # Delay before playing notes
                    pre_game_ticks -= 1
                else:
                    if mp3_ticks > 0:
                        if current_note is None:
                            if available_sounds:
                                current_note = available_sounds.pop()
                                current_frequency_value = piano_frequencies[current_note]

                                tone_bar = ToneBar(
                                    freq_to_y(current_frequency_value),
                                    current_note,
                                    current_frequency_value
                                )
                                tone_bar_group.add(tone_bar)

                                play_mp3(f"{current_note}.mp3")

                        mp3_ticks -= 1

                        if mp3_ticks == 0:
                            stop_mp3()
                            current_note = None
                    else:
                        if between_mp3_ticks > 0:
                            between_mp3_ticks -= 1
                        else:
                            if sounds_played < num_sounds_to_play - 1:
                                sounds_played += 1
                                mp3_ticks = seconds_to_ticks(mp3_seconds)
                                between_mp3_ticks = seconds_to_ticks(between_mp3_seconds)
                            else:
                                if post_game_ticks > 0:
                                    post_game_ticks -= 1
                                else:
                                    if player_score > 0:
                                        last_player_score = float((player_score/player_max_score)*100)
                                    else:
                                        last_player_score = 0
                                    player_score = 0
                                    player_max_score = 0
                                    game_event_active = False

            if current_frequency is None:
                none_ticks += 1

                if none_ticks >= ticks_until_invisible and player_visible:
                    player_group.remove(player)
                    player_visible = False
            else:
                none_ticks = 0

                if not player_visible:
                    player_group.add(player)
                    player_visible = True

                player.update(freq_to_y(current_frequency))

            if player_visible:
                player_trail = PlayerTrail(
                    int(SCREEN_WIDTH / 2),
                    int(player.rect.y + player.rect.height / 2)
                )
                player_trail_group.add(player_trail)

            player_trail_group.update(player.rect.y)
            tone_bar_group.update(player.rect.y)

            screen.blit(background, (0, 0))

            # Draw player guide line
            screen.blit(guide_surface, (0, 0))

            tone_bar_group.draw(screen)
            player_trail_group.draw(screen)
            player_group.draw(screen)

            draw_text(screen, f"Latest score: {last_player_score:.2f}%", game_info_font, TEXT_COLOR, int(SCREEN_WIDTH/2)+40, 20)

            if current_frequency is None:
                draw_text(screen, "Current frequency: None", game_info_font, TEXT_COLOR, int(SCREEN_WIDTH/2)-260, 20)
            else:
                draw_text(screen, f"Current frequency: {current_frequency:.1f} Hz", game_info_font, TEXT_COLOR, int(SCREEN_WIDTH/2)-260, 20)

            pygame.display.flip()

    finally:
        stop_mp3()
        audio.stop()