#!/usr/bin/env python3
"""
Simple SMS Fix - Test common solutions for CMS ERROR 500
"""
import serial
import time

print("=== SIMPLE SMS FIX TEST ===")

# Connect to module (assume already powered)
ser = serial.Serial('/dev/serial0', 57600, timeout=3)
time.sleep(1)

# Test connection
ser.write(b'AT\r\n')
time.sleep(1)
if b'OK' not in ser.read(100):
    print("Module not responding")
    exit(1)

print("Module connected")

# Enable verbose errors
ser.write(b'AT+CMEE=2\r\n')
time.sleep(1)
ser.read(100)

# Set text mode
ser.write(b'AT+CMGF=1\r\n')
time.sleep(1)
ser.read(100)

# Check SMS service center
print("Checking SMS service center...")
ser.write(b'AT+CSCA?\r\n')
time.sleep(2)
resp = ser.read(200).decode('utf-8', errors='ignore')
print(f"Current SMSC: {resp}")

# Set SMS service center for COSMOTE (most common in Greece)
print("Setting SMS service center...")
ser.write(b'AT+CSCA="+306942000000"\r\n')
time.sleep(2)
resp = ser.read(100).decode('utf-8', errors='ignore')
print(f"SMSC set result: {resp}")

# Set SMS storage to SIM
ser.write(b'AT+CPMS="SM","SM","SM"\r\n')
time.sleep(2)
resp = ser.read(200).decode('utf-8', errors='ignore')
print(f"Storage set: {resp}")

# Test SMS
print("Testing SMS...")
phone = "+306980531698"
message = "SMS fix test"

ser.write(f'AT+CMGS="{phone}"\r'.encode())
time.sleep(3)
resp = ser.read(100)
print(f"CMGS response: {resp}")

if b'>' in resp:
    print("Got prompt, sending message...")
    ser.write(message.encode())
    ser.write(b'\x1A')
    time.sleep(15)
    
    result = ser.read(300).decode('utf-8', errors='ignore')
    print(f"Final result: {result}")
    
    if "+CMGS" in result:
        print("✅ SMS SENT SUCCESSFULLY!")
    elif "CMS ERROR" in result:
        error = result.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in result else "unknown"
        print(f"❌ CMS ERROR {error}")
        if error == "500":
            print("Still getting 500 - try different number format or wait for SIM activation")
    else:
        print("❌ Unknown response")
else:
    print("❌ No SMS prompt received")
    if b"CMS ERROR" in resp:
        error = resp.decode().split("CMS ERROR:")[1].strip() if "CMS ERROR:" in resp.decode() else "unknown"
        print(f"CMS ERROR: {error}")

ser.close()
print("Test complete")