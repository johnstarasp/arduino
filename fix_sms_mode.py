#!/usr/bin/env python3
"""
Fix SMS mode for SIMCOM SIM7070 LTE modem
CMS ERROR 304 means wrong SMS mode configuration
"""

import serial
import time

# Your correct settings
SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600
PHONE_NUMBER = "+306980531698"

def send_command(ser, cmd, wait=1):
    """Send AT command and get response"""
    ser.write(cmd.encode() + b'\r\n')
    time.sleep(wait)
    response = ser.read(500).decode('utf-8', errors='ignore')
    return response.strip()

def main():
    print("="*60)
    print("FIXING SMS MODE FOR SIM7070 LTE MODEM")
    print("="*60)
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
        time.sleep(2)
        
        print("✓ Connected to modem")
        
        # Test basic connection
        resp = send_command(ser, "AT")
        if 'OK' not in resp:
            print("✗ Modem not responding")
            return
        
        print("\n1. Checking current SMS configuration:")
        
        # Check current SMS format
        resp = send_command(ser, "AT+CMGF?")
        print(f"   Message format: {resp}")
        
        # Check SMS service
        resp = send_command(ser, "AT+CSMS?")
        print(f"   SMS service: {resp}")
        
        # Check preferred message storage
        resp = send_command(ser, "AT+CPMS?")
        print(f"   Message storage: {resp}")
        
        print("\n2. Configuring SMS for SIM7070:")
        
        # Enable SMS service first
        resp = send_command(ser, "AT+CSMS=1", 2)
        print(f"   Enable SMS service: {'✓' if 'OK' in resp else '✗'} {resp}")
        
        # Set message format to text mode
        resp = send_command(ser, "AT+CMGF=1", 1)
        print(f"   Text mode: {'✓' if 'OK' in resp else '✗'} {resp}")
        
        # Set character set
        resp = send_command(ser, 'AT+CSCS="GSM"', 1)
        print(f"   Character set: {'✓' if 'OK' in resp else '✗'} {resp}")
        
        # Set SMS text mode parameters
        resp = send_command(ser, "AT+CSMP=17,167,0,0", 1)
        print(f"   SMS parameters: {'✓' if 'OK' in resp else '✗'} {resp}")
        
        # Set message storage to SIM
        resp = send_command(ser, 'AT+CPMS="SM","SM","SM"', 2)
        print(f"   Message storage: {'✓' if 'OK' in resp else '✗'} {resp}")
        
        # For LTE modems, check if we need to set specific network mode
        print("\n3. Checking network mode:")
        resp = send_command(ser, "AT+CNSMOD?")
        print(f"   Network mode: {resp}")
        
        # If it's in LTE-only mode, we might need to enable 2G/3G for SMS
        if 'LTE' in resp and '2G' not in resp:
            print("   Setting network mode to support SMS...")
            resp = send_command(ser, "AT+CNMP=38", 3)  # All network modes
            print(f"   Network mode set: {'✓' if 'OK' in resp else '✗'} {resp}")
            
            # Wait for re-registration
            print("   Waiting for network re-registration...")
            time.sleep(10)
        
        # Check network registration again
        resp = send_command(ser, "AT+CREG?")
        print(f"   Registration: {resp}")
        
        print("\n4. Testing SMS with corrected settings:")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Try sending SMS
        print(f"   Sending to {PHONE_NUMBER}...")
        
        ser.write(f'AT+CMGS="{PHONE_NUMBER}"\r\n'.encode())
        time.sleep(1)
        
        # Read response
        response = ""
        for _ in range(10):  # Try reading multiple times
            chunk = ser.read(50).decode('utf-8', errors='ignore')
            response += chunk
            if '>' in response or 'ERROR' in response:
                break
            time.sleep(0.1)
        
        print(f"   Response: {response.strip()}")
        
        if '>' in response:
            print("   ✓ SMS prompt received!")
            
            # Send message
            message = f"SIM7070 test at {time.strftime('%H:%M:%S')}"
            ser.write(message.encode())
            ser.write(b'\x1A')  # Ctrl+Z
            
            print("   Sending message...")
            time.sleep(8)  # Give more time for LTE
            
            # Read final response
            final_response = ser.read(500).decode('utf-8', errors='ignore')
            print(f"   Final response: {final_response.strip()}")
            
            if '+CMGS:' in final_response or 'OK' in final_response:
                print("\n✓ SMS SENT SUCCESSFULLY!")
                
                print("\n" + "="*60)
                print("SUCCESS! Update your firstTry.py:")
                print("="*60)
                print(f'SERIAL_PORT = "{SERIAL_PORT}"')
                print(f'BAUD_RATE = {BAUD_RATE}')
                print("\nAlso add these SMS initialization commands:")
                print('# In init_modem() method, add:')
                print('(b\'AT+CSMS=1\\r\', "Enable SMS service"),')
                print('(b\'AT+CSMP=17,167,0,0\\r\', "SMS parameters"),')
                
            else:
                print(f"\n✗ SMS failed: {final_response}")
                
                # Try alternative SMS center
                print("\n5. Trying to set SMS center manually:")
                resp = send_command(ser, "AT+CSCA?")
                print(f"   Current SMS center: {resp}")
                
                # Common Greek SMS centers
                sms_centers = [
                    '"+306942000000"',  # Cosmote
                    '"+306977000000"',  # Vodafone
                    '"+306948000000"'   # Wind
                ]
                
                for center in sms_centers:
                    resp = send_command(ser, f"AT+CSCA={center}")
                    if 'OK' in resp:
                        print(f"   Set SMS center to {center}")
                        break
                        
        else:
            print(f"   ✗ No SMS prompt. Error: {response}")
            
            if 'CMS ERROR' in response:
                error_match = response.split('CMS ERROR:')
                if len(error_match) > 1:
                    error_code = error_match[1].strip().split()[0]
                    print(f"   CMS Error code: {error_code}")
                    
                    error_meanings = {
                        '304': 'Invalid PDU mode parameter',
                        '330': 'SMSC address unknown',
                        '500': 'Unknown error',
                        '514': 'Invalid message format'
                    }
                    
                    if error_code in error_meanings:
                        print(f"   Meaning: {error_meanings[error_code]}")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()