#!/usr/bin/env python3
"""
SMS fix specifically for SIM7070G Cat-M/NB-IoT/GPRS HAT
Based on SIM7080 Series AT Command Manual
"""

import serial
import time

SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600
PHONE_NUMBER = "+306980531698"

def send_command(ser, cmd, wait_time=2, description=""):
    """Send AT command with proper timing for SIM7070G"""
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    print(f"   → {cmd} ({description})")
    ser.write(cmd.encode() + b'\r\n')
    time.sleep(wait_time)
    
    response = ser.read(1000).decode('utf-8', errors='ignore')
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    
    for line in lines:
        print(f"   ← {line}")
    
    return response

def main():
    print("="*70)
    print("SIM7070G Cat-M/NB-IoT SMS CONFIGURATION")
    print("Waveshare HAT - Following SIM7080 AT Command Manual")
    print("="*70)
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=10)
        time.sleep(3)
        
        print("\n1. Basic modem initialization:")
        
        # Basic AT test
        resp = send_command(ser, "AT", 1, "Test communication")
        if 'OK' not in resp:
            print("✗ Modem not responding")
            return
        
        # Get module info
        send_command(ser, "ATI", 1, "Module information")
        
        # Check SIM status
        resp = send_command(ser, "AT+CPIN?", 2, "SIM card status")
        if 'READY' not in resp:
            print("✗ SIM card not ready")
            if 'SIM PIN' in resp:
                pin = input("Enter SIM PIN: ")
                send_command(ser, f'AT+CPIN="{pin}"', 5, "Enter PIN")
            else:
                return
        
        print("\n2. Network configuration for SIM7070G:")
        
        # Set network mode for Cat-M (important for SMS)
        send_command(ser, "AT+CNMP=38", 3, "Set all network modes")
        send_command(ser, "AT+CMNB=1", 3, "Enable Cat-M1")
        
        # Set APN (important for some SMS functions)
        send_command(ser, 'AT+CGDCONT=1,"IP","internet"', 2, "Set APN")
        
        # Check network registration
        for i in range(10):
            resp = send_command(ser, "AT+CREG?", 1, f"Network registration check {i+1}")
            if '+CREG: 0,1' in resp or '+CREG: 0,5' in resp:
                print("   ✓ Network registered")
                break
            elif '+CREG: 0,2' in resp:
                print("   ... Still searching for network")
                time.sleep(3)
            else:
                print(f"   Registration status: {resp}")
                time.sleep(3)
        
        # Check signal quality
        send_command(ser, "AT+CSQ", 1, "Signal quality")
        
        print("\n3. SMS configuration for SIM7070G:")
        
        # Critical: Set operating mode for SMS
        send_command(ser, "AT+CFUN=1", 3, "Set full functionality")
        
        # SMS service configuration
        send_command(ser, "AT+CSMS=1", 2, "Enable SMS service")
        
        # Set SMS format to text mode
        send_command(ser, "AT+CMGF=1", 1, "Set text mode")
        
        # Set SMS parameters (format, validity, etc.)
        send_command(ser, "AT+CSMP=17,167,0,0", 1, "SMS parameters")
        
        # Set character set
        send_command(ser, 'AT+CSCS="GSM"', 1, "GSM character set")
        
        # Set SMS storage to phone memory (more reliable than SIM)
        send_command(ser, 'AT+CPMS="ME","ME","ME"', 2, "Phone memory storage")
        
        # Disable SMS indications to avoid interference
        send_command(ser, "AT+CNMI=0,0,0,0,0", 1, "Disable SMS notifications")
        
        # Check/Set SMS center (critical for SMS sending)
        resp = send_command(ser, "AT+CSCA?", 1, "Check SMS center")
        
        if '""' in resp or 'ERROR' in resp:
            print("   Setting SMS center for Greece...")
            # Greek mobile operators SMS centers
            sms_centers = [
                "+306942000000",  # Cosmote
                "+306977000000",  # Vodafone  
                "+306948000000"   # Wind/Three
            ]
            
            for center in sms_centers:
                resp = send_command(ser, f'AT+CSCA="{center}"', 2, f"Set SMS center {center}")
                if 'OK' in resp:
                    break
        
        print("\n4. Testing SMS sending:")
        
        # Clear buffers completely
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(1)
        
        print(f"   Sending SMS to {PHONE_NUMBER}")
        
        # Send CMGS command
        ser.write(f'AT+CMGS="{PHONE_NUMBER}"\r\n'.encode())
        print(f"   → AT+CMGS=\"{PHONE_NUMBER}\"")
        
        # Wait for prompt with detailed monitoring
        response = ""
        prompt_found = False
        
        for i in range(50):  # 5 seconds with 0.1s intervals
            time.sleep(0.1)
            
            while ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                print(f"   ← {repr(chunk)}")
                
                if '> ' in response or '>' in response:
                    prompt_found = True
                    print("   ✓ SMS prompt received!")
                    break
                elif 'ERROR' in response:
                    print(f"   ✗ Error: {response}")
                    break
            
            if prompt_found or 'ERROR' in response:
                break
        
        if prompt_found:
            # Send message content
            message = f"SIM7070G test from Pi - {time.strftime('%H:%M:%S')}"
            print(f"   → Message: {message}")
            
            ser.write(message.encode())
            ser.write(b'\x1A')  # Ctrl+Z to send
            
            # Wait for send confirmation
            print("   Waiting for send confirmation...")
            response = ""
            
            for i in range(100):  # 10 seconds
                time.sleep(0.1)
                
                while ser.in_waiting > 0:
                    chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    response += chunk
                    print(f"   ← {repr(chunk)}")
                    
                    if '+CMGS:' in response:
                        print("\n   ✓ SMS SENT SUCCESSFULLY!")
                        msg_id = response.split('+CMGS:')[1].strip().split()[0] if '+CMGS:' in response else "unknown"
                        print(f"   Message ID: {msg_id}")
                        break
                    elif 'OK' in response and i > 20:  # Give some time for +CMGS
                        print("\n   ✓ SMS probably sent (OK received)")
                        break
                    elif '+CMS ERROR:' in response:
                        error_code = response.split('+CMS ERROR:')[1].strip().split()[0]
                        print(f"\n   ✗ SMS failed with CMS ERROR: {error_code}")
                        break
                
                if '+CMGS:' in response or 'OK' in response or '+CMS ERROR:' in response:
                    break
            
            if '+CMGS:' not in response and 'OK' not in response:
                print(f"\n   ? No clear confirmation. Full response: {response}")
        
        else:
            print(f"\n   ✗ No SMS prompt received")
            print(f"   Full response: {repr(response)}")
            
            # Try troubleshooting
            print("\n5. Troubleshooting:")
            
            # Check if modem is busy
            send_command(ser, "AT+CPAS", 1, "Check modem status")
            
            # Try resetting SMS service
            send_command(ser, "AT+CSMS=0", 1, "Disable SMS")
            time.sleep(1)
            send_command(ser, "AT+CSMS=1", 2, "Re-enable SMS")
            
            # Check current settings
            send_command(ser, "AT+CMGF?", 1, "Check SMS format")
            send_command(ser, "AT+CSCA?", 1, "Check SMS center")
        
        print("\n" + "="*70)
        print("CONFIGURATION FOR firstTry.py:")
        print("="*70)
        print(f'SERIAL_PORT = "{SERIAL_PORT}"')
        print(f'BAUD_RATE = {BAUD_RATE}')
        print("\nAdd these commands to init_modem():")
        print('commands = [')
        print('    (b\'AT\\r\', "Basic AT test"),')
        print('    (b\'AT+CFUN=1\\r\', "Full functionality"),')
        print('    (b\'AT+CNMP=38\\r\', "All network modes"),')  
        print('    (b\'AT+CMNB=1\\r\', "Enable Cat-M1"),')
        print('    (b\'AT+CSMS=1\\r\', "Enable SMS service"),')
        print('    (b\'AT+CMGF=1\\r\', "SMS text mode"),')
        print('    (b\'AT+CSMP=17,167,0,0\\r\', "SMS parameters"),')
        print('    (b\'AT+CSCS="GSM"\\r\', "Character set"),')
        print('    (b\'AT+CPMS="ME","ME","ME"\\r\', "Phone memory"),')
        print('    (b\'AT+CNMI=0,0,0,0,0\\r\', "Disable notifications")')
        print(']')
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()