import pygame

from menu import choose_microphone
from game import run_game, SCREEN_WIDTH, SCREEN_HEIGHT


def main() -> None:
    # Pygame maste startas innan fonster, bilder, ljud och fonter kan anvandas.
    pygame.init()

    # RESIZABLE gor att anvandaren kan andra fonsterstorlek.
    # Spelet raknar om layouten nar fonstret andras.
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    running = True

    while running:
        # Forst visas en meny dar anvandaren valjer mikrofon.
        microphone = choose_microphone(screen, clock)

        if microphone is None:
            running = False
        else:
            # run_game returnerar True om anvandaren trycker Esc for att ga
            # tillbaka till mikrofonmenyn, och False om hela programmet ska sluta.
            back_to_menu = run_game(screen, clock, microphone)
            if not back_to_menu:
                running = False

    # Stanger pygame snyggt nar programmet avslutas.
    pygame.quit()


if __name__ == "__main__":
    main()
