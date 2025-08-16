#!/usr/bin/env python3
"""
Final SMS test fixing all issues found:
1. Phone number format: 00 instead of +
2. Signal strength checking
3. Network registration waiting
4. Proper error handling for CMS 304
"""

import serial
import time
import os

SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600  # We know this works
PHONE_NUMBER = "00306980531698"  # Correct format for SIM7070G

def wait_for_signal(ser, max_attempts=10):
    """Wait for good signal strength"""
    print("Checking signal strength...")
    
    for i in range(max_attempts):
        ser.write(b'AT+CSQ\r\n')
        time.sleep(1)
        resp = ser.read(200).decode('utf-8', errors='ignore')
        
        if '+CSQ:' in resp:
            try:
                # Parse signal strength
                import re
                match = re.search(r'\+CSQ:\s*(\d+),(\d+)', resp)
                if match:
                    rssi = int(match.group(1))
                    if rssi == 99:
                        print(f"  Attempt {i+1}: No signal (99)")
                        time.sleep(3)
                        continue
                    elif rssi < 10:
                        print(f"  Attempt {i+1}: Weak signal ({rssi})")
                    else:
                        print(f"  Attempt {i+1}: Good signal ({rssi})")
                        return True
            except:
                print(f"  Attempt {i+1}: Could not parse signal")
        else:
            print(f"  Attempt {i+1}: No signal response")
        
        time.sleep(3)
    
    print("⚠ Signal still weak, but continuing...")
    return False

def wait_for_network(ser, max_attempts=15):
    """Wait for network registration"""
    print("Waiting for network registration...")
    
    for i in range(max_attempts):
        ser.write(b'AT+CREG?\r\n')
        time.sleep(1)
        resp = ser.read(200).decode('utf-8', errors='ignore')
        
        if '+CREG: 0,1' in resp:
            print(f"  ✓ Registered on home network (attempt {i+1})")
            return True
        elif '+CREG: 0,5' in resp:
            print(f"  ✓ Registered roaming (attempt {i+1})")
            return True
        elif '+CREG: 0,2' in resp:
            print(f"  ... Searching for network (attempt {i+1})")
        else:
            print(f"  Status: {resp.strip()}")
        
        time.sleep(2)
    
    return False

def test_sms_formats(ser):
    """Test different phone number formats to avoid CMS 304"""
    formats_to_try = [
        ("00306980531698", "International 00 format"),
        ("+306980531698", "Plus format"), 
        ("306980531698", "Without country prefix"),
        ("6980531698", "Local format")
    ]
    
    print("Testing phone number formats to avoid CMS ERROR 304:")
    
    for phone_format, description in formats_to_try:
        print(f"\n  Testing {description}: {phone_format}")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.5)
        
        # Send CMGS command
        ser.write(f'AT+CMGS="{phone_format}"\r\n'.encode())
        time.sleep(1)
        
        response = ser.read(200).decode('utf-8', errors='ignore')
        print(f"    Response: {repr(response)}")
        
        if '>' in response:
            print(f"    ✓ SUCCESS with {phone_format}!")
            
            # Cancel this test and use this format for real SMS
            ser.write(b'\x1B')  # ESC to cancel
            time.sleep(0.5)
            ser.read(100)  # Clear any response
            
            return phone_format
        elif 'CMS ERROR: 304' in response:
            print(f"    ✗ CMS 304 error with {phone_format}")
        elif 'ERROR' in response:
            print(f"    ✗ Other error: {response}")
        else:
            print(f"    ? Unclear response")
    
    return None

def send_sms_final(ser, phone_number):
    """Send SMS with the working phone format"""
    print(f"\nSending final SMS to {phone_number}:")
    
    # Clear everything
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(1)
    
    # Send CMGS
    ser.write(f'AT+CMGS="{phone_number}"\r\n'.encode())
    time.sleep(1)
    
    response = ser.read(100).decode('utf-8', errors='ignore')
    
    if '>' not in response:
        print(f"  ✗ No prompt: {response}")
        return False
    
    print("  ✓ SMS prompt received")
    
    # Send message
    message = f"SIM7070G WORKING! {time.strftime('%H:%M:%S')}"
    print(f"  Sending: {message}")
    
    ser.write(message.encode())
    ser.write(b'\x1A')  # Ctrl+Z
    
    # Wait for confirmation
    print("  Waiting for confirmation...")
    
    response = ""
    for i in range(100):
        time.sleep(0.1)
        
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            response += chunk
            
            if '+CMGS:' in response:
                print("  🎉 SMS SENT SUCCESSFULLY!")
                return True
            elif 'OK' in response and i > 30:
                print("  ✓ SMS sent (OK)")
                return True
            elif 'ERROR' in response:
                print(f"  ✗ Send failed: {response}")
                return False
    
    print(f"  ? Timeout: {response}")
    return False

def main():
    print("="*60)
    print("FINAL SIM7070G SMS TEST")
    print("Fixing CMS ERROR 304 and signal issues")
    print("="*60)
    
    if os.geteuid() != 0:
        print("Run with: sudo python3 final_sms_test.py")
        return
    
    try:
        # Connect
        print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
        time.sleep(2)
        
        # Test connection
        ser.write(b'AT\r\n')
        time.sleep(0.5)
        if 'OK' not in ser.read(100).decode('utf-8', errors='ignore'):
            print("✗ No modem response")
            return
        print("✓ Modem responding")
        
        # Check SIM
        ser.write(b'AT+CPIN?\r\n')
        time.sleep(1)
        resp = ser.read(200).decode('utf-8', errors='ignore')
        if 'READY' not in resp:
            print(f"✗ SIM not ready: {resp}")
            return
        print("✓ SIM ready")
        
        # Wait for signal and network
        wait_for_signal(ser)
        
        if not wait_for_network(ser):
            print("✗ Network registration failed")
            return
        print("✓ Network registered")
        
        # Configure SMS
        print("\nConfiguring SMS...")
        commands = [
            b'ATE0\r\n',
            b'AT+CSMS=1\r\n',
            b'AT+CMGF=1\r\n',
            b'AT+CPMS="ME","ME","ME"\r\n'
        ]
        
        for cmd in commands:
            ser.write(cmd)
            time.sleep(0.5)
            ser.read(200)
        
        print("✓ SMS configured")
        
        # Test formats to avoid CMS 304
        working_format = test_sms_formats(ser)
        
        if working_format:
            print(f"\n✓ Found working format: {working_format}")
            success = send_sms_final(ser, working_format)
            
            if success:
                print("\n" + "="*60)
                print("🎉 SMS TEST SUCCESSFUL!")
                print("="*60)
                print("Your SIM7070G is working perfectly!")
                print(f"Working phone format: {working_format}")
            else:
                print("\n✗ SMS send failed")
        else:
            print("\n✗ No working phone format found")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()