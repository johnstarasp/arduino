#!/usr/bin/env python3
"""
Final SMS fix for SIM7070 - handles timing and buffer issues
"""

import serial
import time

SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600
PHONE_NUMBER = "+306980531698"

def clear_and_wait(ser, wait_time=0.5):
    """Clear buffers and wait"""
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(wait_time)

def send_at_cmd(ser, command, timeout=3, expect_ok=True):
    """Send AT command with proper timing"""
    clear_and_wait(ser, 0.2)
    
    print(f"   Sending: {command}")
    ser.write(command.encode() + b'\r\n')
    
    # Read response with timeout
    response = ""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            response += chunk
            
            if expect_ok and 'OK' in response:
                break
            elif not expect_ok and ('>' in response or 'ERROR' in response):
                break
        time.sleep(0.1)
    
    print(f"   Response: {response.strip()}")
    return response

def main():
    print("="*60)
    print("FINAL SMS FIX FOR SIM7070")
    print("="*60)
    
    try:
        # Open serial with specific settings for SIM7070
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            timeout=5,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        
        print("✓ Connected to SIM7070")
        time.sleep(2)
        
        # Step 1: Basic modem test
        print("\n1. Testing modem response:")
        resp = send_at_cmd(ser, "AT")
        if 'OK' not in resp:
            print("✗ Modem not responding properly")
            return
        
        # Step 2: Complete SMS setup
        print("\n2. Complete SMS configuration:")
        
        commands = [
            ("ATE0", "Disable echo"),
            ("AT+CSMS=1", "Enable SMS service"), 
            ("AT+CMGF=1", "Set text mode"),
            ("AT+CSMP=17,167,0,0", "SMS parameters"),
            ("AT+CNMI=0,0,0,0,0", "Disable SMS notifications"),
            ("AT+CPMS=\"ME\",\"ME\",\"ME\"", "Use phone memory")
        ]
        
        for cmd, desc in commands:
            resp = send_at_cmd(ser, cmd, timeout=3)
            status = "✓" if 'OK' in resp else "✗"
            print(f"   {status} {desc}")
            time.sleep(0.5)
        
        # Step 3: Check SMS center
        print("\n3. SMS Center configuration:")
        resp = send_at_cmd(ser, "AT+CSCA?")
        
        if '+CSCA:' not in resp or '""' in resp:
            print("   Setting SMS center for Greece...")
            # Try Cosmote SMS center
            send_at_cmd(ser, 'AT+CSCA="+306942000000"')
        
        # Step 4: Test with detailed SMS sending
        print("\n4. Sending SMS with detailed monitoring:")
        
        # Clear everything
        clear_and_wait(ser, 1)
        
        print(f"   Target: {PHONE_NUMBER}")
        
        # Send CMGS command
        cmd = f'AT+CMGS="{PHONE_NUMBER}"'
        ser.write(cmd.encode() + b'\r\n')
        print(f"   Sent: {cmd}")
        
        # Wait and monitor for prompt
        response = ""
        prompt_received = False
        
        for i in range(30):  # 3 seconds total
            time.sleep(0.1)
            
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                print(f"   [{i:2d}] Buffer: {repr(chunk)}")
                
                if '>' in response:
                    prompt_received = True
                    print("   ✓ SMS prompt detected!")
                    break
                elif 'ERROR' in response:
                    print(f"   ✗ Error received: {response}")
                    break
        
        if prompt_received:
            # Send the message
            message = f"SIM7070 working! Time: {time.strftime('%H:%M:%S')}"
            print(f"   Sending message: {message}")
            
            ser.write(message.encode())
            time.sleep(0.1)
            ser.write(b'\x1A')  # Ctrl+Z
            
            print("   Message sent, waiting for confirmation...")
            
            # Wait for send confirmation
            final_response = ""
            for i in range(100):  # 10 seconds
                time.sleep(0.1)
                
                if ser.in_waiting > 0:
                    chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    final_response += chunk
                    print(f"   [{i:2d}] Response: {repr(chunk)}")
                    
                    if '+CMGS:' in final_response:
                        print("\n   ✓ SMS SENT SUCCESSFULLY!")
                        print(f"   Message ID in response: {final_response}")
                        break
                    elif 'OK' in final_response and len(final_response) > 10:
                        print("\n   ✓ SMS SENT (OK received)")
                        break
                    elif 'ERROR' in final_response:
                        print(f"\n   ✗ SMS send failed: {final_response}")
                        break
            else:
                print(f"\n   ? Timeout waiting for confirmation. Last response: {final_response}")
        
        else:
            print(f"\n   ✗ No SMS prompt received. Full response: {repr(response)}")
            
            # Debug: Try alternative approach
            print("\n5. Alternative SMS method:")
            
            # Try PDU mode
            clear_and_wait(ser, 1)
            resp = send_at_cmd(ser, "AT+CMGF=0")  # PDU mode
            if 'OK' in resp:
                print("   Switched to PDU mode - this might work better")
                
                # Switch back to text mode
                send_at_cmd(ser, "AT+CMGF=1")
            
            # Try different phone number format
            alt_numbers = [
                PHONE_NUMBER.replace('+30', '0030'),  # International format
                PHONE_NUMBER.replace('+', '00'),       # Alternative international
                PHONE_NUMBER[3:] if PHONE_NUMBER.startswith('+30') else PHONE_NUMBER  # Local format
            ]
            
            for alt_num in alt_numbers:
                if alt_num != PHONE_NUMBER:
                    print(f"   Trying alternative number format: {alt_num}")
                    clear_and_wait(ser, 0.5)
                    
                    ser.write(f'AT+CMGS="{alt_num}"\r\n'.encode())
                    time.sleep(1)
                    
                    resp = ser.read(200).decode('utf-8', errors='ignore')
                    if '>' in resp:
                        print(f"   ✓ Prompt received with {alt_num}")
                        ser.write(b'\x1B')  # ESC to cancel
                        break
                    else:
                        print(f"   ✗ No prompt with {alt_num}")
        
        # Final configuration summary
        print("\n" + "="*60)
        print("CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Port: {SERIAL_PORT}")
        print(f"Baud: {BAUD_RATE}")
        print(f"Phone: {PHONE_NUMBER}")
        print("\nTo update firstTry.py, change these lines:")
        print(f'SERIAL_PORT = "{SERIAL_PORT}"')
        print(f'BAUD_RATE = {BAUD_RATE}')
        
        print("\nAnd add this to the init_modem() method:")
        print('commands = [')
        print('    (b\'AT\\r\', "Basic AT test"),')
        print('    (b\'ATE0\\r\', "Disable echo"),')
        print('    (b\'AT+CSMS=1\\r\', "Enable SMS service"),')
        print('    (b\'AT+CMGF=1\\r\', "Set SMS text mode"),')
        print('    (b\'AT+CSMP=17,167,0,0\\r\', "SMS parameters"),')
        print('    (b\'AT+CNMI=0,0,0,0,0\\r\', "Disable notifications"),')
        print('    (b\'AT+CPMS="ME","ME","ME"\\r\', "Use phone memory")')
        print(']')
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()