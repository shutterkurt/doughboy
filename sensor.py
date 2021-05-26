import busio
import board
import adafruit_shtc3
import adafruit_sht31d
import time

"""Encapsulating the sensor readings here"""

i2c = busio.I2C(board.SCL, board.SDA)
topSensor = adafruit_shtc3.SHTC3(i2c)
botSensor = adafruit_sht31d.SHT31D(i2c)

# number of samples to average during calibration
_CALIBRATION_SAMPLES = 15
# amount of seconds between successive calibration sample
_CALIBRATION_TIME = .5

_TOP_SENSOR_CALIBRATION_VAL = 0
_BOT_SENSOR_CALIBRATION_VAL = 0

def c2f(temperature):
    # Convert input temperature in C to F
    # 9/5C+32
    f = float(temperature) * 9 / 5 + 32
    # round to hundredths
    f = int(100*f + 50) / 100
    return f

def tempC():
    """get the temperature from the sensor as C"""
    return topSensor.temperature

def tempF():
    """get the temperature from the sensor as F"""
    return c2f(topSensor.temperature)

def rawTemps():
    return [c2f(topSensor.temperature), c2f(botSensor.temperature)]

def humidity():
    """get the humidity from the sensor"""
    return topSensor.relative_humidity

def measurements():
    """get both temp and humidity simultaneously"""
    return topSensor.measurements

def _calibrate():
    """calibrate the sensors by reading N samples and average"""
    top_sum = 0
    bot_sum =0
    print("calibrating...")
    for x in range(_CALIBRATION_SAMPLES):
        top_sum += c2f(topSensor.temperature)
        bot_sum += c2f(botSensor.temperature)
        time.sleep(_CALIBRATION_TIME)
    top_val = top_sum / _CALIBRATION_SAMPLES
    bot_val = bot_sum / _CALIBRATION_SAMPLES
    print("top val= " + str(top_val))
    print("bot val= " + str(bot_val))
    print("delta / 2= " + str((top_val-bot_val)/2))

def _streamingStats():
    prev_topAvg = 0
    prev_topStd = 0
    prev_botAvg = 0
    prev_botStd = 0
    prev_deltaAvg = 0
    prev_deltaStd = 0
    numSamples = 1  #start at 2 so not get divide by zero not perfect but simpler
    first = True

    while True:
        numSamples += 1
        curTop = c2f(topSensor.temperature)
        curBot = c2f(topSensor.temperature)
        curDelta = curTop - curBot
        if (first):
            first = False
            prev_topAvg = curTop
            prev_botAvg = curBot
            prev_deltaAvg = curDelta
        cur_topAvg = prev_topAvg + (curTop-prev_topAvg)/numSamples
        cur_botAvg = prev_botAvg + (curBot-prev_botAvg)/numSamples
        cur_deltaAvg = prev_deltaAvg + (curDelta-prev_deltaAvg)/numSamples
        
        #FIXME add the std deviations~!

        print(f"sample ({numSamples})")
        print(f"curTop ({curTop}) curBot ({curBot}) curDelta ({curDelta})")
        print(f"topAvg ({cur_topAvg}) botAvg ({cur_botAvg}) deltaAvg ({cur_deltaAvg})")

        prev_topAvg = cur_topAvg
        prev_botAvg = cur_botAvg
        prev_deltaAvg = cur_deltaAvg

        time.sleep(2)

if __name__ == "__main__":

    _calibrate()
    _streamingStats()