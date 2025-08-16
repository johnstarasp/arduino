#!/usr/bin/env python3
"""
Simple test script to find and test GSM modem on Raspberry Pi
Copy this to your Pi and run: sudo python3 simple_fix.py
"""

import serial
import time

def find_modem():
    """Find the GSM modem port and baud rate"""
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/serial0', '/dev/ttyAMA0', '/dev/ttyS0']
    bauds = [9600, 115200]
    
    print("Searching for GSM modem...")
    print("-" * 40)
    
    for port in ports:
        for baud in bauds:
            try:
                print(f"Testing {port} @ {baud}...", end=" ")
                ser = serial.Serial(port, baud, timeout=2)
                time.sleep(1)
                
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Send AT command
                ser.write(b'AT\r\n')
                time.sleep(0.5)
                response = ser.read(100).decode('utf-8', errors='ignore')
                
                if 'OK' in response:
                    print("FOUND!")
                    print(f"\n✓ Modem at {port} ({baud} baud)")
                    print(f"Response: {response.strip()}")
                    
                    # Test signal
                    ser.write(b'AT+CSQ\r\n')
                    time.sleep(0.5)
                    sig = ser.read(100).decode('utf-8', errors='ignore')
                    print(f"Signal: {sig.strip()}")
                    
                    # Test network
                    ser.write(b'AT+CREG?\r\n')
                    time.sleep(0.5)
                    reg = ser.read(100).decode('utf-8', errors='ignore')
                    print(f"Network: {reg.strip()}")
                    
                    ser.close()
                    return port, baud
                else:
                    print("No response")
                
                ser.close()
            except Exception as e:
                print(f"Error: {str(e)[:30]}")
    
    return None, None

def test_sms(port, baud, phone):
    """Test sending an SMS"""
    print(f"\nTesting SMS to {phone}...")
    
    try:
        ser = serial.Serial(port, baud, timeout=5)
        time.sleep(2)
        
        # Initialize modem
        commands = [
            (b'AT\r\n', "AT Test"),
            (b'ATE0\r\n', "Disable Echo"),
            (b'AT+CMGF=1\r\n', "Text Mode"),
        ]
        
        for cmd, desc in commands:
            ser.write(cmd)
            time.sleep(0.5)
            resp = ser.read(100).decode('utf-8', errors='ignore')
            print(f"{desc}: {'OK' if 'OK' in resp else 'FAILED'}")
        
        # Send SMS
        ser.write(f'AT+CMGS="{phone}"\r\n'.encode())
        time.sleep(1)
        resp = ser.read(100).decode('utf-8', errors='ignore')
        
        if '>' in resp:
            msg = "Test from Raspberry Pi\x1A"
            ser.write(msg.encode())
            time.sleep(5)
            final = ser.read(200).decode('utf-8', errors='ignore')
            
            if 'OK' in final or '+CMGS' in final:
                print("✓ SMS sent successfully!")
                return True
            else:
                print("✗ SMS failed:", final[:50])
        else:
            print("✗ No SMS prompt:", resp[:50])
        
        ser.close()
    except Exception as e:
        print(f"✗ SMS Error: {e}")
    
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("GSM MODEM TESTER FOR RASPBERRY PI")
    print("=" * 50)
    
    # Find modem
    port, baud = find_modem()
    
    if port:
        print(f"\n✓ Update your firstTry.py with:")
        print(f'  SERIAL_PORT = "{port}"')
        print(f'  BAUD_RATE = {baud}')
        
        # Test SMS
        phone = "+306980531698"  # Your configured number
        test_sms(port, baud, phone)
    else:
        print("\n✗ No modem found!")
        print("\nTroubleshooting:")
        print("1. Check modem is plugged into USB")
        print("2. Check modem has power")
        print("3. Run: lsusb")
        print("4. Run: ls -la /dev/tty*")