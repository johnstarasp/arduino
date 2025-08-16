#!/usr/bin/env python3
"""
Simple SMS test for SIM7070G
Just sends one SMS to verify functionality
"""

import serial
import time

# Your working settings
SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600
PHONE_NUMBER = "00306980531698"  # Your number in working format

def send_sms_test():
    print("="*50)
    print("SIM7070G SMS FUNCTIONALITY TEST")
    print("="*50)
    
    try:
        # Connect to modem
        print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
        time.sleep(2)
        
        # Test connection
        print("Testing modem...")
        ser.write(b'AT\r\n')
        time.sleep(0.5)
        resp = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in resp:
            print("✗ Modem not responding")
            return
        print("✓ Modem responding")
        
        # Quick SMS setup
        print("Setting up SMS...")
        commands = [
            b'ATE0\r\n',           # Disable echo
            b'AT+CSMS=1\r\n',      # Enable SMS service
            b'AT+CMGF=1\r\n',      # Text mode
            b'AT+CPMS="ME","ME","ME"\r\n'  # Use phone memory
        ]
        
        for cmd in commands:
            ser.write(cmd)
            time.sleep(0.5)
            ser.read(200)  # Clear response
        
        print("✓ SMS configured")
        
        # Send SMS
        print(f"Sending SMS to {PHONE_NUMBER}...")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send CMGS command
        ser.write(f'AT+CMGS="{PHONE_NUMBER}"\r\n'.encode())
        time.sleep(1)
        
        # Check for prompt
        response = ser.read(100).decode('utf-8', errors='ignore')
        print(f"Response: {repr(response)}")
        
        if '>' in response:
            print("✓ SMS prompt received")
            
            # Send message
            message = f"SIM7070G test - {time.strftime('%H:%M:%S')}"
            print(f"Sending: {message}")
            
            ser.write(message.encode())
            ser.write(b'\x1A')  # Ctrl+Z
            
            # Wait for confirmation
            print("Waiting for send confirmation...")
            time.sleep(5)
            
            response = ser.read(300).decode('utf-8', errors='ignore')
            print(f"Send response: {repr(response)}")
            
            if '+CMGS:' in response or 'OK' in response:
                print("\n🎉 SMS SENT SUCCESSFULLY!")
                print("Check your phone for the message")
            else:
                print(f"\n❌ SMS send failed: {response}")
        else:
            print(f"❌ No SMS prompt: {response}")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    send_sms_test()