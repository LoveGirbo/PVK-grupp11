import pygame

from audio_reader import list_input_devices

FPS = 60

BG_COLOR = (20, 24, 32)
PANEL_COLOR = (35, 40, 52)
HIGHLIGHT_COLOR = (70, 130, 220)
TEXT_COLOR = (235, 235, 235)
SUBTEXT_COLOR = (180, 180, 180)
BUTTON_COLOR = (60, 160, 90)
BUTTON_DISABLED = (80, 80, 80)


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


def fit_text(text: str, font: pygame.font.Font, max_width: int) -> str:
    if font.size(text)[0] <= max_width:
        return text

    ellipsis = "..."
    available_width = max_width - font.size(ellipsis)[0]

    if available_width <= 0:
        return ellipsis

    fitted = text
    while fitted and font.size(fitted)[0] > available_width:
        fitted = fitted[:-1]

    return fitted + ellipsis


def choose_microphone(screen: pygame.Surface, clock: pygame.time.Clock):
    pygame.display.set_caption("Frequency game - microphone selection")

    title_font = pygame.font.Font(None, 52)
    text_font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 26)

    devices = list_input_devices()
    selected = 0
    scroll_offset = 0

    while True:
        clock.tick(FPS)

        screen_w, screen_h = screen.get_size()
        list_top = 140
        item_height = 48
        list_bottom = screen_h - 100
        visible_count = max(1, (list_bottom - list_top) // item_height)

        if selected < scroll_offset:
            scroll_offset = selected
        elif selected >= scroll_offset + visible_count:
            scroll_offset = selected - visible_count + 1

        start_button = pygame.Rect(max(200, screen_w - 220), screen_h - 80, 160, 44)
        refresh_button = pygame.Rect(40, screen_h - 80, 140, 44)

        item_rects = []
        visible_devices = devices[scroll_offset:scroll_offset + visible_count]

        for i, _device in enumerate(visible_devices):
            y = list_top + i * item_height
            rect = pygame.Rect(40, y, max(120, screen_w - 80), 40)
            item_rects.append((rect, scroll_offset + i))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None

                if event.key == pygame.K_r:
                    devices = list_input_devices()
                    if devices:
                        selected = min(selected, len(devices) - 1)
                    else:
                        selected = 0

                if devices:
                    if event.key == pygame.K_DOWN:
                        selected = min(selected + 1, len(devices) - 1)
                    elif event.key == pygame.K_UP:
                        selected = max(selected - 1, 0)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return devices[selected]

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                if refresh_button.collidepoint(mouse_pos):
                    devices = list_input_devices()
                    if devices:
                        selected = min(selected, len(devices) - 1)
                    else:
                        selected = 0

                if devices and start_button.collidepoint(mouse_pos):
                    return devices[selected]

                for rect, index in item_rects:
                    if rect.collidepoint(mouse_pos):
                        selected = index

            if event.type == pygame.MOUSEWHEEL and devices:
                selected = max(0, min(selected - event.y, len(devices) - 1))

        screen.fill(BG_COLOR)

        draw_text(screen, "Choose microphone", title_font, TEXT_COLOR, 40, 40)
        draw_text(
            screen,
            "Use arrow keys or mouse. Press Enter/Space to start. Press R to refresh.",
            small_font,
            SUBTEXT_COLOR,
            40,
            95,
        )

        if not devices:
            draw_text(screen, "No input microphones found.", text_font, TEXT_COLOR, 40, 160)
            draw_text(screen, "Connect a microphone and press R to refresh.", text_font, SUBTEXT_COLOR, 40, 200)
        else:
            for rect, index in item_rects:
                device = devices[index]
                is_selected = index == selected

                pygame.draw.rect(
                    screen,
                    HIGHLIGHT_COLOR if is_selected else PANEL_COLOR,
                    rect,
                    border_radius=8,
                )

                device_text = fit_text(
                    f"[{device['index']}] {device['name']}",
                    small_font,
                    rect.width - 24,
                )

                draw_text(
                    screen,
                    device_text,
                    small_font,
                    TEXT_COLOR,
                    rect.x + 12,
                    rect.y + 10,
                )

        pygame.draw.rect(screen, PANEL_COLOR, refresh_button, border_radius=8)
        draw_text(screen, "Refresh (R)", text_font, TEXT_COLOR, refresh_button.x + 14, refresh_button.y + 10)

        pygame.draw.rect(
            screen,
            BUTTON_COLOR if devices else BUTTON_DISABLED,
            start_button,
            border_radius=8,
        )
        draw_text(screen, "Start", text_font, TEXT_COLOR, start_button.x + 48, start_button.y + 10)

        pygame.display.flip()
