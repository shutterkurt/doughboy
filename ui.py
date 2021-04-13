# A utility module to setup use the display
import time
import subprocess
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789

# Initialize 
# Configuration for CS and DC pins:
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# Create the ST7789 display:
disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=None,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Create blank image for drawing.
# Make sure to create image with mode 'RGB' for full color.
height = disp.width  # we swap height/width to rotate it to landscape!
width = disp.height
image = Image.new("RGB", (width, height))
rotation = 90

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
font = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)

# Turn on the backlight
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

# Shell scripts for system monitoring from here:
# https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load

# assume ip addr doesn't change :)
cmd = "hostname -I | cut -d' ' -f1"
IP = "IP: " + subprocess.check_output(cmd, shell=True).decode("utf-8")

local_setpoint = 78
local_current = 0
local_power = 0

def cls():
    # Clear the screen by drawing a black filled box
    draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
    disp.image(image, rotation)

def updateScreen(setpoint=-1, current=-1, power=-1):
    """update local values if given, then update screen"""

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    #update local values if given
    global local_setpoint
    global local_current
    global local_power
    if (setpoint != -1):
        local_setpoint = setpoint
    if (current != -1):
        local_current = current
    if (power != -1):
        local_power = power

    # Update text on the display:
    SETPOINT = "set: " + str(local_setpoint)
    CURRENT = "cur: " + str(local_current)
    POWER = "power: " + str(local_power)

    y = top
    draw.text((x, y), IP, font=font, fill="#FFFFFF")
    y += font.getsize(IP)[1]
    draw.text((x, y), SETPOINT, font=font, fill="#00FF00")
    y += font.getsize(SETPOINT)[1]
    draw.text((x, y), CURRENT, font=font, fill="#00FF00")
    y += font.getsize(CURRENT)[1]
    draw.text((x, y), POWER, font=font, fill="#00FF00")
    y += font.getsize(POWER)[1]

    # Display image.
    disp.image(image, rotation)

if __name__ == "__main__":
    print("simple test of the screen...")
    cls()
    updateScreen()
    time.sleep(5)
    updateScreen(setpoint=55)
    time.sleep(5)
    updateScreen(current=55)
    time.sleep(5)
    updateScreen(power=5)
    time.sleep(5)
    updateScreen(99,99,10)
