# Running the Program

## 1. List available microphones

Before starting the program, check which microphone devices are available:

```bash
python3 main.py -l
```

## 2. Start the main loop

Run the main loop with:

```bash
python3 main.py -d 2 -t -25 -s 5 --pause 7
```

To stop the program, press:

```text
Ctrl + C
```

## Parameters

### Required parameters

- `-d`  
  Selects which microphone device to use.

- `-t`  
  Sets the decibel threshold in dBFS.

- `-s`  
  Sets how long the input is measured, in seconds.

- `--pause`  
  Sets how long the result is displayed before the next measurement starts, in seconds.

### Optional parameters

- `--gate-db`  
  While recording input, only dBFS values above this threshold will be registered.  
  This helps reduce background noise.

## Example

```bash
python3 main.py -d 2 -t -25 -s 5 --pause 7
```

This example:
- uses microphone device `2`
- sets the threshold to `-25 dBFS`
- measures input for `5` seconds
- waits `7` seconds before allowing the next measurement
