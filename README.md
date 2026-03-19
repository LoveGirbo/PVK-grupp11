How to run the main.py file

1. Select microhone
List available device microphones:
python3 Test2.py -l

2. Main loop 
Start the main loop:
python3 Test2.py -d 2 -t -25 -s 5 --pause 7

Stop the main loop:
crtl + c

Mandatory parameters:
-d selects microphone
-t is the decible threshhold in (dBFS, computer meassured dB)
-s how long the input will be measured (seconds)
--pause how long the output will be diplayed before next measurement can be done (seconds)

Additional parameter:
--gate-db while recording input, only dBFS above this value will be registered to avoid noise being picked up (dBFS)
