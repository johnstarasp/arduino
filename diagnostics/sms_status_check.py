#!/usr/bin/env python3
"""
Quick SMS Status Check - Test if CMS ERROR 500 is fixed
"""
import serial
import time

print("=== SMS STATUS CHECK ===")

try:
    # Connect to module (assume powered)
    ser = serial.Serial('/dev/serial0', 57600, timeout=3)
    time.sleep(1)
    
    # Test AT
    ser.write(b'AT\r\n')
    time.sleep(1)
    resp = ser.read(100)
    if b'OK' not in resp:
        print("❌ Module not responding")
        exit(1)
    print("✅ Module connected")
    
    # Check current SMSC
    print("Checking SMS service center...")
    ser.write(b'AT+CSCA?\r\n')
    time.sleep(2)
    resp = ser.read(200).decode('utf-8', errors='ignore')
    print(f"Current SMSC: {resp.strip()}")
    
    # Set SMSC if needed
    if '+306942000000' not in resp:
        print("Setting COSMOTE SMSC...")
        ser.write(b'AT+CSCA="+306942000000"\r\n')
        time.sleep(2)
        result = ser.read(100)
        print(f"SMSC set result: {result}")
    else:
        print("✅ SMSC already configured")
    
    # Quick SMS test
    print("Testing SMS send...")
    ser.write(b'AT+CMGF=1\r\n')  # Text mode
    time.sleep(1)
    ser.read(100)
    
    ser.write(b'AT+CMGS="+306980531698"\r')
    time.sleep(3)
    resp = ser.read(100)
    
    if b'>' in resp:
        print("✅ Got SMS prompt")
        ser.write(b'Status check SMS\x1A')
        time.sleep(10)
        result = ser.read(200).decode('utf-8', errors='ignore')
        
        if '+CMGS' in result:
            print("🎉 SMS SENT SUCCESSFULLY!")
            print("CMS ERROR 500 is FIXED!")
        elif 'CMS ERROR' in result:
            error = result.split('CMS ERROR:')[1].strip().split()[0] if 'CMS ERROR:' in result else 'unknown'
            print(f"❌ Still getting CMS ERROR {error}")
        else:
            print(f"❓ Unknown result: {result}")
    else:
        print(f"❌ No SMS prompt: {resp}")
    
    ser.close()
    
except Exception as e:
    print(f"❌ Error: {e}")

print("Status check complete")