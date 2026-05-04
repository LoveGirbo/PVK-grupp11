import os
import random
import pygame
import math
import random

from audio_reader import SoundReader

# Variables
# Game variables
max_notes = 3
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
background_path = ""  # Add background here
TEXT_COLOR = (235, 235, 235)
BACKGROUND_COLOR = (0, 0, 0)

# Player
movement_smoothing = 5  # Higher value equals smoother movement (1 = no smoothing)
player_path = ""  # Add player sprite here
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
dB_threshold = 50.0  # Higher = lower threshold

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

        self.rect = self.image.get_rect(midleft=(SCREEN_WIDTH-140, y))

    def update(self, player_y: float) -> None:
        self.rect.x -= movement_speed

        if SCREEN_WIDTH / 3  >= self.rect.x >= SCREEN_WIDTH / 3 - tone_bar_width:
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
guide_x = SCREEN_WIDTH // 3
guide_top = 0
guide_bottom = SCREEN_HEIGHT

guide_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
pygame.draw.line(
    guide_surface,
    (180, 180, 180, 100),  # transparent gray
    (guide_x, guide_top),
    (guide_x, guide_bottom),
    3,
)

# 1. Skapa längre listor (t.ex. 4-5 oktaver totalt)
# OCTAVE_WHITE = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "A3"]


WHITE_KEYS = [
    "A0", "B0",
    "C1", "D1", "E1", "F1", "A1", "B1",
    "C2", "D2", "E2", "F2", "A2", "B2",
    "C3", "D3", "E3", "F3", "A3", "B3",
    "C4", "D4", "E4", "F4", "A4", "B4",
    "C5", "D5", "E5", "F5", "A5", "B5",
    "C6", "D6", "E6", "F6", "A6", "B6",
    "C7", "D7", "E7", "F7", "A7", "B7"
]

BLACK_KEYS = [
    "Db4", "Eb4", "Gb4", "Ab4", "Bb4",
    "Db5", "Eb5", "Gb5", "Ab5", "Bb5",
    "Db6", "Eb6", "Gb6", "Ab6", "Bb6",
    "Db7", "Eb7", "Gb7", "Ab7", "Bb7"
]


# Vi multiplicerar så vi får ett rejält omfång (t.ex. 5 oktaver)
# WHITE_KEYS = OCTAVE_WHITE * 5
# BLACK_KEYS = OCTAVE_BLACK * 5


def draw_piano(screen, active_note):
    t = pygame.time.get_ticks() / 200
    pulse = (math.sin(t) + 1) / 2  # värde mellan 0–1

    piano_x = SCREEN_WIDTH - 150
    piano_y = 10  # Starta högt upp

    # --- NYA MÅTT (Smalare för att få plats med alla nya tangenter) ---
    white_key_width = 20  # Mycket smalare bredd per tangent
    white_key_height = 140  # Behåller längden

    black_key_width = 12  # Smalare svarta
    black_key_height = 90

    # -------------------
    # RITA VITA TANGENTER
    # -------------------
    for i, note in enumerate(WHITE_KEYS):
        color = (255, 255, 255)
        # OBS: Om du har flera 'C' behöver du en unik ID för active_note,
        # men för utseendet fungerar detta:

        rect = pygame.Rect(
            piano_x + 20,
            piano_y + i * white_key_width,
            white_key_height,
            white_key_width
        )
        color = (255, 255, 255)
        if note == active_note:
            color = (0, 100, 255)

        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, width=1)

    # -------------------
    # RITA SVARTA TANGENTER
    # -------------------
    # De svarta tangenternas positioner i en oktav (relativt de vita)
    # C#, D#, (gap), F#, G#, A#, (gap)
    # -------------------
    # RITA SVARTA TANGENTER
    # -------------------
    # Namnen på de svarta tangenterna i ordning per oktav (för matchning)
    black_note_names = ["Db", "Eb", "Gb", "Ab", "Bb"]
    # Positioner relativt vita tangenter: C#(0.7), D#(1.7), F#(3.7), G#(4.7), A#(5.7)
    black_offsets = [0.7, 1.7, 3.7, 4.7, 5.7]

    for octave in range(1, 8):  # Loopa igenom oktaver (t.ex. 1-7)
        for i in range(5):  # 5 svarta per oktav
            # Skapa namnet på tangenten, t.ex. "Db" + "4" = "Db4"
            note_name = f"{black_note_names[i]}{octave}"

            # Beräkna position (hitta index i WHITE_KEYS för att synka höjden)
            # Varje oktav börjar efter 7 vita tangenter.
            # Vi justerar startindex (-2) för att matcha att WHITE_KEYS börjar på A0
            rel_pos = black_offsets[i] + ((octave - 1) * 7) + 2

            rect = pygame.Rect(
                piano_x + 70,
                piano_y + int(rel_pos * white_key_width),
                black_key_height,
                black_key_width
            )

            # Färgsättning: Grön om aktiv, annars svart
            if note_name == active_note:
                color = (0, 100, 255)
            else:
                color = (0, 0, 0)

            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (60, 60, 60), rect, width=1)


