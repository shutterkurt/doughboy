# top level file for the doughboy project

import ui
import sensor

import time
import signal
import sys

def handle_sigint(sig, frame):
    print('bye bye')
    sys.exit(0)
    
signal.signal(signal.SIGINT, handle_sigint)

ui.cls()
print('Press Ctrl-C to stop...')
while True:
    ui.updateScreen(78, c2f(sensor.tempF()), 0)
    time.sleep(2)