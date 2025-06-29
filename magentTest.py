import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    print("Pin 17 status:", GPIO.input(17))
finally:
    GPIO.cleanup()
