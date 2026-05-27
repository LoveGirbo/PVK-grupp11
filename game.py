import os
import random
import pygame
import math

from audio_reader import SoundReader

# --- CONSTANTS ---
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 120
BACKGROUND_COLOR = (0, 0, 0)
TEXT_COLOR = (235, 235, 235)

# Game logic
max_notes = 3
mp3_seconds = 1.5
between_mp3_seconds = 0.1
seconds_until_invisible = 0.1
tone_delta_threshold = 10

# Movement
movement_speed = 1
movement_smoothing = 5

# Player visuals
player_size = 20
player_colour = (240, 240, 20)

# Tone bar visuals
tone_bar_alpha = 200 # More solid
tone_bar_colour = (0, 204, 255)

# Audio
minimum_frequency = 180.0
maximum_frequency = 610.0
dB_threshold = 50.0
AUDIO_FOLDER = "audio"
background_path = ""

# Piano drawing constants
PIANO_Y_OFFSET = 10
WHITE_KEY_H_SIZE = 140
BLACK_KEY_V_SIZE_RATIO = 0.6
BLACK_KEY_H_SIZE = 90

# Globals for scoring
player_score = 0
player_max_score = 0
last_player_score = 0.0
last_note_is_hit = False

# --- MUSICAL DATA ---
NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

WHITE_KEYS = []
for oct in range(0, 9):
    for n in ["C", "D", "E", "F", "G", "A", "B"]:
        name = f"{n}{oct}"
        if oct == 0 and n not in ["A", "B"]: continue
        if oct == 8 and n != "C": continue
        WHITE_KEYS.append(name)

piano_frequencies = {
    "G3": 196.00, "Ab3": 207.65, "A3": 220.00, "Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "Db4": 277.18, "D4": 293.66, "Eb4": 311.13, "E4": 329.63,
    "F4": 349.23, "Gb4": 369.99, "G4": 392.00, "Ab4": 415.30, "A4": 440.00,
    "Bb4": 466.16, "B4": 493.88,
    "C5": 523.25, "Db5": 554.37, "D5": 587.33, "Eb5": 622.25
}

# --- HELPERS ---
def get_white_key_v_size(screen_h: int) -> float:
    return max(1.0, (screen_h - (2 * PIANO_Y_OFFSET)) / len(WHITE_KEYS))