def run_game(screen: pygame.Surface, clock: pygame.time.Clock, microphone) -> bool:
    pygame.display.set_caption(f"Frequency game - {microphone['name']}")

    background = load_image_or_fallback(
        background_path,
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        BACKGROUND_COLOR,
    )

    player_group = pygame.sprite.Group()
    player = Player(int(SCREEN_WIDTH / 3), int(SCREEN_HEIGHT / 3))

    player_trail_group = pygame.sprite.Group()
    tone_bar_group = pygame.sprite.Group()

    audio = SoundReader()
    game_info_font = pygame.font.Font(None, 25)
    big_font = pygame.font.Font(None, 40)

    player_visible = False
    game_event_active = True

    game_state = 0
    pause_timer = 0
    notes_sent = 0

    mp3_ticks = 0
    between_mp3_ticks = 0
    none_ticks = 0

    global player_score, player_max_score, last_player_score, last_note_is_hit
    ticks_until_invisible = seconds_to_ticks(seconds_until_invisible)

    available_sounds = list(piano_frequencies.keys())
    random.shuffle(available_sounds)

    try:
        audio.start()
        audio.start_listening()
        active_note = None

        while True:
            clock.tick(FPS)

            if mp3_ticks <= 0:
                current_frequency = audio.get_latest_frequency()
            else:
                current_frequency = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return True

            # --- POÄNGUPPDATERING I REALTID ---
            if player_max_score > 0:
                last_player_score = float((player_score / player_max_score) * 100)
            else:
                last_player_score = 0

            # --- AUTOMATISERAD SPELLOGIK ---
            if game_event_active:
                if game_state == 0:
                    if mp3_ticks <= 0 and between_mp3_ticks <= 0:
                        if notes_sent < max_notes:
                            if not available_sounds:
                                available_sounds = list(piano_frequencies.keys())
                                random.shuffle(available_sounds)
                            current_note = available_sounds.pop()
                            active_note = current_note
                            freq_val = piano_frequencies[current_note]
                            tone_bar = ToneBar(freq_to_y(freq_val), current_note, freq_val)
                            tone_bar_group.add(tone_bar)
                            play_mp3(f"{current_note}.mp3")
                            mp3_ticks = seconds_to_ticks(mp3_seconds)
                            between_mp3_ticks = seconds_to_ticks(between_mp3_seconds)
                            notes_sent += 1
                        else:
                            game_state = 1


                elif game_state == 1:
                    # Vänta tills alla noter åkt förbi innan vi pausar
                    if len(tone_bar_group) == 0:
                        # Här sparar vi slutresultatet för visning i rutan
                        final_round_score = last_player_score

                        # Vi nollställer INTE last_player_score här förrän pausen är slut
                        # Men vi nollställer räknarna för nästa runda
                        player_score, player_max_score = 0, 0
                        notes_sent = 0
                        active_note, current_note = None, None
                        pause_timer = seconds_to_ticks(10)
                        game_state = 2


                elif game_state == 2:
                    pause_timer -= 1
                    if pause_timer <= 0:
                        last_player_score = 0  # Nollställ inför nästa aktiva runda
                        game_state = 0

                if mp3_ticks > 0:
                    mp3_ticks -= 1
                    if mp3_ticks == 0: stop_mp3()
                if between_mp3_ticks > 0:
                    between_mp3_ticks -= 1

            # --- LOGIK FÖR SPELARE ---
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
                player_trail = PlayerTrail(int(SCREEN_WIDTH / 3), int(player.rect.y + player.rect.height / 2))
                player_trail_group.add(player_trail)

            player_trail_group.update(player.rect.y)
            tone_bar_group.update(player.rect.y)

            # --- RITNING ---
            screen.blit(background, (0, 0))
            screen.blit(guide_surface, (0, 0))
            tone_bar_group.draw(screen)
            player_trail_group.draw(screen)
            player_group.draw(screen)

            # --- PAUS-RUTA ---
            if game_state == 2:
                r_w, r_h = 600, 300
                r_x, r_y = (SCREEN_WIDTH // 2) - (r_w // 2), (SCREEN_HEIGHT // 2) - (r_h // 2)

                pygame.draw.rect(screen, (255, 255, 255), (r_x, r_y, r_w, r_h), border_radius=20)
                pygame.draw.rect(screen, (0, 0, 0), (r_x, r_y, r_w, r_h), 4, border_radius=20)

                # Batteriet visar slutresultatet
                bat_w, bat_h = 500, 50
                bat_x, bat_y = r_x + (r_w // 2 - bat_w // 2), r_y + 140
                pygame.draw.rect(screen, (0, 0, 0), (bat_x, bat_y, bat_w, bat_h), 4)
                pygame.draw.rect(screen, (0, 0, 0), (bat_x + bat_w, bat_y + 12, 12, 25))

                # Använder final_round_score här för att frysa batteriet under pausen
                fill_w = int((final_round_score / 100) * (bat_w - 8))
                if fill_w > 0:
                    pygame.draw.rect(screen, (50, 205, 50), (bat_x + 4, bat_y + 4, fill_w, bat_h - 8))

                sec = math.ceil(pause_timer / FPS)
                t1 = big_font.render("Snyggt jobbat!", True, (255, 100, 0))
                t2 = big_font.render(f"Du matchade {final_round_score:.0f}% av tonerna!", True, (0, 0, 0))
                t3 = game_info_font.render(f"Nästa runda börjar om: {sec}s", True, (150, 150, 150))

                screen.blit(t1, (r_x + (r_w // 2 - t1.get_width() // 2), r_y + 40))
                screen.blit(t2, (r_x + (r_w // 2 - t2.get_width() // 2), r_y + 90))
                screen.blit(t3, (r_x + (r_w // 2 - t3.get_width() // 2), r_y + 230))

            draw_piano(screen, active_note)
            pygame.display.flip()


    finally:
        stop_mp3()
        audio.stop()

