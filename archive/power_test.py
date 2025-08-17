#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import serial

# Power control pin
PWRKEY = 4

print("SIM7070G Power Test")
print("-" * 40)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PWRKEY, GPIO.OUT)

print("Powering on module...")

# Power on sequence
GPIO.output(PWRKEY, GPIO.HIGH)
time.sleep(0.5)
GPIO.output(PWRKEY, GPIO.LOW)
time.sleep(2)
GPIO.output(PWRKEY, GPIO.HIGH)

print("Waiting 10 seconds for module to boot...")
time.sleep(10)

print("Testing serial connection...")

# Test serial at different baud rates
for port in ['/dev/ttyS0', '/dev/serial0']:
    for baud in [115200, 57600, 9600]:
        try:
            print(f"\nTrying {port} at {baud} baud...")
            ser = serial.Serial(port, baud, timeout=2)
            time.sleep(1)
            
            # Send AT command
            ser.write(b'AT\r\n')
            time.sleep(1)
            
            # Read response
            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print(f"Response: {response}")
                
                if b'OK' in response or b'AT' in response:
                    print(f"✓ SUCCESS! Module responding at {port} {baud} baud")
                    
                    # Quick SMS test
                    ser.write(b'AT+CMGF=1\r\n')
                    time.sleep(1)
                    ser.read(ser.in_waiting)
                    
                    phone = "+306976518415"
                    ser.write(f'AT+CMGS="{phone}"\r'.encode())
                    time.sleep(2)
                    
                    ser.write(b'Power test SMS\x1A')
                    time.sleep(10)
                    
                    if ser.in_waiting:
                        resp = ser.read(ser.in_waiting)
                        print(f"SMS Response: {resp}")
                    
                    ser.close()
                    GPIO.cleanup()
                    exit(0)
            
            ser.close()
            
        except Exception as e:
            print(f"Error: {e}")

print("\nModule not responding. Try manual power cycle.")
GPIO.cleanup()