def freq_to_note(freq: float) -> str:
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
    if not note_name: return -100
    v_size = get_white_key_v_size(screen_h)
    is_black = "b" in note_name
    
    if is_black:
        note_prefix = note_name[0:2]
        try:
            octave = int(note_name[2:])
            offsets = {"Db": 0.7, "Eb": 1.7, "Gb": 3.7, "Ab": 4.7, "Bb": 5.7}
            c_index = WHITE_KEYS.index(f"C{octave}")
            rel_pos = offsets[note_prefix]
            return PIANO_Y_OFFSET + int((c_index + rel_pos) * v_size) + int(v_size * BLACK_KEY_V_SIZE_RATIO) // 2
        except: return -100
    else:
        try:
            idx = WHITE_KEYS.index(note_name)
            return PIANO_Y_OFFSET + int(idx * v_size + v_size // 2)
        except: return -100

def freq_to_y(freq: float, screen_h: int) -> int:
    note = freq_to_note(freq)
    y = get_note_y(note, screen_h)
    if y < 0:
        freq_range = maximum_frequency - minimum_frequency
        f = max(minimum_frequency, min(maximum_frequency, freq))
        return int(screen_h - ((f - minimum_frequency) * (screen_h / freq_range)))
    return y

def load_image_or_fallback(path: str, size: tuple[int, int], fill_color: tuple[int, int, int]) -> pygame.Surface:
    if path and os.path.exists(path):
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(image, size)
        except: pass
    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(fill_color)
    return surface

def seconds_to_ticks(seconds: float) -> int:
    return int(seconds * FPS)

def play_mp3(filename: str) -> None:
    path = os.path.join(AUDIO_FOLDER, filename)
    if not os.path.exists(path): return
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()

def stop_mp3() -> None:
    pygame.mixer.music.stop()

# --- CLASSES ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__()
        self.image = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, player_colour, (player_size // 2, player_size // 2), player_size // 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.center_y = float(self.rect.centery)

    def update(self, new_y: float, target_x: int) -> None:
        speed = 1 / movement_smoothing
        self.center_y += (new_y - self.center_y) * speed
        self.rect.centery = round(self.center_y)
        self.rect.centerx = target_x

class ToneBar(pygame.sprite.Sprite):
    def __init__(self, frequency: float, note_name: str, screen_h: int, screen_w: int):
        super().__init__()
        self.frequency = frequency
        self.note_name = note_name
        self.width = int(mp3_seconds * FPS * movement_speed)
        self.update_image(screen_h)
        self.rect = self.image.get_rect(midleft=(screen_w, freq_to_y(frequency, screen_h)))

    def update_image(self, screen_h: int):
        v_size = get_white_key_v_size(screen_h)
        # Scaled down by 25% from 3.6x -> 2.7x
        h = max(30, int(v_size * 2.7)) 
        self.image = pygame.Surface((self.width, h), pygame.SRCALPHA)
        br = h // 4
        
        pygame.draw.rect(self.image, (*tone_bar_colour, tone_bar_alpha), (0, 0, self.width, h), border_radius=br)
        pygame.draw.rect(self.image, (255, 255, 255, 220), (0, 0, self.width, h), width=3, border_radius=br)
        
        # Text size increased slightly
        font_size = max(26, int(h * 0.5))
        font = pygame.font.Font(None, font_size)
        label = f"{self.note_name} - {int(self.frequency)} Hz"
        txt = font.render(label, True, (255, 255, 255))
        self.image.blit(txt, txt.get_rect(center=(self.width // 2, h // 2)))

    def update(self, player_y: float, target_x: int, screen_h: int) -> None:
        self.rect.x -= movement_speed
        self.rect.centery = freq_to_y(self.frequency, screen_h)
        
        if self.rect.left <= target_x <= self.rect.right:
            global player_max_score, player_score, last_note_is_hit
            player_max_score += 1
            # Dynamic threshold based on actual graphic height
            if abs(player_y - self.rect.centery) < (self.rect.height // 2):
                player_score += 1
                last_note_is_hit = True
            else: last_note_is_hit = False
        
        # Stop rendering when it passes the piano (WHITE_KEY_H_SIZE)
        if self.rect.right < WHITE_KEY_H_SIZE: self.kill()

# --- OPTIMIZED DRAWING ---
def render_grid(w: int, h: int) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    v_size = get_white_key_v_size(h)
    for i in range(len(WHITE_KEYS)):
        gy = PIANO_Y_OFFSET + int(i * v_size + v_size // 2)
        pygame.draw.line(surf, (45, 45, 45), (0, gy), (w, gy), 1)
    return surf

def render_piano(w: int, h: int, active_note: str = None) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    v_size = get_white_key_v_size(h)
    
    # White keys
    for i, note in enumerate(WHITE_KEYS):
        r = pygame.Rect(0, PIANO_Y_OFFSET + int(i * v_size), WHITE_KEY_H_SIZE, int(v_size))
        color = (0, 150, 255) if note == active_note else (255, 255, 255)
        pygame.draw.rect(surf, color, r)
        pygame.draw.rect(surf, (180, 180, 180), r, width=1)

    # Black keys
    black_v_size = int(v_size * BLACK_KEY_V_SIZE_RATIO)
    for oct in range(0, 9):
        try:
            ci = WHITE_KEYS.index(f"C{oct}")
            for i, bn in enumerate(["Db", "Eb", "Gb", "Ab", "Bb"]):
                nn = f"{bn}{oct}"; rp = [0.7, 1.7, 3.7, 4.7, 5.7][i]
                r = pygame.Rect(0, PIANO_Y_OFFSET + int((ci + rp) * v_size), BLACK_KEY_H_SIZE, black_v_size)
                color = (0, 150, 255) if nn == active_note else (0, 0, 0)
                pygame.draw.rect(surf, color, r); pygame.draw.rect(surf, (60, 60, 60), r, width=1)
        except ValueError: continue
    return surf

def run_game(screen: pygame.Surface, clock: pygame.time.Clock, microphone) -> bool:
    pygame.display.set_caption(f"Frequency game - {microphone['name']}")
    
    def refresh_layout():
        w, h = screen.get_size()
        bg = load_image_or_fallback(background_path, (w, h), BACKGROUND_COLOR)
        return w, h, bg

    w, h, background = refresh_layout()
    cached_grid = render_grid(w, h)
    cached_piano = render_piano(w, h, None)
    
    player = Player(w // 3, h // 3)
    tone_bar_group = pygame.sprite.Group()
    audio = SoundReader()
    big_font = pygame.font.Font(None, 40)
    cta_font = pygame.font.Font(None, 48)

    player_visible = False
    game_state = 0; notes_sent = 0; mp3_ticks = 0; pause_timer = 0; none_ticks = 0
    player_trail_points = []; last_active_note = None
    
    global player_score, player_max_score, last_player_score, last_note_is_hit
    player_score = 0; player_max_score = 0
    
    available_sounds = list(piano_frequencies.keys())
    random.shuffle(available_sounds)

    try:
        audio.start(); audio.start_listening()
        while True:
            clock.tick(FPS)
            w, h = screen.get_size(); target_x = w // 3
            current_freq = audio.get_latest_frequency() if mp3_ticks <= 0 else None
            un = freq_to_note(current_freq) if current_freq else None

            if un != last_active_note:
                cached_piano = render_piano(w, h, un)
                last_active_note = un

            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return True
                if event.type == pygame.VIDEORESIZE:
                    w, h, background = refresh_layout()
                    cached_grid = render_grid(w, h)
                    cached_piano = render_piano(w, h, un)
                    for tb in tone_bar_group: tb.update_image(h)

            if player_max_score > 0: last_player_score = (player_score / player_max_score) * 100
            else: last_player_score = 0

            if game_state == 0:
                if mp3_ticks <= 0:
                    if notes_sent < max_notes:
                        if not available_sounds:
                            available_sounds = list(piano_frequencies.keys()); random.shuffle(available_sounds)
                        note = available_sounds.pop(); freq = piano_frequencies[note]
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

            if current_freq is not None:
                none_ticks = 0; player_visible = True
                player.update(freq_to_y(current_freq, h), target_x)
            else:
                none_ticks += 1
                if none_ticks >= seconds_to_ticks(seconds_until_invisible): player_visible = False

            if player_visible: player_trail_points.insert(0, (target_x, player.rect.centery))
            new_trail = []
            for (tx, ty) in player_trail_points:
                nx = tx - movement_speed
                # Boundary check: Stop rendering trail when it hits the piano
                if nx > WHITE_KEY_H_SIZE: new_trail.append((nx, ty))
            player_trail_points = new_trail[:400]
            tone_bar_group.update(player.rect.centery, target_x, h)

            # --- RENDER ---
            screen.blit(background, (0, 0))
            screen.blit(cached_grid, (0, 0)) # Grid is furthest back
            
            # Hit line above grid
            pygame.draw.line(screen, (100, 100, 100), (target_x, 0), (target_x, h), 2)
            
            # Notes above grid
            tone_bar_group.draw(screen)
            
            # Trail above notes
            if len(player_trail_points) > 1:
                color = (0, 255, 100) if last_note_is_hit else player_colour
                pygame.draw.lines(screen, color, False, player_trail_points, 5)
            
            if player_visible: screen.blit(player.image, player.rect)
            
            # Piano is on top
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
