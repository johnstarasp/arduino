#!/usr/bin/env python3
"""
Fix SIM card and network issues for SIMCOM SIM7070 modem
"""

import serial
import time
import sys

# Your modem settings (as detected)
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 57600
PHONE_NUMBER = "+306980531698"

def send_at_command(ser, command, wait=1):
    """Send AT command and return response"""
    ser.write(command.encode() + b'\r\n')
    time.sleep(wait)
    response = ser.read(500).decode('utf-8', errors='ignore')
    return response

def main():
    print("="*60)
    print("SIMCOM SIM7070 SIM CARD & NETWORK FIX")
    print("="*60)
    
    try:
        # Connect to modem
        print(f"\nConnecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
        time.sleep(2)
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test connection
        print("\n1. Testing connection...")
        resp = send_at_command(ser, "AT")
        if 'OK' in resp:
            print("✓ Modem responding")
        else:
            print("✗ Modem not responding")
            return
        
        # Check SIM card status
        print("\n2. Checking SIM card...")
        resp = send_at_command(ser, "AT+CPIN?")
        print(f"   SIM Status: {resp.strip()}")
        
        if 'READY' in resp:
            print("   ✓ SIM card ready")
        elif 'SIM PIN' in resp:
            print("   ✗ SIM requires PIN")
            pin = input("   Enter SIM PIN: ")
            resp = send_at_command(ser, f'AT+CPIN="{pin}"', 3)
            print(f"   PIN result: {resp.strip()}")
        elif 'SIM PUK' in resp:
            print("   ✗ SIM requires PUK (locked)")
            return
        elif 'NOT INSERTED' in resp:
            print("   ✗ SIM not inserted properly")
            print("   Check SIM card insertion and restart")
            return
        else:
            print("   ⚠ Unknown SIM status")
        
        # Power cycle the modem module
        print("\n3. Power cycling modem...")
        resp = send_at_command(ser, "AT+CFUN=0", 3)  # Minimum functionality
        print(f"   Power down: {'OK' if 'OK' in resp else 'Failed'}")
        
        time.sleep(2)
        
        resp = send_at_command(ser, "AT+CFUN=1", 5)  # Full functionality
        print(f"   Power up: {'OK' if 'OK' in resp else 'Failed'}")
        
        # Wait for initialization
        print("\n4. Waiting for network initialization...")
        for i in range(10):
            time.sleep(2)
            print(f"   Checking... ({i+1}/10)")
            
            # Check registration
            resp = send_at_command(ser, "AT+CREG?")
            if '+CREG: 0,1' in resp or '+CREG: 0,5' in resp:
                print("   ✓ Network registered!")
                break
            elif '+CREG: 0,2' in resp:
                print("   ... Searching for network")
        
        # Check network registration status
        print("\n5. Network Status:")
        
        # Network registration
        resp = send_at_command(ser, "AT+CREG?")
        print(f"   Registration: {resp.strip()}")
        
        # Signal quality
        resp = send_at_command(ser, "AT+CSQ")
        print(f"   Signal: {resp.strip()}")
        
        # Operator
        resp = send_at_command(ser, "AT+COPS?")
        print(f"   Operator: {resp.strip()}")
        
        # Network mode (for SIM7070)
        resp = send_at_command(ser, "AT+CNSMOD?")
        print(f"   Network Mode: {resp.strip()}")
        
        # Check if registered
        resp = send_at_command(ser, "AT+CREG?")
        if '+CREG: 0,1' in resp or '+CREG: 0,5' in resp:
            print("\n✓ NETWORK READY FOR SMS!")
            
            # Configure SMS
            print("\n6. Configuring SMS...")
            commands = [
                ("ATE0", "Disable echo"),
                ("AT+CMGF=1", "Text mode"),
                ("AT+CSCS=\"GSM\"", "Character set"),
                ("AT+CNMI=2,1,0,0,0", "SMS notifications")
            ]
            
            for cmd, desc in commands:
                resp = send_at_command(ser, cmd)
                print(f"   {desc}: {'OK' if 'OK' in resp else 'Failed'}")
            
            # Send test SMS
            print(f"\n7. Sending test SMS to {PHONE_NUMBER}...")
            
            # Start SMS
            ser.write(f'AT+CMGS="{PHONE_NUMBER}"\r\n'.encode())
            time.sleep(1)
            resp = ser.read(100).decode('utf-8', errors='ignore')
            
            if '>' in resp:
                # Send message
                msg = f"Test from SIM7070 at {time.strftime('%H:%M')}"
                ser.write(msg.encode())
                ser.write(b'\x1A')  # Ctrl+Z
                
                time.sleep(5)
                resp = ser.read(500).decode('utf-8', errors='ignore')
                
                if 'OK' in resp or '+CMGS' in resp:
                    print("   ✓ SMS SENT SUCCESSFULLY!")
                else:
                    print(f"   ✗ SMS failed: {resp.strip()}")
            else:
                print(f"   ✗ No SMS prompt: {resp.strip()}")
                
        else:
            print("\n✗ Network not ready")
            print("\nTroubleshooting:")
            print("1. Check antenna connection")
            print("2. Move to area with better signal")
            print("3. Check if SIM card has active service")
            print("4. Try manual network selection:")
            print("   AT+COPS=?  (list available networks)")
            print("   AT+COPS=0  (automatic selection)")
        
        # Save configuration
        print("\n8. Configuration for firstTry.py:")
        print(f'   SERIAL_PORT = "{SERIAL_PORT}"')
        print(f'   BAUD_RATE = {BAUD_RATE}')
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()