#!/usr/bin/env python3
import serial
import time
import sys

print("Minimal SMS test starting...")

try:
    print("1. Connecting to serial port...")
    ser = serial.Serial('/dev/serial0', 57600, timeout=2)
    print("   Connected!")
    
    print("2. Testing AT command...")
    ser.write(b'AT\r\n')
    time.sleep(1)
    resp = ser.read(50)
    print(f"   AT response: {resp}")
    
    if b'OK' not in resp:
        print("   Module not responding!")
        sys.exit(1)
    
    print("3. Setting SMS service center...")
    ser.write(b'AT+CSCA="+306942000000"\r\n')
    time.sleep(2)
    resp = ser.read(100)
    print(f"   SMSC response: {resp}")
    
    print("4. Setting text mode...")
    ser.write(b'AT+CMGF=1\r\n')
    time.sleep(1)
    resp = ser.read(50)
    print(f"   Text mode: {resp}")
    
    print("5. Sending SMS...")
    ser.write(b'AT+CMGS="+306980531698"\r')
    time.sleep(2)
    resp = ser.read(50)
    print(f"   CMGS response: {resp}")
    
    if b'>' in resp:
        print("6. Got prompt, sending message...")
        ser.write(b'Test SMS\x1A')
        time.sleep(10)
        resp = ser.read(200)
        print(f"   Final response: {resp}")
        
        if b'CMGS' in resp:
            print("   SUCCESS!")
        elif b'ERROR' in resp:
            print(f"   FAILED: {resp}")
        else:
            print("   Unknown response")
    else:
        print("   No SMS prompt received")
    
    ser.close()
    print("Test complete")

except Exception as e:
    print(f"Error: {e}")
    print("Make sure SIM module is powered and responding")