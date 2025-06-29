import RPi.GPIO as GPIO
import time

def pulse_detected(channel):
    print("Pulse detected!")

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    GPIO.add_event_detect(17, GPIO.FALLING, callback=pulse_detected, bouncetime=10)
    print("Waiting for pulses. Ctrl+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
finally:
    GPIO.cleanup()
