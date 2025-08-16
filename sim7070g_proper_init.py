#!/usr/bin/env python3
"""
SIM7070G SMS test with proper initialization based on Zero-iee blog
Key findings: auto-bauding, timing critical, multiple AT commands needed
"""

import serial
import time
import os

SERIAL_PORT = "/dev/ttyS0"
PHONE_NUMBER = "00306980531698"

def try_baud_rates():
    """Try different baud rates as SIM7070G has auto-bauding"""
    baud_rates = [115200, 57600, 9600, 38400]  # 115200 is preferred per blog
    
    for baud in baud_rates:
        try:
            print(f"Trying {baud} baud...")
            ser = serial.Serial(SERIAL_PORT, baud, timeout=3)
            time.sleep(2)
            
            # Critical: Send AT multiple times for auto-bauding
            # Based on blog: first AT for baud detection, second for response
            for attempt in range(3):
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                print(f"  AT attempt {attempt + 1}...")
                ser.write(b'AT\r\n')
                time.sleep(0.5)
                
                response = ser.read(100).decode('utf-8', errors='ignore')
                print(f"  Response: {repr(response)}")
                
                if 'OK' in response:
                    print(f"✓ Connected at {baud} baud")
                    return ser, baud
            
            ser.close()
            
        except Exception as e:
            print(f"  Failed: {e}")
    
    return None, None

def proper_initialization(ser):
    """Initialize SIM7070G with proper timing"""
    print("\nProper SIM7070G initialization:")
    
    # Enable echo first (as shown in blog)
    print("  Enabling echo...")
    ser.write(b'ATE1\r\n')
    time.sleep(0.5)
    resp = ser.read(200).decode('utf-8', errors='ignore')
    print(f"  ATE1 response: {repr(resp)}")
    
    # Check SIM and network
    commands = [
        ("AT+CPIN?", 2, "SIM status"),
        ("AT+CREG?", 1, "Network registration"),
        ("AT+CSQ", 1, "Signal quality"),
        ("AT+COPS?", 2, "Operator info")
    ]
    
    for cmd, wait, desc in commands:
        print(f"  {desc}...")
        ser.write(cmd.encode() + b'\r\n')
        time.sleep(wait)
        resp = ser.read(300).decode('utf-8', errors='ignore')
        print(f"  {cmd} response: {repr(resp)}")
        
        # Check for critical failures
        if cmd == "AT+CPIN?" and 'READY' not in resp:
            print("  ⚠ SIM not ready")
        elif cmd == "AT+CREG?" and not any(x in resp for x in ['+CREG: 0,1', '+CREG: 0,5']):
            print("  ⚠ Not registered on network")
    
    return True

def configure_sms_properly(ser):
    """Configure SMS with proper SIM7070G sequence"""
    print("\nConfiguring SMS for SIM7070G:")
    
    # SMS configuration sequence
    commands = [
        ("AT+CSMS=1", 2, "Enable SMS service"),
        ("AT+CMGF=1", 1, "Text mode"),
        ("AT+CSCS=\"GSM\"", 1, "Character set"),
        ("AT+CPMS=\"ME\",\"ME\",\"ME\"", 2, "Phone memory"),
        ("AT+CNMI=0,0,0,0,0", 1, "Disable notifications"),
        ("AT+CSCA?", 1, "Check SMS center")
    ]
    
    for cmd, wait, desc in commands:
        print(f"  {desc}...")
        ser.reset_input_buffer()
        ser.write(cmd.encode() + b'\r\n')
        time.sleep(wait)
        
        resp = ser.read(300).decode('utf-8', errors='ignore')
        print(f"  {cmd}: {repr(resp)}")
        
        # Check for SMS center
        if cmd == "AT+CSCA?" and ('""' in resp or '+CSCA:' not in resp):
            print("  Setting Greek SMS center...")
            ser.write(b'AT+CSCA="+306942000000"\r\n')
            time.sleep(1)
            ser.read(100)

def send_sms_with_timing(ser, phone):
    """Send SMS with proper timing for SIM7070G"""
    print(f"\nSending SMS to {phone} with proper timing:")
    
    # Clear everything first
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(1)
    
    # Send CMGS with careful timing
    print("  Sending CMGS command...")
    ser.write(f'AT+CMGS="{phone}"\r\n'.encode())
    
    # Wait longer for SIM7070G response
    response = ""
    prompt_found = False
    
    for i in range(100):  # 10 seconds
        time.sleep(0.1)
        
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            response += chunk
            
            # Show real-time response
            if chunk:
                print(f"  [{i:2d}] {repr(chunk)}")
            
            if '>' in response:
                prompt_found = True
                print("  ✓ SMS prompt received!")
                break
            elif 'ERROR' in response:
                print(f"  ✗ Error: {response}")
                return False
    
    if not prompt_found:
        print(f"  ✗ No prompt received. Response: {repr(response)}")
        return False
    
    # Send message with timing
    message = f"SIM7070G test - {time.strftime('%H:%M:%S')}"
    print(f"  Sending message: {message}")
    
    ser.write(message.encode())
    time.sleep(0.2)  # Small delay before Ctrl+Z
    ser.write(b'\x1A')
    
    # Wait for confirmation with longer timeout
    print("  Waiting for send confirmation...")
    response = ""
    
    for i in range(200):  # 20 seconds for SIM7070G
        time.sleep(0.1)
        
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            response += chunk
            
            if chunk:
                print(f"  [{i:2d}] {repr(chunk)}")
            
            if '+CMGS:' in response:
                print("\n  🎉 SMS SENT SUCCESSFULLY!")
                return True
            elif 'OK' in response and len(response) > 10:
                print("\n  ✓ SMS sent (OK received)")
                return True
            elif '+CMS ERROR:' in response:
                print(f"\n  ✗ SMS failed: {response}")
                return False
    
    print(f"\n  ? Timeout. Final response: {repr(response)}")
    return False

def main():
    print("="*70)
    print("SIM7070G SMS TEST - PROPER INITIALIZATION")
    print("Based on Zero-iee blog findings")
    print("="*70)
    
    if os.geteuid() != 0:
        print("⚠ Run with sudo: sudo python3 sim7070g_proper_init.py")
        return
    
    # Step 1: Find working baud rate
    print("1. Finding correct baud rate...")
    ser, baud = try_baud_rates()
    
    if not ser:
        print("✗ Could not establish communication")
        return
    
    try:
        print(f"✓ Communication established at {baud} baud")
        
        # Step 2: Proper initialization
        proper_initialization(ser)
        
        # Step 3: SMS configuration
        configure_sms_properly(ser)
        
        # Step 4: Send test SMS
        success = send_sms_with_timing(ser, PHONE_NUMBER)
        
        if success:
            print("\n" + "="*70)
            print("SUCCESS! SIM7070G SMS is working")
            print("="*70)
            print(f"Working configuration:")
            print(f"  Port: {SERIAL_PORT}")
            print(f"  Baud: {baud}")
            print(f"  Phone: {PHONE_NUMBER}")
        else:
            print("\n" + "="*70)
            print("SMS test failed")
            print("="*70)
            print("Check:")
            print("- SIM card has credit")
            print("- Network signal is good")
            print("- Phone number format is correct")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        if ser:
            ser.close()

if __name__ == "__main__":
    main()