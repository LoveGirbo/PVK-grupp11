# Frequency Game

A small pygame pitch-matching game. The app plays piano notes, listens to the
selected microphone, and scores how closely the incoming pitch follows the note
bars on screen.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pygame sounddevice numpy
```

## Run

Start the game with:

```bash
python3 main.py
```

Choose a microphone from the menu with the arrow keys or mouse, then press
Enter, Space, or the Start button.

## Controls

- `Up` / `Down`: choose a microphone in the menu
- `Mouse wheel`: scroll through microphones
- `R`: refresh the microphone list
- `Enter` / `Space`: start with the selected microphone
- `Esc`: return from the game to the microphone menu, or quit from the menu

## Project Files

- `main.py`: application loop
- `menu.py`: microphone selection screen
- `game.py`: game rendering, scoring, and note spawning
- `audio_reader.py`: live microphone pitch detection
- `audio/`: note playback files
