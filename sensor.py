import busio
import board
import adafruit_shtc3

"""Encapsulating the sensor readings here"""

i2c = busio.I2C(board.SCL, board.SDA)
sht = adafruit_shtc3.SHTC3(i2c)

temperature, relative_humidity = sht.measurements

def c2f(temperature):
    # Convert input temperature in C to F
    # 9/5C+32
    f = float(temperature) * 9 / 5 + 32
    # round to hundredths
    f = int(100*f + 50) / 100
    return f

def tempC():
    """get the temperature from the sensor as C"""
    return sht.temperature

def tempF():
    """get the temperature from the sensor as F"""
    return c2f(sht.temperature)

def humidity():
    """get the humidity from the sensor"""
    return sht.relative_humidity

def measurements():
    """get both temp and humidity simultaneously"""
    return sht.measurements