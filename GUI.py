import pygame
from pygame.locals import *

pygame.init()

clock = pygame.time.Clock()
fps = 60

screen_width = 800
screen_height = 600

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Frequency game")

# Load images
# background = pygame.image.load("images/Background.jpg")

class Player_class(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load("images/Player_sprite.png")
        self.rect = self.image.get_rect()
        self.rect.center = x, y

player_group = pygame.sprite.Group()
player1 = Player_class(int(screen_width/2), int(screen_height/2))
player_group.add(player1)

run = True
while run:

    clock.tick(fps)

    # screen.blit(background, (0, 0))
    player_group.draw(screen)



    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    pygame.display.update()

pygame.quit()






