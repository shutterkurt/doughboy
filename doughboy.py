# top level file for the doughboy project

import ui
import sensor
import mqtt

import json
import time, math
import signal
import sys
import logging, logging.config
import trio
import configparser

logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)

def handle_sigint(sig, frame):
    print('bye bye')
    mqtt.cleanup()
    sys.exit(0)


if __name__ == "__main__":

    signal.signal(signal.SIGINT, handle_sigint)
    config = configparser.ConfigParser()
    config.read("doughboy.ini")
    LOGGER.debug("read ini file: " + str(config))
    pwmPeriod = config["CONTROL"].getfloat("pwmPeriod")
    setPoint = config["CONTROL"].getfloat("setPoint")


    ui.cls()
    print('Press Ctrl-C to stop...')
    while True:
        start = time.time()
        newTemp = sensor.tempF()
        LOGGER.info("curTemp= " + str(newTemp))
        # FIXME: look into why updateScreen takes ~2 seconds!!
        ui.updateScreen(setPoint, newTemp, 0)
        payload = {"curTemp": newTemp}
        mqtt.publish(json.dumps(payload))
        
        # subtract off elapsed time from above processing
        # from the period to get sleep time
        elapsed = int(time.time() - start)
        now = time.time()
        remainder = math.ceil(now) - now
        time.sleep(pwmPeriod - elapsed - 1 + remainder)
