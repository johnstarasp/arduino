#!/usr/bin/env python3
"""
Quick SMS Center Fix - Set to +3097100000 and test
"""
import serial
import time

print("=== SMS CENTER FIX ===")
print("Setting SMS center to +3097100000")

try:
    # Connect
    ser = serial.Serial('/dev/serial0', 57600, timeout=3)
    time.sleep(1)
    
    # Test connection
    ser.write(b'AT\r\n')
    time.sleep(1)
    if b'OK' not in ser.read(50):
        print("❌ Module not responding")
        exit(1)
    print("✅ Module connected")
    
    # Check current SMS center
    print("\nCurrent SMS center:")
    ser.write(b'AT+CSCA?\r\n')
    time.sleep(2)
    resp = ser.read(200).decode('utf-8', errors='ignore')
    print(f"   {resp.strip()}")
    
    # Set correct SMS center
    print("\nSetting SMS center to +3097100000...")
    ser.write(b'AT+CSCA="+3097100000"\r\n')
    time.sleep(2)
    resp = ser.read(100).decode('utf-8', errors='ignore')
    print(f"   Result: {resp.strip()}")
    
    if "OK" in resp:
        print("✅ SMS center set successfully")
    else:
        print("❌ Failed to set SMS center")
        exit(1)
    
    # Verify it was set
    print("\nVerifying SMS center:")
    ser.write(b'AT+CSCA?\r\n')
    time.sleep(2)
    resp = ser.read(200).decode('utf-8', errors='ignore')
    print(f"   {resp.strip()}")
    
    if "+3097100000" in resp:
        print("✅ SMS center verified: +3097100000")
    else:
        print("❌ SMS center not properly set")
        exit(1)
    
    # Quick SMS test
    print("\nTesting SMS with correct center...")
    
    # Set text mode
    ser.write(b'AT+CMGF=1\r\n')
    time.sleep(1)
    ser.read(50)
    
    # Enable verbose errors
    ser.write(b'AT+CMEE=2\r\n')
    time.sleep(1)
    ser.read(50)
    
    # Test SMS send
    ser.write(b'AT+CMGS="+306980531698"\r')
    time.sleep(3)
    prompt = ser.read(100)
    print(f"   SMS prompt: {prompt}")
    
    if b'>' in prompt:
        print("✅ Got SMS prompt")
        ser.write(b'SMS center fixed to +3097100000\x1A')
        time.sleep(15)
        result = ser.read(300).decode('utf-8', errors='ignore')
        print(f"   SMS result: {result.strip()}")
        
        if "+CMGS" in result:
            print("🎉 SMS SENT SUCCESSFULLY!")
            print("✅ SMS center fix WORKED!")
        elif "CMS ERROR" in result:
            error = result.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in result else "unknown"
            print(f"❌ Still getting CMS ERROR {error}")
            if error == "500":
                print("   SIM may need activation time or different carrier")
        else:
            print("❓ Unknown SMS response")
    else:
        print("❌ No SMS prompt")
        if b"CMS ERROR" in prompt:
            error = prompt.decode().split("CMS ERROR:")[1].strip() if "CMS ERROR:" in prompt.decode() else "unknown"
            print(f"   Error at prompt: {error}")
    
    ser.close()
    print("\nSMS center fix complete")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("Done")