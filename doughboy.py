# top level file for the doughboy project

import json
import os
import logging, logging.config
import trio
import configparser
from dough_controller import Controller

# FIXME: need to get proper paths for these config/ini files!

logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)
log = logging.getLogger(__name__)

_INI_FILENAME = "doughboy.ini"
_iniFileStamp = 0

def readIni():

    parser = configparser.ConfigParser()
    parser.read(_INI_FILENAME)
    log.debug("=======================================================")
    config = {
        "pwmPeriod" : parser["CONTROL"].getfloat("pwmPeriod"),
        "preheatCycles": parser["CONTROL"].getfloat("preheatCycles"),
        "preheatThreshold": parser["CONTROL"].getfloat("preheatThreshold"),
        "preheatPowerLevel": parser["CONTROL"].getfloat("preheatPowerLevel"),
        "setPoint" : parser["CONTROL"].getfloat("setPoint"),
        "topicStatus" : parser["CONTROL"].get("topicStatus"),
        "topicPlugCommand" : parser["CONTROL"].get("topicPlugCommand"),
        "kP" : parser["CONTROL"].getfloat("kP"),
        "kI" : parser["CONTROL"].getfloat("kI"),
        "kD" : parser["CONTROL"].getfloat("kD"),
        "enablePID" : parser["CONTROL"].getboolean("enablePID"),
        "enableOut" : parser["CONTROL"].getboolean("enableOut"),
        "preheatAutoEnablePidAfter" : parser["CONTROL"].getboolean("preheatAutoEnablePidAfter"),
        "initialIntegralSum" : parser["CONTROL"].getfloat("initialIntegralSum"),
    }
    log.debug("read ini file: " + json.dumps(config, indent=2, sort_keys=True))

    return config

def checkIniFileChange(controller:Controller):
    global _iniFileStamp
    stamp = os.stat(_INI_FILENAME).st_mtime
    if (stamp != _iniFileStamp):
        log.debug(f"ini file changed ({stamp}) configure from ini file")
        _iniFileStamp = stamp
        # configure from the ini file
        controller.configure(readIni())

async def watchIniFile(controller:Controller):
    # poll for ini file changes
    while True:
        checkIniFileChange(controller)
        await trio.sleep(30)

async def main(controller:Controller):
    log.debug("starting controller main...")
    async with trio.open_nursery() as nursery:
        log.info("spawning loop")
        nursery.start_soon(controller.controlLoop, nursery)
        nursery.start_soon(watchIniFile, controller)

def run(controller:Controller):
    try:
        trio.run(main, controller)
    except KeyboardInterrupt as exc:
        log.info("bye bye")
    finally:
        controller.cleanup()

if __name__ == "__main__":

    # signal.signal(signal.SIGINT, handle_sigint)

    # initial configure controller from ini file
    controller = Controller(readIni())
    run(controller)
