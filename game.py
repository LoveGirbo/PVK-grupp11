import os
import random
import pygame
import math

from audio_reader import SoundReader

# --- KONSTANTER ---
# Dessa värden styr spelets grundinställningar. För en kund som vill testa
# nya versioner är det oftast här man börjar, innan man ändrar i funktionerna.
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 120
BACKGROUND_COLOR = (0, 0, 0)
TEXT_COLOR = (235, 235, 235)

# Bakgrundsgrafik
SPACE_TOP_COLOR = (9, 14, 36)
SPACE_BOTTOM_COLOR = (18, 36, 62)

# Spellogik
# Sätt test_mode = True om raketen alltid ska synas utan mikrofoninput.
# Det är praktiskt vid design/test, men bör normalt vara False vid uppvisning.
test_mode = False

# Antal noter som spelas i en runda innan resultatet visas.
max_notes = 3

# Hur länge en notfil spelas och hur lång paus det är innan nästa not.
mp3_seconds = 1.5
between_mp3_seconds = 0.4

# Om mikrofonen inte hör något på den här tiden döljs raketen, om test_mode är False.
seconds_until_invisible = 0.1

# En liten "snällhetsmarginal": efter en korrekt matchning kan spelaren vara
# tyst i några frames utan att direkt tappa matchningen.
tone_delta_threshold = 10
match_grace_frames = 3

# Hur mjukt ljudvågen byter form när mikrofonens frekvens ändras.
# Lägre värde = mjukare/långsammare. Högre värde = snabbare respons.
wave_frequency_smoothing = 0.02
wave_amplitude_smoothing = 0.08

# Rörelse
# Raketen flyttas inte direkt till ny frekvens, utan glider dit med smoothing.
movement_speed = 1
movement_smoothing = 5

# Spelargrafik
# Storlek, rotation och tilt för raketen.
player_size = 36
player_rotation = -45
player_max_tilt = 35
player_tilt_response = 3.0
player_tilt_smoothing = 0.25
player_sprite_supersample = 3
player_colour = (240, 240, 20)
player_path = "images/Player_sprite.png" # Exempel på sökväg till sprite

# Avgasgrafik
# Avgaserna är partiklar som skapas bakom raketen varje frame.
# Fler partiklar/längre livslängd ger en tjockare och längre svans.
exhaust_particles_per_frame = 4
exhaust_max_particles = 520
exhaust_lifetime = 190
exhaust_start_radius = 11
exhaust_spread = 9

# Tonbalksgrafik
# Tonbalkarna är de blåa/gröna rektanglarna som spelaren ska matcha.
tone_bar_alpha = 200 # Mer täckande
tone_bar_colour = (0, 204, 255)
tone_bar_match_colour = (0, 220, 90)

# Ljud
# Spelets mikrofonvisning spänns över C2-B6. Det betyder att raketen kan visa
# frekvenser i detta område, även om matchningsnoterna är ett mindre urval.
minimum_frequency = 65.41
maximum_frequency = 1975.53
dB_threshold = 50.0
AUDIO_FOLDER = "audio"
background_path = ""

# Konstanter för pianoritning
# Pianot ritas till vänster. Spelet använder samma tonpositioner för piano,
# raket, tonbalkar och mikrofonvåg.
PIANO_Y_OFFSET = 10
WHITE_KEY_H_SIZE = 140
BLACK_KEY_V_SIZE_RATIO = 0.6
BLACK_KEY_H_SIZE = 90

# Globala poängvärden
# Dessa räknare nollställs i början av varje spelrunda.
player_score = 0
player_max_score = 0
last_player_score = 0.0
last_note_is_hit = False

# --- MUSIKDATA ---
# NOTE_NAMES är alla halvtoner i en oktav. "Db" betyder D-flat/Dess.
NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
WHITE_NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]

# Det synliga pianot visar C2-B6. Ändra dessa två om spelplanen ska zoomas
# in eller ut. Exempel: C3-C6 ger ett mindre, mer inzoomat röstspann.
VISIBLE_LOW_NOTE = "C2"
VISIBLE_HIGH_NOTE = "B6"

