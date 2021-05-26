import ui
import sensor
import mqtt
import trio
from simple_pid import PID

import logging
import time
import math
import json

_log = logging.getLogger(__name__)

class Controller:

    def configure(self, config):
        self.pwmPeriod = config["pwmPeriod"]
        self.setPoint = config["setPoint"]
        self.topicStatus = config["topicStatus"]
        self.topicPlugCommand = config["topicPlugCommand"]

        # TODO: do something better for level lower bound
        # for now set a lower bound for the level
        # from below: sleepTime = 10 * level * self.pwmPeriod / 100
        # just flip it for what level for 3 seconds lower bound
        self.minLevel = (3 * 100) / (10 * self.pwmPeriod)
        _log.debug(f"min level ({self.minLevel})")
        
        # create the PID controller:
        kP = config["kP"]
        kI = config["kI"]
        kD = config["kD"]
        self.pid.tunings = (kP, kI, kD)
        _log.debug(f"pid tunings ({self.pid.tunings})")
        self.pid.setpoint = self.setPoint
        # FIXME: need to fix the pid library - clips I but not overall in POM mode
        # self.pid.output_limits = (0, 10)
        self.pid.auto_mode = True
        # can't turn this on till we have proper constants! otherwise delta input T ~0
        self.pid.proportional_on_measurement = True

    def turnOn(self):
        _log.debug("turning on...")
        if (self.relayState!="On"):
            self.relayCycles+=1
            self.relayState="On"
        # THINK: avoid an mqtt message by listening to plug state?
        mqtt.publish("On", self.topicPlugCommand)

    def turnOff(self, reason="none"):
        _log.debug(f'turning off ({reason})...')
        if (self.relayState!="Off"):
            self.relayCycles+=1
            self.relayState="Off"
        # THINK: avoid an mqtt message by listening to plug state?
        mqtt.publish("Off", self.topicPlugCommand)

    def __init__(self, config):

        # create the PID loop
        self.pid = PID()

        # keep track of number of relay on-off switches for the session
        # then print out when done
        self.relayCycles = 0
        self.relayState = "Off"
        self.startTime = time.time()

        # configure from config dictionary
        self.configure(config)

        # start with relay known to be off:
        self.turnOff("initial state = OFF")

    def cleanup(self):
        _log.info("cleaning up...")
        self.turnOff("cleanup")
        elapsedHours = (time.time() - self.startTime)/(3600)
        _log.info(f"session relay cycles ({self.relayCycles}) over ({elapsedHours}) hours")
        _log.info(f"cycles per hour ({self.relayCycles/elapsedHours})")
        mqtt.cleanup()

    async def sleepFor(self, rawTime):
        #calculate actual sleep time taking into account processing time up to this call
        # i.e. if rawTime is 10 seconds, but processing took 2 so far, then only sleep for 8
        elapsed = int(trio.current_time() - self.start)
        now = trio.current_time()
        remainder = math.ceil(now) - now
        sleepTime = rawTime - elapsed - 1 + remainder
        _log.debug(f'sleepFor: actual sleep time ({sleepTime})')
        await trio.sleep(sleepTime)


    async def turnOffLater(self, level):
        sleepTime = 10 * level * self.pwmPeriod / 100
        _log.debug(f'turnOffLater: level ({level}) period ({self.pwmPeriod}) sleeptime ({sleepTime})')
        await self.sleepFor(sleepTime)
        self.turnOff("turnOffLater")

    def setPower(self, level, nursery):
        _log.info(f'setting power to ({level})')
        if (level == 0):
            self.turnOff("setPower")
        else:
            self.turnOn()
            if (level != 10):
                nursery.start_soon(self.turnOffLater,level)
    
    def pid2level(self, pidOutput):
        # clamp to range 0-10
        if (pidOutput <= 0):
            level = 0
        elif (pidOutput >= 10):
            level = 10
        else:
            # otherwise create one decimal place, rounding up
            level = int(10*pidOutput + 5) / 10
            # level can't be lower than time it takes for ui to redraw
            # (till i fix that)
            if (level < self.minLevel):
                level = 0
        _log.debug(f"pid2level pidOutput({pidOutput}) level ({level})")
        return level


    async def controlLoop(self, nursery):
        _log.info("starting control loop...")

        prevTemp = None

        ui.cls()
        print('Press Ctrl-C to stop...')
        while True:
            # keep track of how long all of this takes
            self.start = trio.current_time()
            
            #get new current temperature
            newTemp = sensor.tempF()
            if prevTemp==None:
                prevTemp = newTemp
            _log.info(f"curTemp= ({newTemp}) delta ({newTemp-prevTemp}) error ({self.setPoint - newTemp})")
            prevTemp = newTemp

            # call the pid to get new power level & set the output accordingly
            level = self.pid2level(self.pid(newTemp))
            _log.debug(f'pid output level ({level})')
            curP, curI, curD = self.pid.components
            _log.debug(f'pid components ({curP} {curI} {curD})')

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

