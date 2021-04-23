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
        log.debug("=======================================================")
        log.debug("read ini file: " + str(config))
        self.pwmPeriod = config["CONTROL"].getfloat("pwmPeriod")
        self.setPoint = config["CONTROL"].getfloat("setPoint")
        self.topicStatus = config["CONTROL"].get("topicStatus")
        self.topicPlugCommand = config["CONTROL"].get("topicPlugCommand")

        # use these for test
        self.setPointHi = config["CONTROL"].getfloat("setPointHi")
        self.setPointLo = config["CONTROL"].getfloat("setPointLo")
        self.setPointPeriodMinutes = config["CONTROL"].getfloat("setPointPeriodMinutes")

        # TODO: do something better for level lower bound
        # for now set a lower bound for the level
        # from below: sleepTime = 10 * level * self.pwmPeriod / 100
        # just flip it for what level for 3 seconds lower bound
        self.minLevel = (3 * 100) / (10 * self.pwmPeriod)
        log.debug(f"min level ({self.minLevel})")
        
        # keep track of number of relay on-off switches for the session
        # then print out when done
        self.relayCycles = 0
        self.relayState = "Off"
        self.startTime = time.time()

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
        if (self.relayState!="On"):
            self.relayCycles+=1
            self.relayState="On"
        # THINK: avoid an mqtt message by listening to plug state?
        mqtt.publish("On", self.topicPlugCommand)

    def turnOff(self, reason="none"):
        log.debug(f'turning off ({reason})...')
        if (self.relayState!="Off"):
            self.relayCycles+=1
            self.relayState="Off"
        # THINK: avoid an mqtt message by listening to plug state?
        mqtt.publish("Off", self.topicPlugCommand)

    def cleanup(self):
        log.info("cleaning up...")
        self.turnOff("cleanup")
        elapsedHours = (time.time() - self.startTime)/(3600)
        log.info(f"session relay cycles ({self.relayCycles}) over ({elapsedHours}) hours")
        log.info(f"cycles per hour ({self.relayCycles/elapsedHours})")
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
        log.info(f'setting power to ({level})')
        if (level == 0):
            self.turnOff("setPower")
        else:
            self.turnOn()
            if (level != 10):
                nursery.start_soon(self.turnOffLater,level)
    
    def pid2level(self, pidOutput):
        # pid outputs a float clamped to 0-10
        if (pidOutput==0):
            return 0
        elif (pidOutput==10):
            return 10
        else:
            # otherwise create one decimal place, rounding up
            level = int(10*pidOutput + 5) / 10
            # level can't be lower than time it takes for ui to redraw
            # (till i fix that)
            # so lets say it can't be lower than 3 seconds
            if (level < self.minLevel):
                level = 0
            
            return level

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
            level = self.pid2level(self.pid(newTemp))
            log.debug(f'pid output level ({level})')
            curP, curI, curD = self.pid.components
            log.debug(f'pid components ({curP} {curI} {curD})')

            # level = 0
            self.setPower(level, nursery)

            # update the screen
            # FIXME: look into why updateScreen takes ~2 seconds!!
            # FIXME: convert it into a trio loop based on pwmPeriod
            # convert into a class, and just update its members here
            # have the trio loop to actually update the screen
            # need checkpoints along the way! or some such until understand why takes so long
            ui.updateScreen(self.setPoint, newTemp, level)

            # publish the payload
            payload = {
                "curTemp": newTemp,
                "setPoint": self.setPoint,
                "level": level*10,   # to give percent power, not tenths power
                "curP": curP,
                "curI": curI,
                "curD": curD
                }
            # log.debug(f"mqtt payload ({json.dumps(payload)})")
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
