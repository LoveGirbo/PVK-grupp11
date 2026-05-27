import pygame

from menu import choose_microphone
from game import run_game, SCREEN_WIDTH, SCREEN_HEIGHT


def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
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