def note_to_midi(note_name: str) -> int:
    # Gör om ett notnamn, t.ex. "A4", till ett tal. Det gör det enkelt att
    # jämföra vilka noter som ligger högre/lägre.
    if len(note_name) < 2:
        return -1

    note_prefix = note_name[:2] if len(note_name) > 2 and note_name[1] == "b" else note_name[0]
    octave_text = note_name[len(note_prefix):]

    try:
        octave = int(octave_text)
    except ValueError:
        return -1

    return (octave + 1) * 12 + NOTE_NAMES.index(note_prefix)

def build_visible_white_keys(low_note: str, high_note: str) -> list[str]:
    # Skapar listan med vita tangenter som faktiskt ska synas på skärmen.
    low_midi = note_to_midi(low_note)
    high_midi = note_to_midi(high_note)
    keys = []

    for oct in range(0, 9):
        for n in WHITE_NOTE_NAMES:
            name = f"{n}{oct}"
            midi = note_to_midi(name)

            if low_midi <= midi <= high_midi:
                keys.append(name)

    return keys

WHITE_KEYS = build_visible_white_keys(VISIBLE_LOW_NOTE, VISIBLE_HIGH_NOTE)

# Detta är noterna som spelet slumpvis kan skicka ut som tonbalkar.
# Viktigt: varje note här måste också ha en ljudfil i audio/, t.ex. C4.mp3.
piano_frequencies = {
    "C3": 130.81, "Db3": 138.59, "D3": 146.83, "Eb3": 155.56, "E3": 164.81,
    "F3": 174.61, "Gb3": 185.00,
    "G3": 196.00, "Ab3": 207.65, "A3": 220.00, "Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "Db4": 277.18, "D4": 293.66, "Eb4": 311.13, "E4": 329.63,
    "F4": 349.23, "Gb4": 369.99, "G4": 392.00, "Ab4": 415.30, "A4": 440.00,
    "Bb4": 466.16, "B4": 493.88,
    "C5": 523.25, "Db5": 554.37, "D5": 587.33, "Eb5": 622.25, "E5": 659.25,
    "F5": 698.46, "Gb5": 739.99, "G5": 783.99
}

# --- HJÄLPFUNKTIONER ---
def get_white_key_v_size(screen_h: int) -> float:
    # Räknar ut hur hög varje vit tangent ska vara för aktuell fönsterhöjd.
    return max(1.0, (screen_h - (2 * PIANO_Y_OFFSET)) / len(WHITE_KEYS))

def white_key_top_y(note_name: str, screen_h: int) -> int:
    # Returnerar Y-positionen för överkanten av en vit tangent.
    # Låga toner ska vara längre ner och höga toner längre upp.
    idx = WHITE_KEYS.index(note_name)
    v_size = get_white_key_v_size(screen_h)
    display_idx = len(WHITE_KEYS) - 1 - idx

    return PIANO_Y_OFFSET + int(display_idx * v_size)

def freq_to_note(freq: float) -> str:
    # Gör om en frekvens i Hz till närmaste pianonot.
    # Exempel: 440 Hz blir A4.
    if freq <= 0: return ""
    try:
        n = 12 * math.log2(freq / 440) + 49
        n = round(n)
        note_idx = (n + 8) % 12
        octave = (n + 8) // 12
        if 0 <= octave <= 8:
            return f"{NOTE_NAMES[note_idx]}{octave}"
    except: pass
    return ""

def get_note_y(note_name: str, screen_h: int) -> int:
    # Hittar var en viss not ska ligga på Y-axeln.
    # Svarta tangenter placeras mellan sina närmaste vita tangenter.
    if not note_name: return -100
    v_size = get_white_key_v_size(screen_h)
    is_black = "b" in note_name
    
    if is_black:
        note_prefix = note_name[0:2]
        try:
            octave = int(note_name[2:])
            previous_white = {
                "Db": "C",
                "Eb": "D",
                "Gb": "F",
                "Ab": "G",
                "Bb": "A",
            }[note_prefix]
            previous_note = f"{previous_white}{octave}"
            return white_key_top_y(previous_note, screen_h)
        except: return -100
    else:
        try:
            return white_key_top_y(note_name, screen_h) + int(v_size // 2)
        except: return -100

def freq_to_y(freq: float, screen_h: int) -> int:
    # Spelets viktigaste mappning: mikrofonfrekvens -> Y-position på skärmen.
    # Först försöker vi hitta närmaste pianonot. Om tonen ligger utanför
    # pianot används frekvensspannet som fallback.
    note = freq_to_note(freq)
    y = get_note_y(note, screen_h)
    if y < 0:
        freq_range = maximum_frequency - minimum_frequency
        f = max(minimum_frequency, min(maximum_frequency, freq))
        return int(screen_h - ((f - minimum_frequency) * (screen_h / freq_range)))
    return y

def load_image_or_fallback(path: str, size: tuple[int, int], fill_color: tuple[int, int, int]) -> pygame.Surface:
    # Försöker ladda en bild. Om bilden saknas skapas en enfärgad fallback-yta
    # så att spelet inte kraschar.
    if path and os.path.exists(path):
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(image, size)
        except: pass
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(fill_color)
    return surface

def mix_color(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * amount),
        int(color_a[1] + (color_b[1] - color_a[1]) * amount),
        int(color_a[2] + (color_b[2] - color_a[2]) * amount),
    )

