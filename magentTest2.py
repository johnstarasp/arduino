import RPi.GPIO as GPIO

HALL_SENSOR_PIN = 17
pulse_count = 0


def pulse_detected(channel):
    global pulse_count
    pulse_count += 1
GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(HALL_SENSOR_PIN, GPIO.FALLING, callback=pulse_detected, bouncetime=10)
