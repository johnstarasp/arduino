#!/usr/bin/env python3
"""
Verify SMS Fix Results
"""
import serial
import time

print("=== VERIFYING SMS FIX RESULTS ===")

try:
    ser = serial.Serial('/dev/serial0', 57600, timeout=3)
    time.sleep(1)
    
    # Check if module responds
    ser.write(b'AT\r\n')
    time.sleep(1)
    if b'OK' not in ser.read(50):
        print("❌ Module not responding")
        exit(1)
    
    print("✅ Module connected")
    
    # Check SMS center
    ser.write(b'AT+CSCA?\r\n')
    time.sleep(2)
    resp = ser.read(200).decode('utf-8', errors='ignore')
    print(f"Current SMS center: {resp.strip()}")
    
    if '+3097100000' in resp:
        print("✅ SMS center correctly set to +3097100000")
        
        # Test SMS
        print("Testing SMS...")
        ser.write(b'AT+CMGF=1\r\n')
        time.sleep(1)
        ser.read(50)
        
        ser.write(b'AT+CMGS="+306980531698"\r')
        time.sleep(3)
        prompt = ser.read(100)
        
        if b'>' in prompt:
            print("✅ SMS prompt received")
            ser.write(b'SMS fix verification test\x1A')
            time.sleep(15)
            result = ser.read(300).decode('utf-8', errors='ignore')
            
            if '+CMGS' in result:
                print("🎉 SMS SENT SUCCESSFULLY!")
                print("✅ CMS ERROR 500 FIXED!")
            elif 'CMS ERROR' in result:
                error = result.split('CMS ERROR:')[1].strip().split()[0] if 'CMS ERROR:' in result else 'unknown'
                print(f"❌ Still getting CMS ERROR {error}")
            else:
                print(f"❓ Unknown result: {result}")
        else:
            print("❌ No SMS prompt received")
    else:
        print("❌ SMS center not set to +3097100000")
        print("Setting it now...")
        ser.write(b'AT+CSCA="+3097100000"\r\n')
        time.sleep(2)
        result = ser.read(100)
        print(f"Set result: {result}")
    
    ser.close()
    
except Exception as e:
    print(f"Error: {e}")

print("Verification complete")