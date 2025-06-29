import RPi.GPIO as GPIO
import time
import serial

# -----------------------------
# CONFIGURATION
# -----------------------------
HALL_SENSOR_PIN = 17
CIRCUMFERENCE = 0.5  # meters
SMS_PHONE_NUMBER = "+306980531698"  # Replace with your phone number
SERIAL_PORT = "/dev/serial0"      # Might be /dev/ttyS0 or /dev/ttyAMA0
BAUD_RATE = 115200
SMS_DELAY = 10  # seconds

# -----------------------------
# GLOBALS
# -----------------------------
pulse_count = 0

# -----------------------------
# SETUP
# -----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def pulse_detected(channel):
    global pulse_count
    pulse_count += 1

GPIO.add_event_detect(HALL_SENSOR_PIN, GPIO.FALLING, callback=pulse_detected, bouncetime=10)

def init_modem(serial_conn):
    serial_conn.write(b'AT\r')
    time.sleep(0.5)
    serial_conn.write(b'AT+CMGF=1\r')  # Set SMS text mode
    time.sleep(0.5)

def send_sms(serial_conn, number, message):
    serial_conn.write(f'AT+CMGS="{number}"\r'.encode())
    time.sleep(0.5)
    serial_conn.write(f'{message}\x1A'.encode())  # \x1A = Ctrl+Z to send
    print("SMS sent.")

# -----------------------------
# MAIN
# -----------------------------
try:
    print("Starting speed + SMS program...")

    # Initialize SIM7070G serial
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    init_modem(ser)

    while True:
        pulse_count = 0
        time.sleep(SMS_DELAY)

        # Calculate speed
        revolutions = pulse_count
        distance_m = revolutions * CIRCUMFERENCE
        speed_mps = distance_m / SMS_DELAY
        speed_kph = speed_mps * 3.6

        # Send SMS
        speed_msg = f"Current speed: {speed_kph:.2f} km/h"
        print(speed_msg)
        send_sms(ser, SMS_PHONE_NUMBER, speed_msg)

except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    GPIO.cleanup()
    if 'ser' in locals():
        ser.close()
