#!/usr/bin/env python3
"""
Working SMS Script with CMS ERROR 500 Fix
Includes SMSC configuration for new SIM cards
"""
import serial
import time
from datetime import datetime

def send_sms_with_fix(phone, message):
    """Send SMS with CMS ERROR 500 fix applied"""
    print(f"=== SMS with Fix: {phone} ===")
    print(f"Message: {message}")
    
    try:
        # Connect to module
        ser = serial.Serial('/dev/serial0', 57600, timeout=5)
        time.sleep(2)
        
        # Test connection
        ser.write(b'AT\r\n')
        time.sleep(1)
        if b'OK' not in ser.read(100):
            print("❌ Module not responding")
            return False
        print("✅ Module connected")
        
        # CRITICAL FIX: Set SMS Service Center for COSMOTE
        print("Setting SMS service center...")
        ser.write(b'AT+CSCA="+306942000000"\r\n')
        time.sleep(2)
        resp = ser.read(100)
        if b'OK' in resp:
            print("✅ SMS service center configured")
        else:
            print(f"⚠️  SMSC warning: {resp}")
        
        # Enable verbose errors
        ser.write(b'AT+CMEE=2\r\n')
        time.sleep(1)
        ser.read(100)
        
        # Set text mode
        ser.write(b'AT+CMGF=1\r\n')
        time.sleep(1)
        resp = ser.read(100)
        if b'OK' not in resp:
            print(f"❌ Text mode failed: {resp}")
            return False
        print("✅ Text mode set")
        
        # Set SMS storage to SIM
        ser.write(b'AT+CPMS="SM","SM","SM"\r\n')
        time.sleep(2)
        ser.read(200)  # Read response
        
        # Send SMS
        print("Sending SMS...")
        ser.reset_input_buffer()
        ser.write(f'AT+CMGS="{phone}"\r'.encode())
        
        # Wait for prompt
        time.sleep(3)
        prompt = ser.read(100)
        print(f"Prompt response: {prompt}")
        
        if b'>' in prompt:
            print("✅ Got SMS prompt")
            
            # Send message
            ser.write(message.encode())
            time.sleep(1)
            ser.write(b'\x1A')  # Ctrl+Z
            
            # Wait for confirmation
            print("Waiting for SMS confirmation...")
            time.sleep(15)
            result = ser.read(300).decode('utf-8', errors='ignore')
            print(f"SMS result: {result}")
            
            if "+CMGS" in result:
                print("🎉 SMS SENT SUCCESSFULLY!")
                ser.close()
                return True
            elif "CMS ERROR" in result:
                error = result.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in result else "unknown"
                print(f"❌ CMS ERROR {error}")
                if error == "500":
                    print("   Still getting 500 - SIM may need more time to activate")
                ser.close()
                return False
            else:
                print("❌ Unknown SMS response")
                ser.close()
                return False
        else:
            print("❌ No SMS prompt received")
            if b"CMS ERROR" in prompt:
                error = prompt.decode().split("CMS ERROR:")[1].strip() if "CMS ERROR:" in prompt.decode() else "unknown"
                print(f"❌ CMS ERROR at prompt: {error}")
            ser.close()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test the fixed SMS functionality"""
    print("=== SMS FIX TEST ===")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    
    phone = "+306980531698"
    message = f"SMS fix test successful at {datetime.now().strftime('%H:%M:%S')}"
    
    success = send_sms_with_fix(phone, message)
    
    if success:
        print("\n🎉 SMS FIX SUCCESSFUL!")
        print("You can now use this method in your speedometer scripts")
    else:
        print("\n❌ SMS still failing")
        print("Try waiting 24-48 hours for SIM activation")
        print("Or contact carrier to enable SMS service")

if __name__ == "__main__":
    main()