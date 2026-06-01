# Frequency Game

Ett interaktivt frekvens-spel byggt med Python och pygame. Spelet spelar upp
pianotoner, lyssnar på spelarens röst via mikrofonen och låter spelaren styra
en raket genom att matcha tonhöjden.

## Vad Spelet Gör

- Spelar upp en pianoton från mappen `audio/`.
- Skapar en blå ruta som rör sig från höger till vänster.
- Läser av aktuell frekvens från mikrofonen.
- Flyttar raketen uppåt/nedåt beroende på spelarens tonhöjd.
- Ger poäng när raketen matchar tonen vid den vertikala linjen.
- Visar gröna avgaser när spelaren matchar tonen.

## Installation

Installera paket:

```bash
pip install pygame sounddevice numpy
```

På vissa datorer kan `sounddevice` kräva att PortAudio finns installerat.
På macOS kan det installeras med Homebrew:

```bash
brew install portaudio
```

## Starta Programmet

Kör:

```bash
python3 main.py
```

Välj mikrofon i menyn med piltangenterna eller musen och starta med Enter,
Space eller Start-knappen.

## Kontroller

- `Up` / `Down`: välj mikrofon i menyn
- `Mouse wheel`: scrolla i mikrofonlistan
- `R`: uppdatera mikrofonlistan
- `Enter` / `Space`: starta spelet med vald mikrofon
- `Esc`: gå tillbaka från spelet till menyn, eller avsluta från menyn

## Projektets Viktiga Filer

- `main.py`: startar pygame, öppnar fönstret och växlar mellan meny och spel.
- `menu.py`: visar mikrofonmenyn och låter användaren välja input.
- `game.py`: innehåller själva spelet, raketen, tonbalkarna, poängräkning och grafik.
- `audio_reader.py`: läser mikrofonljud och räknar ut aktuell frekvens i Hz.
- `audio/`: innehåller pianoljudfiler som `C4.mp3`, `A4.mp3` osv.
- `images/Player_sprite.png`: raketbilden som används som spelare.

## Vanliga Inställningar

De flesta spelinställningar finns högst upp i `game.py`.

Bra variabler att känna till:

- `test_mode`: sätt till `True` om raketen alltid ska synas vid test.
- `mouse_mode`: sätt till `True` om raketen ska styras med musen istället för rösten.
- `max_notes`: antal noter per runda.
- `piano_frequencies`: vilka noter som kan spawna som tonbalkar.
- `VISIBLE_LOW_NOTE` / `VISIBLE_HIGH_NOTE`: vilket pianoregister som visas.
- `minimum_frequency` / `maximum_frequency`: frekvensspannet som visas i spelet.
- `movement_smoothing`: hur mjukt raketen följer mikrofonen.
- `match_grace_frames`: hur snällt spelet är efter en korrekt matchning.
- `wave_frequency_smoothing`: hur mjukt ljudvågen byter form mellan toner.
- `wave_amplitude_smoothing`: hur mjukt ljudvågen går mellan platt och aktiv.

## Lägga Till Eller Ändra Toner

Tonerna väljs från `piano_frequencies` i `game.py`.

Exempel:

```python
piano_frequencies = {
    "C4": 261.63,
    "D4": 293.66,
}
```

Viktigt: varje not i `piano_frequencies` måste ha en matchande ljudfil i
`audio/`. Om spelet ska spawna `C4` måste filen `audio/C4.mp3` finnas.

## Felsökning

Om ingen mikrofon syns:

- Kontrollera att datorn har gett terminalen/Python mikrofontillgång.
- Tryck `R` i mikrofonmenyn för att läsa om listan.
- Testa en annan mikrofon.

Om raketen inte rör sig:

- Kontrollera att rätt mikrofon valts.
- Testa att sjunga/humma tydligare och närmare mikrofonen.
- Se över `gate_db` i `audio_reader.py` om mikrofonen är väldigt tyst.

Om en ton inte spelas:

- Kontrollera att ljudfilen finns i `audio/`.
- Filnamnet måste matcha noten exakt, till exempel `Db4.mp3`.