def render_space_background(w: int, h: int) -> pygame.Surface:
    # Enkel, lugn bakgrund: bara en gradient. Den ritas om vid start/resize,
    # inte varje frame, vilket är bra för prestanda.
    surface = pygame.Surface((w, h))

    for y in range(h):
        amount = y / max(1, h - 1)
        pygame.draw.line(
            surface,
            mix_color(SPACE_TOP_COLOR, SPACE_BOTTOM_COLOR, amount),
            (0, y),
            (w, y),
        )

    return surface

def seconds_to_ticks(seconds: float) -> int:
    return int(seconds * FPS)

def play_mp3(filename: str) -> None:
    # Spelar upp en notfil från audio/. Används när en tonbalk spawnar.
    path = os.path.join(AUDIO_FOLDER, filename)
    if not os.path.exists(path): return
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
        except pygame.error:
            return
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()

def stop_mp3() -> None:
    pygame.mixer.music.stop()

# --- KLASSER ---
class Player(pygame.sprite.Sprite):
    # Player är raketen. Den styrs av mikrofonens frekvens i Y-led.
    def __init__(self, x: int, y: int):
        super().__init__()
        sprite_size = player_size * 2
        source_size = sprite_size * player_sprite_supersample

        # Försök ladda raketbilden. Om filen saknas ritas en enkel cirkel.
        if player_path and os.path.exists(player_path):
            image = pygame.image.load(player_path).convert_alpha()
            self.source_image = pygame.transform.smoothscale(image, (source_size, source_size))
        else:
            self.source_image = pygame.Surface((source_size, source_size), pygame.SRCALPHA)
            pygame.draw.circle(self.source_image, player_colour, (source_size // 2, source_size // 2), source_size // 2)
        
        self.sprite_size = sprite_size
        self.tilt = 0.0
        self.image = self.render_image()
        self.rect = self.image.get_rect(center=(x, y))
        self.center_y = float(self.rect.centery)
        self.angle = 90

    def render_image(self) -> pygame.Surface:
        # Raketen roteras i högre upplösning och skalas ner efteråt.
        # Det gör att spriten ser mindre pixlig ut när den tiltar.
        high_res_image = pygame.transform.rotate(
            self.source_image,
            player_rotation + self.tilt
        )
        target_size = (
            max(1, high_res_image.get_width() // player_sprite_supersample),
            max(1, high_res_image.get_height() // player_sprite_supersample),
        )

        return pygame.transform.smoothscale(high_res_image, target_size)

    def update(self, new_y: float, target_x: int) -> None:
        # new_y är målpositionen från mikrofonens frekvens.
        # Raketen glider mjukt mot den positionen och tiltar efter riktningen.
        speed = 1 / movement_smoothing
        old_y = self.center_y

        self.center_y += (new_y - self.center_y) * speed
        y_velocity = self.center_y - old_y

        target_tilt = max(
            -player_max_tilt,
            min(player_max_tilt, -y_velocity * player_tilt_response)
        )
        self.tilt += (target_tilt - self.tilt) * player_tilt_smoothing

        center = (target_x, round(self.center_y))
        self.image = self.render_image()
        self.rect = self.image.get_rect(center=center)

class ToneBar(pygame.sprite.Sprite):
    # ToneBar är en not som rör sig från höger till vänster.
    # När den passerar den vertikala linjen jämförs den med spelarens pitch.
    def __init__(self, frequency: float, note_name: str, screen_h: int, screen_w: int):
        super().__init__()
        self.frequency = frequency
        self.note_name = note_name
        self.width = int(mp3_seconds * FPS * movement_speed)
        self.is_matched = False
        self.match_grace = 0
        self.update_image(screen_h)
        self.rect = self.image.get_rect(midleft=(screen_w, freq_to_y(frequency, screen_h)))

    def update_image(self, screen_h: int, matched: bool = None):
        # Ritar om tonbalken. Den blir grön när spelaren matchar tonen.
        if matched is not None:
            self.is_matched = matched

        v_size = get_white_key_v_size(screen_h)
        # Nedskalad med 25 %, från 3.6x till 2.7x.
        h = max(30, int(v_size * 2.7)) 
        self.image = pygame.Surface((self.width, h), pygame.SRCALPHA)
        br = h // 4
        fill_colour = tone_bar_match_colour if self.is_matched else tone_bar_colour
        
        pygame.draw.rect(self.image, (*fill_colour, tone_bar_alpha), (0, 0, self.width, h), border_radius=br)
        pygame.draw.rect(self.image, (255, 255, 255, 220), (0, 0, self.width, h), width=3, border_radius=br)
        
        # Textstorleken har ökats lite.
        font_size = max(26, int(h * 0.5))
        font = pygame.font.Font(None, font_size)
        label = f"{self.note_name} - {int(self.frequency)} Hz"
        txt = font.render(label, True, (255, 255, 255))
        self.image.blit(txt, txt.get_rect(center=(self.width // 2, h // 2)))

    def update(self, player_y: float, target_x: int, screen_h: int, input_active: bool) -> None:
        # Flytta balken, kontrollera om den är vid träfflinjen och uppdatera
        # poängen. input_active krävs för att tystnad inte ska ge gratispoäng.
        self.rect.x -= movement_speed
        self.rect.centery = freq_to_y(self.frequency, screen_h)
        is_at_target = self.rect.left <= target_x <= self.rect.right
        has_live_match = (
            input_active
            and is_at_target
            and abs(player_y - self.rect.centery) < (self.rect.height // 2)
        )
        if has_live_match:
            self.match_grace = match_grace_frames
        elif self.match_grace > 0:
            self.match_grace -= 1

        is_matched = is_at_target and (has_live_match or self.match_grace > 0)

        if is_matched != self.is_matched:
            center = self.rect.center
            self.update_image(screen_h, is_matched)
            self.rect = self.image.get_rect(center=center)
        
        if is_at_target:
            global player_max_score, player_score, last_note_is_hit
            player_max_score += 1
            # Dynamisk gräns baserad på grafikens faktiska höjd.
            if is_matched:
                player_score += 1
                last_note_is_hit = True
            else: last_note_is_hit = False
        
        # Ta bort tonbalken när den passerat pianot till vänster.
        if self.rect.right < WHITE_KEY_H_SIZE: self.kill()

# --- OPTIMERAD RITNING ---
def render_grid(w: int, h: int) -> pygame.Surface:
    # Tidigare ritades horisontella stödlinjer här. Nu returneras en tom yta
    # eftersom kunden ville ha bort de horisontella linjerna.
    return pygame.Surface((w, h), pygame.SRCALPHA)

def render_piano(w: int, h: int, active_note: str = None) -> pygame.Surface:
    # Ritar pianot till vänster. active_note markeras blått.
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    v_size = get_white_key_v_size(h)
    
    # Vita tangenter
    for note in WHITE_KEYS:
        r = pygame.Rect(0, white_key_top_y(note, h), WHITE_KEY_H_SIZE, int(v_size))
        color = (0, 150, 255) if note == active_note else (255, 255, 255)
        pygame.draw.rect(surf, color, r)
        pygame.draw.rect(surf, (180, 180, 180), r, width=1)

    # Svarta tangenter
    black_v_size = int(v_size * BLACK_KEY_V_SIZE_RATIO)
    for oct in range(0, 9):
        for bn, previous_white in {
            "Db": "C",
            "Eb": "D",
            "Gb": "F",
            "Ab": "G",
            "Bb": "A",
        }.items():
            nn = f"{bn}{oct}"
            previous_note = f"{previous_white}{oct}"

            if previous_note not in WHITE_KEYS:
                continue

            y = white_key_top_y(previous_note, h) - int(black_v_size / 2)
            r = pygame.Rect(0, y, BLACK_KEY_H_SIZE, black_v_size)
            color = (0, 150, 255) if nn == active_note else (0, 0, 0)
            pygame.draw.rect(surf, color, r); pygame.draw.rect(surf, (60, 60, 60), r, width=1)
    return surf

def draw_frequency_indicator(
    screen: pygame.Surface,
    frequency: float = None,
    strength: float = 0.0,
) -> None:
    # Ritar en ljudvåg högt upp på spelplanen.
    # När mikrofonen är tyst blir strength 0 och vågen blir en platt linje.
    # När ljud finns ökar strength mjukt och vågen får amplitud.
    screen_w, screen_h = screen.get_size()
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    width = max(1, screen_w - WHITE_KEY_H_SIZE)
    start_x = WHITE_KEY_H_SIZE
    y = max(90, screen_h // 7)
    points = []
    has_frequency = frequency is not None
    phase = pygame.time.get_ticks() * 0.008
    amplitude = 42 * max(0.0, min(1.0, strength))
    frequency_amount = (
        max(0.0, min(1.0, (frequency - minimum_frequency) / (maximum_frequency - minimum_frequency)))
        if has_frequency
        else 0.0
    )
    wave_density = 0.035 + frequency_amount * 0.075

    for i in range(width + 1):
        edge_fade = math.sin((i / width) * math.pi)
        wave = (
            math.sin(i * wave_density + phase) * 0.86
            + math.sin(i * wave_density * 2.0 - phase * 0.7) * 0.14
        )
        points.append((start_x + i, y + int(wave * amplitude * edge_fade)))

    for offset, color, line_width in [
        (4, (70, 40, 255, 12), 6),
        (2, (95, 95, 255, 24), 4),
        (0, (155, 230, 255, 105), 1),
    ]:
        shifted_points = [(px, py + offset) for px, py in points]
        pygame.draw.lines(overlay, color, False, shifted_points, line_width)

    screen.blit(overlay, (0, 0))

def run_game(screen: pygame.Surface, clock: pygame.time.Clock, microphone) -> bool:
    # Detta är huvudfunktionen för spelet. Den kör tills användaren trycker
    # Esc för att gå tillbaka till menyn eller stänger fönstret.
    pygame.display.set_caption(f"Frequency game - {microphone['name']}")
    
    def refresh_layout():
        # Anropas vid start och när fönstret ändrar storlek.
        # All grafik som beror på fönsterstorlek räknas om här.
        w, h = screen.get_size()
        if background_path:
            bg = load_image_or_fallback(background_path, (w, h), BACKGROUND_COLOR)
        else:
            bg = render_space_background(w, h)
        return w, h, bg

    w, h, background = refresh_layout()
    cached_grid = render_grid(w, h)
    cached_piano = render_piano(w, h, None)
    
    player = Player(w // 3, h // 3)
    tone_bar_group = pygame.sprite.Group()
    audio = SoundReader(
        device=microphone["index"],
        min_hz=minimum_frequency,
    )
    big_font = pygame.font.Font(None, 40)
    cta_font = pygame.font.Font(None, 48)

    player_visible = False
    game_state = 0; notes_sent = 0; mp3_ticks = 0; pause_timer = 0; none_ticks = 0
    exhaust_particles = []; last_active_note = None
    displayed_wave_frequency = None
    displayed_wave_strength = 0.0
    
    global player_score, player_max_score, last_player_score, last_note_is_hit
    player_score = 0; player_max_score = 0
    
    available_sounds = list(piano_frequencies.keys())
    random.shuffle(available_sounds)

    try:
        audio.start(); audio.start_listening()
        while True:
            clock.tick(FPS)
            w, h = screen.get_size(); target_x = w // 3

            # Läs senaste frekvensen från mikrofonen.
            # Under tiden en notfil spelas ignoreras mikrofonen för att undvika
            # att spelet lyssnar på sin egen uppspelning.
            current_freq = audio.get_latest_frequency() if mp3_ticks <= 0 else None
            current_note = freq_to_note(current_freq) if current_freq else None

            # Ljudvågen ska inte hoppa direkt mellan frekvenser. Därför har den
            # en separat mjukad frekvens och en separat mjukad amplitud.
            if current_freq is None:
                displayed_wave_frequency = None
            elif displayed_wave_frequency is None:
                displayed_wave_frequency = current_freq
            else:
                displayed_wave_frequency += (
                    current_freq - displayed_wave_frequency
                ) * wave_frequency_smoothing

            target_wave_strength = 1.0 if current_freq is not None else 0.0
            displayed_wave_strength += (
                target_wave_strength - displayed_wave_strength
            ) * wave_amplitude_smoothing

            if current_note != last_active_note:
                cached_piano = render_piano(w, h, current_note)
                last_active_note = current_note

            # Hantera tangenttryck, fönsterstängning och fönsterstorlek.
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return True
                if event.type == pygame.VIDEORESIZE:
                    w, h, background = refresh_layout()
                    cached_grid = render_grid(w, h)
                    cached_piano = render_piano(w, h, current_note)
                    for tb in tone_bar_group: tb.update_image(h)

            if player_max_score > 0: last_player_score = (player_score / player_max_score) * 100
            else: last_player_score = 0

            # --- SPELLOGIK ---
            # game_state 0 = aktiv runda, 1 = vänta tills balkar är borta,
            # 2 = visa resultat innan nästa runda startar.
            if game_state == 0:
                if mp3_ticks <= 0:
                    if notes_sent < max_notes:
                        if not available_sounds:
                            available_sounds = list(piano_frequencies.keys()); random.shuffle(available_sounds)
                        note = available_sounds.pop(); freq = piano_frequencies[note]
                        # Skapa en ny tonbalk och spela upp motsvarande ljudfil.
                        tone_bar_group.add(ToneBar(freq, note, h, w))
                        play_mp3(f"{note}.mp3")
                        mp3_ticks = seconds_to_ticks(mp3_seconds + between_mp3_seconds)
                        notes_sent += 1
                    else: game_state = 1
            elif game_state == 1:
                if len(tone_bar_group) == 0:
                    final_score = last_player_score; player_score, player_max_score, notes_sent = 0, 0, 0
                    pause_timer = seconds_to_ticks(7); game_state = 2
            elif game_state == 2:
                pause_timer -= 1
                if pause_timer <= 0: last_player_score, game_state = 0, 0

            if mp3_ticks > 0:
                mp3_ticks -= 1
                if mp3_ticks == 0: stop_mp3()

            # --- SPELARE / MIKROFON ---
            # Om mikrofonen hör en frekvens flyttas raketen till motsvarande Y.
            # Om det är tyst döljs raketen efter en kort stund, om test_mode är False.
            if current_freq is not None:
                none_ticks = 0; player_visible = True
                player.update(freq_to_y(current_freq, h), target_x)
            else:
                none_ticks += 1
                if not test_mode and none_ticks >= seconds_to_ticks(seconds_until_invisible): player_visible = False

            if test_mode:
                player_visible = True

            # Uppdatera tonbalkar och scoring. input_active hindrar tystnad
            # från att räknas som träff, även om raketen står kvar på rätt Y.
            input_active = current_freq is not None
            tone_bar_group.update(player.rect.centery, target_x, h, input_active)

            matching_tone = any(
                input_active
                and
                tone_bar.rect.left <= target_x <= tone_bar.rect.right
                and abs(player.rect.centery - tone_bar.rect.centery) < (tone_bar.rect.height // 2)
                for tone_bar in tone_bar_group
            )

            # --- AVGASPARTIKLAR ---
            # Partiklar skapas bakom raketen. Vid matchning får de grön tint.
            if player_visible:
                exhaust_x = player.rect.left + player.rect.width * 0.18
                exhaust_y = player.rect.centery
                exhaust_matched = matching_tone
                exhaust_color = (0, 255, 100) if matching_tone else (255, 150, 40)

                for _ in range(exhaust_particles_per_frame):
                    offset_x = random.uniform(-4, 10)
                    exhaust_particles.append({
                        "x": exhaust_x + offset_x,
                        "y": exhaust_y + random.uniform(-exhaust_spread, exhaust_spread) * (1 - max(0, offset_x) / 14),
                        "age": 0,
                        "life": exhaust_lifetime + random.randint(-12, 12),
                        "radius": random.uniform(exhaust_start_radius * 0.35, exhaust_start_radius),
                        "drift": random.uniform(-0.45, 0.45),
                        "color": exhaust_color,
                        "matched": exhaust_matched,
                    })

            new_particles = []
            for particle in exhaust_particles:
                particle["age"] += 1
                particle["x"] -= movement_speed
                particle["y"] += particle["drift"]
                particle["drift"] *= 0.98

                if (
                    particle["age"] < particle["life"]
                    and particle["x"] > WHITE_KEY_H_SIZE
                ):
                    new_particles.append(particle)

            exhaust_particles = new_particles[-exhaust_max_particles:]

            # --- RENDER ---
            # Ritar allt i lager: bakgrund, linje, tonbalkar, ljudvåg,
            # avgaser, raket, piano och text.
            screen.blit(background, (0, 0))
            screen.blit(cached_grid, (0, 0)) # Bakgrunden ligger längst bak.

            pygame.draw.line(screen, (100, 100, 100), (target_x, 0), (target_x, h), 2)
            
            # Noter ovanpå bakgrunden
            tone_bar_group.draw(screen)

            draw_frequency_indicator(
                screen,
                displayed_wave_frequency,
                displayed_wave_strength,
            )
            
            # Avgaser ovanpå noter
            if exhaust_particles:
                exhaust_surface = pygame.Surface((w, h), pygame.SRCALPHA)

                for particle in exhaust_particles:
                    progress = particle["age"] / particle["life"]
                    taper = (1 - progress) ** 1.7
                    radius = max(1, int(particle["radius"] * taper))
                    alpha = max(0, int(225 * (1 - progress) ** 1.35))

                    if particle["matched"]:
                        if progress < 0.28:
                            color = (185, 255, 190)
                        elif progress < 0.75:
                            color = particle["color"]
                        else:
                            fade = int(95 * (1 - progress))
                            color = (20, max(35, fade + 45), 35)
                    elif progress < 0.28:
                        color = (255, 245, 170)
                    elif progress < 0.62:
                        color = particle["color"]
                    else:
                        smoke = int(120 * (1 - progress))
                        color = (smoke, smoke, smoke + 20)

                    pygame.draw.circle(
                        exhaust_surface,
                        (*color, alpha),
                        (int(particle["x"]), int(particle["y"])),
                        radius,
                    )

                screen.blit(exhaust_surface, (0, 0))
            
            if player_visible: screen.blit(player.image, player.rect)
            
            # Pianot ligger överst
            screen.blit(cached_piano, (0, 0))
            
            cta_surf = cta_font.render("Matcha tonen!", True, (255, 255, 255))
            screen.blit(cta_surf, (w // 2 - cta_surf.get_width() // 2, 20))
            score_surf = big_font.render(f"Match: {last_player_score:.0f}%", True, (255, 255, 255))
            screen.blit(score_surf, (w - score_surf.get_width() - 40, 20))

            if game_state == 2:
                r_w, r_h = 600, 300; r_x, r_y = (w // 2) - (r_w // 2), (h // 2) - (r_h // 2)
                pygame.draw.rect(screen, (255, 255, 255), (r_x, r_y, r_w, r_h), border_radius=20)
                pygame.draw.rect(screen, (0, 0, 0), (r_x, r_y, r_w, r_h), 4, border_radius=20)
                bar_w, bar_h = 500, 40; bar_x, bar_y = r_x + 50, r_y + 140
                pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h))
                fill_w = int((final_score / 100) * bar_w)
                if fill_w > 0: pygame.draw.rect(screen, (50, 205, 50), (bar_x, bar_y, fill_w, bar_h))
                t1 = big_font.render("Snyggt jobbat!", True, (255, 100, 0))
                t2 = big_font.render(f"Match: {final_score:.0f}%", True, (0, 0, 0))
                sec = math.ceil(pause_timer / FPS)
                t3 = big_font.render(f"Nästa runda om: {sec}s", True, (100, 100, 100))
                screen.blit(t1, (r_x + r_w // 2 - t1.get_width() // 2, r_y + 40))
                screen.blit(t2, (r_x + r_w // 2 - t2.get_width() // 2, r_y + 90))
                screen.blit(t3, (r_x + r_w // 2 - t3.get_width() // 2, r_y + 230))
            pygame.display.flip()

    finally:
        stop_mp3(); audio.stop()
