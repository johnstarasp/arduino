import RPi.GPIO as GPIO
import time

SENSOR_PIN = 17  # GPIO17 (pin 11)

GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN)

try:
    while True:
        if GPIO.input(SENSOR_PIN) == GPIO.LOW:
            print("Magnet detected!")
        else:
            print("No magnet.")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Exiting...")
finally:
    GPIO.cleanup()
