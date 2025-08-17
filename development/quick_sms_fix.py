#!/usr/bin/env python3
"""
Quick SMS Fix for CMS ERROR 500
Focuses on common fixes for new SIM cards
"""
import serial
import time

def send_at(ser, cmd, wait=2):
    """Send AT command and return response"""
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting or 300).decode('utf-8', errors='ignore')
    print(f"{cmd}: {response.strip()}")
    return response

def quick_sms_fix():
    print("=== QUICK SMS FIX FOR CMS ERROR 500 ===")
    
    # Connect without power cycling (assume module is already on)
    try:
        ser = serial.Serial('/dev/serial0', 57600, timeout=5)
        time.sleep(2)
        
        # Test connection
        if "OK" not in send_at(ser, "AT", 1):
            print("Module not responding")
            return
        
        print("\n1. Basic SMS Configuration Fix")
        
        # Enable verbose errors
        send_at(ser, "AT+CMEE=2")
        
        # Set text mode
        send_at(ser, "AT+CMGF=1")
        
        # Check and fix SMS service center
        print("\n2. SMS Service Center Check")
        resp = send_at(ser, "AT+CSCA?")
        if '""' in resp or "CSCA:" not in resp:
            print("⚠️  SMS Service Center not set - trying to auto-configure")
            # Common Greek SMS centers
            sms_centers = [
                '+306942000000',  # COSMOTE
                '+306977000000',  # WIND
                '+306945000000',  # VODAFONE
            ]
            
            for center in sms_centers:
                print(f"Trying SMS center: {center}")
                resp = send_at(ser, f'AT+CSCA="{center}"', 2)
                if "OK" in resp:
                    print(f"✓ SMS center set to {center}")
                    break
        
        # Set SMS storage
        print("\n3. SMS Storage Configuration")
        send_at(ser, 'AT+CPMS="SM","SM","SM"')  # Use SIM storage
        
        # Check network registration
        print("\n4. Network Check")
        send_at(ser, "AT+CREG?")
        send_at(ser, "AT+COPS?")
        
        # Test SMS with multiple methods
        print("\n5. Testing SMS Methods")
        phone = "+306980531698"
        message = "Quick fix test SMS"
        
        methods = [
            ("Method 1: Standard", f'AT+CMGS="{phone}"'),
            ("Method 2: No quotes", f'AT+CMGS={phone}'),
            ("Method 3: National", f'AT+CMGS="6980531698"'),
        ]
        
        for method_name, cmd in methods:
            print(f"\n--- {method_name} ---")
            
            # Ensure text mode
            send_at(ser, "AT+CMGF=1", 1)
            
            # Send SMS command
            ser.reset_input_buffer()
            ser.write(f"{cmd}\r".encode())
            time.sleep(3)
            
            response = ser.read(ser.in_waiting or 200)
            print(f"Response: {response}")
            
            if b'>' in response:
                print("✓ Got SMS prompt - sending message")
                ser.write(message.encode())
                time.sleep(1)
                ser.write(b'\x1A')
                
                # Wait for result
                time.sleep(10)
                result = ser.read(ser.in_waiting or 300).decode('utf-8', errors='ignore')
                print(f"Result: {result}")
                
                if "+CMGS" in result:
                    print(f"🎉 SUCCESS! {method_name} worked!")
                    print("Use this method in your scripts")
                    ser.close()
                    return True
                elif "CMS ERROR" in result:
                    error = result.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in result else "unknown"
                    print(f"❌ CMS ERROR {error}")
                    if error == "500":
                        print("   Still getting 500 error - trying next method")
                else:
                    print("❌ Unknown response")
            else:
                print("❌ No SMS prompt")
                if b"CMS ERROR" in response:
                    error = response.decode().split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in response else "unknown"
                    print(f"❌ CMS ERROR {error}")
        
        print("\n❌ All methods failed")
        print("\nFinal troubleshooting:")
        print("1. Check if SIM card is activated for SMS")
        print("2. Try with a different phone number")
        print("3. Wait 24-48 hours for new SIM to fully activate")
        print("4. Contact carrier to enable SMS service")
        
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    quick_sms_fix()