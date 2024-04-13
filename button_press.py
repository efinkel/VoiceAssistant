import RPi.GPIO as GPIO
import time

# Set up GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_pressed_callback(channel):
    print("Button pressed!")

# Add event detection and callback function
GPIO.add_event_detect(23, GPIO.FALLING, callback=button_pressed_callback, bouncetime=300)

try:
    # Keep the script running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # Clean up GPIO and exit
    GPIO.cleanup()

