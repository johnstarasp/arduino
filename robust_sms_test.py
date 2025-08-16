#!/usr/bin/env python3
"""
Robust SMS test with detailed debugging
"""

import serial
import time
import os

SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600
PHONE_NUMBER = "00306980531698"

def send_command_with_wait(ser, cmd, wait_time=1, description=""):
    """Send command and wait for response"""
    print(f"  → {cmd.strip()} ({description})")
    
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(cmd.encode() + b'\r\n')
    time.sleep(wait_time)
    
    response = ser.read(500).decode('utf-8', errors='ignore')
    print(f"  ← {repr(response)}")
    return response

def main():
    print("="*60)
    print("ROBUST SIM7070G SMS TEST")
    print("="*60)
    
    # Check if running as root
    if os.geteuid() != 0:
        print("⚠ Warning: Not running as root")
        print("  Try: sudo python3 test_sms_send.py")
    
    try:
        print(f"\n1. Connecting to {SERIAL_PORT}...")
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=10,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )
        time.sleep(3)
        print("✓ Serial connection established")
        
        # Test basic communication
        print("\n2. Testing basic communication:")
        resp = send_command_with_wait(ser, "AT", 1, "Basic test")
        if 'OK' not in resp:
            print("✗ Modem not responding properly")
            return
        
        # Check modem status
        print("\n3. Checking modem status:")
        send_command_with_wait(ser, "ATI", 1, "Modem info")
        send_command_with_wait(ser, "AT+CPIN?", 2, "SIM status")
        send_command_with_wait(ser, "AT+CREG?", 1, "Network status")
        send_command_with_wait(ser, "AT+CSQ", 1, "Signal quality")
        
        # Complete SMS initialization
        print("\n4. Complete SMS setup:")
        commands = [
            ("ATE0", 1, "Disable echo"),
            ("AT+CFUN=1", 3, "Full functionality"),
            ("AT+CSMS=1", 2, "Enable SMS service"),
            ("AT+CMGF=1", 1, "Text mode"),
            ("AT+CSCS=\"GSM\"", 1, "Character set"),
            ("AT+CPMS=\"ME\",\"ME\",\"ME\"", 2, "Phone memory"),
            ("AT+CNMI=0,0,0,0,0", 1, "Disable notifications")
        ]
        
        for cmd, wait, desc in commands:
            resp = send_command_with_wait(ser, cmd, wait, desc)
            if 'OK' not in resp and 'ERROR' not in resp:
                print(f"    ⚠ Unclear response for {desc}")
        
        # Check SMS center
        print("\n5. SMS Center:")
        resp = send_command_with_wait(ser, "AT+CSCA?", 1, "Check SMS center")
        
        # Try sending SMS with extended monitoring
        print(f"\n6. Sending SMS to {PHONE_NUMBER}:")
        print("   Clearing buffers...")
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(1)
        
        print(f"   Sending CMGS command...")
        ser.write(f'AT+CMGS="{PHONE_NUMBER}"\r\n'.encode())
        
        # Monitor response character by character
        response = ""
        prompt_found = False
        
        print("   Monitoring response:")
        for i in range(100):  # 10 seconds
            time.sleep(0.1)
            
            while ser.in_waiting > 0:
                char = ser.read(1).decode('utf-8', errors='ignore')
                response += char
                print(f"   [{i:2d}] Received: {repr(char)} (total: {repr(response)})")
                
                if '>' in response:
                    prompt_found = True
                    print("   ✓ SMS PROMPT DETECTED!")
                    break
                elif 'ERROR' in response:
                    print(f"   ✗ ERROR DETECTED: {response}")
                    break
            
            if prompt_found or 'ERROR' in response:
                break
        
        if prompt_found:
            # Send message
            message = f"Test from Pi at {time.strftime('%H:%M:%S')}"
            print(f"   Sending message: {message}")
            
            ser.write(message.encode())
            ser.write(b'\x1A')  # Ctrl+Z
            
            # Monitor send response
            print("   Waiting for send confirmation:")
            send_response = ""
            
            for i in range(150):  # 15 seconds
                time.sleep(0.1)
                
                while ser.in_waiting > 0:
                    char = ser.read(1).decode('utf-8', errors='ignore')
                    send_response += char
                    print(f"   [{i:2d}] Send: {repr(char)} (total: {repr(send_response)})")
                    
                    if '+CMGS:' in send_response:
                        print("\n   🎉 SMS SENT SUCCESSFULLY!")
                        break
                    elif 'OK' in send_response and i > 50:
                        print("\n   ✓ SMS probably sent (OK received)")
                        break
                    elif '+CMS ERROR:' in send_response:
                        print(f"\n   ✗ SMS FAILED: {send_response}")
                        break
                
                if any(x in send_response for x in ['+CMGS:', 'OK', '+CMS ERROR:']):
                    break
        
        else:
            print(f"\n   ✗ No SMS prompt received")
            print(f"   Full response: {repr(response)}")
            
            # Try troubleshooting
            print("\n7. Troubleshooting:")
            
            # Check if we can send a simple AT command
            resp = send_command_with_wait(ser, "AT", 1, "Verify connection")
            
            # Try alternative phone number formats
            alt_formats = [
                "+306980531698",      # With +
                "306980531698",       # Without country code
                "6980531698"          # Local format
            ]
            
            for alt_num in alt_formats:
                print(f"   Trying format: {alt_num}")
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                ser.write(f'AT+CMGS="{alt_num}"\r\n'.encode())
                time.sleep(1)
                
                resp = ser.read(100).decode('utf-8', errors='ignore')
                if '>' in resp:
                    print(f"   ✓ Prompt with {alt_num}!")
                    ser.write(b'\x1B')  # ESC to cancel
                    break
                else:
                    print(f"   ✗ No prompt: {repr(resp)}")
        
        print(f"\n8. Session complete")
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()