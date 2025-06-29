import RPi.GPIO as GPIO
import time
import serial

# -----------------------------
# CONFIG
# -----------------------------
HALL_SENSOR_PIN = 17
CIRCUMFERENCE = 0.5  # meters
SMS_PHONE_NUMBER = "+306980531698"  # Replace with your phone number
SERIAL_PORT = "/dev/serial0"  # or "/dev/ttyS0" depending on your setup
BAUD_RATE = 115200
SMS_INTERVAL = 10  # seconds

# -----------------------------
# SETUP
# -----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def init_modem(ser):
    ser.write(b'AT\r')
    time.sleep(0.5)
    ser.write(b'AT+CMGF=1\r')  # Set SMS text mode
    time.sleep(0.5)
    ser.write(b'AT+CFUN=1\r')  # Set SMS text mode
    time.sleep(0.5)

    

def send_sms(ser, number, message):
    ser.write(f'AT+CMGS="{number}"\r'.encode())
    time.sleep(2)
    ser.write(f'{message}\x1A'.encode())  # Ctrl+Z
    print("SMS sent.")
    time.sleep(5)
# -----------------------------
# MAIN LOOP
# -----------------------------
try:
    print("Starting polling-based bike speedometer...")

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    init_modem(ser)

    while True:
        print(f"\nCounting wheel pulses for {SMS_INTERVAL} seconds...")
        pulse_count = 0
        last_state = GPIO.input(HALL_SENSOR_PIN)
        start_time = time.time()

        while (time.time() - start_time) < SMS_INTERVAL:
            current_state = GPIO.input(HALL_SENSOR_PIN)

            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                pulse_count += 1
                print(f"Pulse {pulse_count} detected")
                time.sleep(0.01)  # debounce

            last_state = current_state
            time.sleep(0.001)  # adjust as needed

        # Calculate speed
        distance = pulse_count * CIRCUMFERENCE  # meters
        speed_mps = distance / SMS_INTERVAL
        speed_kph = speed_mps * 3.6

        msg = f"Speed: {speed_kph:.2f} km/h"
        print("Sending SMS:", msg)
        send_sms(ser, SMS_PHONE_NUMBER, msg)

except KeyboardInterrupt:
    print("\nStopping program.")
finally:
    GPIO.cleanup()
    if 'ser' in locals():
        ser.close()
