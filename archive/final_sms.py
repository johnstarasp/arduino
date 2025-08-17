#!/usr/bin/env python3
"""
Final SMS test for SIM7070G
"""
import serial
import time
import sys
import os

# Check if running as root for GPIO access
if os.geteuid() != 0:
    print("Please run with sudo for GPIO access")
    sys.exit(1)

# Try to import GPIO (optional for power control)
try:
    import RPi.GPIO as GPIO
    PWRKEY = 4
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PWRKEY, GPIO.OUT)
    
    print("Powering module...")
    GPIO.output(PWRKEY, GPIO.LOW)
    time.sleep(1)
    GPIO.output(PWRKEY, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(PWRKEY, GPIO.LOW)
    time.sleep(1)
    print("Power sequence complete")
    time.sleep(5)
except:
    print("GPIO control skipped")

print("Testing SIM7070G...")

# Find working configuration
ser = None
for port in ['/dev/ttyS0', '/dev/serial0', '/dev/ttyAMA0']:
    if not os.path.exists(port):
        continue
        
    for baud in [115200, 57600, 9600]:
        try:
            print(f"Testing {port} @ {baud}...")
            s = serial.Serial(port, baud, timeout=2)
            s.write(b'AT\r\n')
            time.sleep(1)
            
            if s.in_waiting:
                resp = s.read(s.in_waiting)
                if b'OK' in resp or b'AT' in resp:
                    print(f"Found module at {port} @ {baud}!")
                    ser = s
                    break
            s.close()
        except:
            pass
    if ser:
        break

if not ser:
    print("Module not found!")
    sys.exit(1)

# Quick SMS send
print("\nSending SMS...")
ser.write(b'ATE0\r\n')
time.sleep(1)
ser.read(ser.in_waiting)

ser.write(b'AT+CMGF=1\r\n')
time.sleep(1)
ser.read(ser.in_waiting)

ser.write(b'AT+CMGS="+306976518415"\r')
time.sleep(2)

ser.write(b'Test SMS from Pi\x1A')
time.sleep(15)

if ser.in_waiting:
    resp = ser.read(ser.in_waiting)
    if b'OK' in resp or b'CMGS' in resp:
        print("SMS SENT!")
    else:
        print(f"Response: {resp}")
else:
    print("No response")

ser.close()
print("Done")
