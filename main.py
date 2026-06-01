import pygame

from menu import choose_microphone
from game import run_game, SCREEN_WIDTH, SCREEN_HEIGHT


def main() -> None:
    # Pygame måste startas innan fönster, bilder, ljud och fonter kan användas.
    pygame.init()

    # RESIZABLE gör att användaren kan ändra fönsterstorlek.
    # Spelet räknar om layouten när fönstret ändras.
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    running = True

    while running:
        # Först visas en meny där användaren väljer mikrofon.
        microphone = choose_microphone(screen, clock)

        if microphone is None:
            running = False
        else:
            # run_game returnerar True om användaren trycker Esc för att gå
            # tillbaka till mikrofonmenyn, och False om hela programmet ska sluta.
            back_to_menu = run_game(screen, clock, microphone)
            if not back_to_menu:
                running = False

    # Stänger pygame snyggt när programmet avslutas.
    pygame.quit()


if __name__ == "__main__":
    main()
