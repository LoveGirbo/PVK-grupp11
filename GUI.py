import pygame
from pygame.locals import *
from audio_reader import SoundReader

pygame.init()

clock = pygame.time.Clock()
fps = 60

screen_width = 800
screen_height = 600

current_frequency = None

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Frequency game")

# Load images
background = pygame.image.load("images/Background.jpg")

def freq_to_y(freq) -> int:
    freq_min = float(200)
    freq_max = float(500)
    freq_range = freq_max - freq_min

    if freq < freq_min:
        freq = freq_min
    elif freq > freq_max:
        freq = freq_max

    return int((freq-freq_min) * (screen_height / freq_range)) # max freq = max y value

audio = SoundReader(
    device=1,
    gate_db=-40.0,
    min_hz=20.0,
)

audio.start()

class Player_class(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.image.load("images/Player_sprite.png")
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.y = float(self.rect.y)

    def update(self, new_y):
        speed = 0.1
        self.y += (new_y - self.y) * speed
        self.rect.y = int(self.y)

player_group = pygame.sprite.Group()
player1 = Player_class(int(screen_width/2), int(screen_height/2))
player_group.add(player1)

run = True
listening_started = False

while run:

    clock.tick(fps)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                audio.start_listening()
                listening_started = True

    current_frequency = audio.get_latest_frequency()
    print(current_frequency)

    if current_frequency is not None:
        player_group.update(freq_to_y(current_frequency))
    else:
        player_group.update(screen_height/2)
    screen.blit(background, (0, 0))
    player_group.draw(screen)

    pygame.display.update()

audio.stop()
pygame.quit()






