#!/usr/bin/env python3
"""
Working SMS Script for SIM7070G on Raspberry Pi
Combines power control and proper initialization
"""

import serial
import time
import sys
import os

def init_gpio():
    """Initialize GPIO for power control"""
    try:
        import RPi.GPIO as GPIO
        PWRKEY = 4  # BCM pin 4
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PWRKEY, GPIO.OUT)
        
        print("Power cycling module...")
        # Power off first
        GPIO.output(PWRKEY, GPIO.HIGH)
        time.sleep(1)
        
        # Power on sequence
        GPIO.output(PWRKEY, GPIO.LOW)
        time.sleep(1)
        GPIO.output(PWRKEY, GPIO.HIGH)
        time.sleep(1)
        
        print("Waiting for module to boot (10 seconds)...")
        time.sleep(10)
        return True
    except Exception as e:
        print(f"GPIO init failed: {e}")
        return False

def find_module():
    """Find and connect to SIM7070G module"""
    ports = ['/dev/ttyS0', '/dev/serial0', '/dev/ttyAMA0']
    bauds = [115200, 57600, 9600]
    
    for port in ports:
        if not os.path.exists(port):
            continue
            
        for baud in bauds:
            try:
                print(f"Trying {port} at {baud} baud...")
                ser = serial.Serial(port, baud, timeout=3)
                time.sleep(1)
                
                # Clear buffer and test
                ser.reset_input_buffer()
                ser.write(b'AT\r\n')
                time.sleep(1)
                
                response = ser.read(ser.in_waiting or 100)
                if b'OK' in response or b'AT' in response:
                    print(f"✓ Module found at {port} @ {baud} baud!")
                    return ser
                    
                ser.close()
            except Exception as e:
                print(f"  Error: {e}")
                
    return None

def send_at(ser, cmd, wait=2):
    """Send AT command and get response"""
    ser.reset_input_buffer()
    ser.write((cmd + '\r\n').encode())
    time.sleep(wait)
    
    response = b''
    if ser.in_waiting:
        response = ser.read(ser.in_waiting)
    return response.decode('utf-8', errors='ignore')

def main():
    print("SIM7070G SMS Sender")
    print("=" * 40)
    
    # Step 1: Power control (if available)
    if os.geteuid() == 0:
        init_gpio()
    else:
        print("Not running as root - skipping GPIO power control")
        print("Module should already be powered on")
    
    # Step 2: Find module
    ser = find_module()
    if not ser:
        print("\n✗ Failed to find module!")
        print("Possible issues:")
        print("1. Module not powered on")
        print("2. Wrong serial port")
        print("3. Module needs manual power button press")
        sys.exit(1)
    
    # Step 3: Initialize module
    print("\n" + "=" * 40)
    print("Initializing module...")
    
    # Disable echo
    send_at(ser, "ATE0", 1)
    
    # Get module info
    resp = send_at(ser, "AT+CGMM", 1)
    print(f"Module: {resp.strip()}")
    
    # Check SIM
    print("\nChecking SIM card...")
    for i in range(5):
        resp = send_at(ser, "AT+CPIN?", 2)
        if "READY" in resp:
            print("✓ SIM card ready")
            break
        print(f"  SIM status: {resp.strip()}")
        time.sleep(2)
    
    # Check signal
    resp = send_at(ser, "AT+CSQ", 1)
    print(f"Signal strength: {resp.strip()}")
    
    # Check network
    print("\nChecking network...")
    for i in range(10):
        resp = send_at(ser, "AT+CREG?", 2)
        if "+CREG: 0,1" in resp or "+CREG: 0,5" in resp:
            print("✓ Network registered")
            break
        print(f"  Network status: {resp.strip()}")
        time.sleep(2)
    
    # Step 4: Send SMS
    print("\n" + "=" * 40)
    print("Sending SMS...")
    
    # Set text mode
    resp = send_at(ser, "AT+CMGF=1", 1)
    if "OK" not in resp:
        print(f"Warning: Text mode response: {resp}")
    
    phone = "+306976518415"
    message = "Success! SMS from Raspberry Pi with SIM7070G"
    
    print(f"Recipient: {phone}")
    print(f"Message: {message}")
    
    # Send SMS command
    ser.reset_input_buffer()
    ser.write(f'AT+CMGS="{phone}"\r'.encode())
    
    # Wait for prompt
    time.sleep(3)
    prompt = ser.read(ser.in_waiting or 100)
    
    if b'>' in prompt or len(prompt) == 0:
        print("Sending message...")
        ser.write(message.encode())
        ser.write(b'\x1A')
        
        # Wait for confirmation
        time.sleep(20)
        response = ser.read(ser.in_waiting or 500).decode('utf-8', errors='ignore')
        
        if "+CMGS" in response or "OK" in response:
            print("\n" + "=" * 40)
            print("✓✓✓ SMS SENT SUCCESSFULLY! ✓✓✓")
            print("=" * 40)
        else:
            print(f"\nSMS response: {response}")
    else:
        print(f"Failed to get SMS prompt: {prompt}")
    
    ser.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
