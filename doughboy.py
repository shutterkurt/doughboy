# top level file for the doughboy project

import ui
import sensor
import mqtt

import json
import time
import signal
import sys

def handle_sigint(sig, frame):
    print('bye bye')
    mqtt.cleanup()
    sys.exit(0)
    
signal.signal(signal.SIGINT, handle_sigint)

ui.cls()
print('Press Ctrl-C to stop...')
while True:
    newTemp = sensor.tempF()
    ui.updateScreen(78, newTemp, 0)
    payload = {"curTemp":newTemp}
    mqtt.publish(json.dumps(payload))
    time.sleep(120)