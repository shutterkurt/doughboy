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
from simple_pid import PID

logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)
log = logging.getLogger(__name__)

class Controller:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read("doughboy.ini")
        log.debug("read ini file: " + str(config))
        self.pwmPeriod = config["CONTROL"].getfloat("pwmPeriod")
        self.setPoint = config["CONTROL"].getfloat("setPoint")
        self.topicStatus = config["CONTROL"].get("topicStatus")
        self.topicPlugCommand = config["CONTROL"].get("topicPlugCommand")

        # create the PID controller:
        kP = config["CONTROL"].getfloat("kP")
        kI = config["CONTROL"].getfloat("kI")
        kD = config["CONTROL"].getfloat("kD")
        self.pid = PID(kP, kI, kD, self.setPoint)
        #self.pid.sample_time = self.pwmPeriod - 1   #make sure it runs when called at pwmPeriod
        self.pid.output_limits = (0, 10)
        self.pid.auto_mode = True
        # can't turn this on till we have proper constants! otherwise delta input T ~0
        #self.pid.proportional_on_measurement = True

    def turnOn(self):
        log.debug("turning on...")
        # THINK: avoid an mqtt message by listening to plug state?
        # mqtt.publish("On", self.topicPlugCommand)

    def turnOff(self, reason="none"):
        log.debug(f'turning off ({reason})...')
        # THINK: avoid an mqtt message by listening to plug state?
        mqtt.publish("Off", self.topicPlugCommand)

    def cleanup(self):
        log.info("cleaning up...")
        self.turnOff("cleanup")
        mqtt.cleanup()

    async def sleepFor(self, rawTime):
        #calculate actual sleep time taking into account processing time up to this call
        # i.e. if rawTime is 10 seconds, but processing took 2 so far, then only sleep for 8
        elapsed = int(trio.current_time() - self.start)
        now = trio.current_time()
        remainder = math.ceil(now) - now
        sleepTime = rawTime - elapsed - 1 + remainder
        log.debug(f'sleepFor: actual sleep time ({sleepTime})')
        await trio.sleep(sleepTime)


    async def turnOffLater(self, level):
        sleepTime = 10 * level * self.pwmPeriod / 100
        log.debug(f'turnOffLater: level ({level}) period ({self.pwmPeriod}) sleeptime ({sleepTime})')
        await self.sleepFor(sleepTime)
        self.turnOff("turnOffLater")

    def setPower(self, level, nursery):
        log.debug(f'setting power to ({level})')
        if (level == 0):
            self.turnOff("setPower")
        else:
            self.turnOn()
            if (level != 10):
                nursery.start_soon(self.turnOffLater,level)


    async def controlLoop(self, nursery):
        log.info("starting control loop...")

        ui.cls()
        print('Press Ctrl-C to stop...')
        while True:
            # keep track of how long all of this takes
            self.start = trio.current_time()
            
            #get new current temperature
            newTemp = sensor.tempF()
            log.info("curTemp= " + str(newTemp))

            # call the pid to get new power level & set the output accordingly
            level = int(self.pid(newTemp) + 0.5)
            log.debug(f'pid output level ({level})')
            log.debug(f'pid components ({self.pid.components})')

            # level = 0
            self.setPower(level, nursery)

            # update the screen
            # FIXME: look into why updateScreen takes ~2 seconds!!
            ui.updateScreen(self.setPoint, newTemp, level)

            # publish the payload
            payload = {
                "curTemp": newTemp,
                "setPoint": self.setPoint,
                "level": level
                }
            mqtt.publish(json.dumps(payload), self.topicStatus)
            
            await self.sleepFor(self.pwmPeriod)


    async def main(self):
        log.debug("starting main...")
        async with trio.open_nursery() as nursery:
            log.info("spawning loop")
            nursery.start_soon(self.controlLoop, nursery)
    
    def run(self):
        try:
            trio.run(self.main)
        except KeyboardInterrupt as exc:
            log.info("bye bye")
        finally:
            self.cleanup()

if __name__ == "__main__":

    # signal.signal(signal.SIGINT, handle_sigint)

    controller = Controller()
    controller.run()
