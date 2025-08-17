#!/usr/bin/env python3
import serial
import time
import os

print("Extended SIM7070G Test")
print("=" * 30)

# Extended power control sequence
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(4, GPIO.OUT)
    
    print("Extended power sequence...")
    # Ensure module is off first
    GPIO.output(4, GPIO.LOW)
    time.sleep(3)
    
    # Power on pulse (2+ seconds)
    GPIO.output(4, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(4, GPIO.LOW)
    
    print("Waiting 15 seconds for boot...")
    time.sleep(15)
    
    print("Power control complete")
except Exception as e:
    print(f"GPIO error: {e}")

# Test multiple configurations with longer waits
configs = [
    ('/dev/ttyS0', 115200),
    ('/dev/ttyS0', 57600),
    ('/dev/ttyS0', 9600),
    ('/dev/serial0', 115200),
    ('/dev/serial0', 57600),
]

for port, baud in configs:
    if not os.path.exists(port):
        print(f"Port {port} doesn't exist")
        continue
        
    print(f"\nTesting {port} @ {baud}...")
    try:
        ser = serial.Serial(port, baud, timeout=3)
        time.sleep(2)
        
        # Try multiple AT commands
        for attempt in range(3):
            print(f"  AT attempt {attempt + 1}...")
            ser.reset_input_buffer()
            ser.write(b'AT\r\n')
            time.sleep(2)
            
            response = ser.read(ser.in_waiting or 100)
            print(f"  Response: {response}")
            
            if b'OK' in response or b'AT' in response:
                print(f"SUCCESS! Module responding at {port} @ {baud}")
                
                # Try SMS
                print("Setting text mode...")
                ser.write(b'AT+CMGF=1\r\n')
                time.sleep(2)
                resp = ser.read(ser.in_waiting or 100)
                print(f"Text mode: {resp}")
                
                print("Checking SIM...")
                ser.write(b'AT+CPIN?\r\n')
                time.sleep(2)
                resp = ser.read(ser.in_waiting or 100)
                print(f"SIM: {resp}")
                
                print("Sending SMS...")
                ser.write(b'AT+CMGS="+306976518415"\r')
                time.sleep(3)
                resp = ser.read(ser.in_waiting or 100)
                print(f"CMGS response: {resp}")
                
                # Send message regardless of prompt
                ser.write(b'SMS SUCCESS from Raspberry Pi!\x1A')
                print("Waiting for SMS confirmation...")
                time.sleep(20)
                
                final = ser.read(ser.in_waiting or 200)
                print(f"Final: {final}")
                
                if b'CMGS' in final or b'OK' in final:
                    print("\n*** SMS SENT SUCCESSFULLY! ***")
                else:
                    print("\nSMS may have failed")
                
                ser.close()
                exit(0)
                
        ser.close()
        
    except Exception as e:
        print(f"  Error: {e}")

print("\nModule not responding on any port/baud combination")
print("Check:")
print("1. Physical connections")
print("2. Power supply")
print("3. SIM card insertion")
print("4. Antenna connection")