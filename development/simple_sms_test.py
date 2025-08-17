#!/usr/bin/env python3
import serial
import time
import os

print("SIM7070G Quick Test")

# Power control
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, 0)
    time.sleep(1)
    GPIO.output(4, 1)
    time.sleep(5)
    print("Power cycle complete")
except:
    print("No GPIO control")

# Test serial
for port in ['/dev/ttyS0', '/dev/serial0']:
    if os.path.exists(port):
        try:
            s = serial.Serial(port, 115200, timeout=2)
            s.write(b'AT\r\n')
            time.sleep(1)
            r = s.read(100)
            print(f"{port}: {r}")
            
            if b'OK' in r:
                print("Module found! Sending SMS...")
                s.write(b'AT+CMGF=1\r\n')
                time.sleep(1)
                s.read(100)
                s.write(b'AT+CMGS="+306976518415"\r')
                time.sleep(2)
                s.write(b'SMS from Pi works!\x1A')
                time.sleep(10)
                result = s.read(200)
                print(f"SMS result: {result}")
                s.close()
                exit(0)
            s.close()
        except Exception as e:
            print(f"Error {port}: {e}")

print("Module not responding")