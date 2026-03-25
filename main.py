import pygame

from menu import choose_microphone
from game import run_game


SCREEN_WIDTH = 900
SCREEN_HEIGHT = 650


def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    running = True

    while running:
        microphone = choose_microphone(screen, clock)

        if microphone is None:
            running = False
        else:
            back_to_menu = run_game(screen, clock, microphone)
            if not back_to_menu:
                running = False

    pygame.quit()


if __name__ == "__main__":
    main()