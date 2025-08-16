#!/usr/bin/env python3
"""
Diagnose SIM card issues with SIM7070G
"""

import serial
import time
import os

SERIAL_PORT = "/dev/ttyS0"
BAUD_RATE = 57600

def send_command(ser, cmd, wait=1):
    """Send command and return response"""
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.write(cmd.encode() + b'\r\n')
    time.sleep(wait)
    response = ser.read(1000).decode('utf-8', errors='ignore')
    # Clean up response - remove echoed command and extra whitespace
    lines = response.strip().split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and line != cmd and not line.startswith('DST:') and not line.startswith('*PSUTTZ:'):
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def main():
    print("="*50)
    print("SIM7070G SIM CARD DIAGNOSTICS")
    print("="*50)
    
    if os.geteuid() != 0:
        print("Run with: sudo python3 diagnose_sim.py")
        return
    
    try:
        print("Connecting to modem...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
        time.sleep(3)
        
        # Test basic connection
        print("\n1. Testing modem connection:")
        resp = send_command(ser, "AT")
        print(f"   AT: {resp}")
        
        if 'OK' not in resp:
            print("   ✗ Modem not responding")
            return
        
        # Get modem info
        print("\n2. Modem information:")
        resp = send_command(ser, "ATI")
        print(f"   Model: {resp}")
        
        # Check SIM card status in detail
        print("\n3. Detailed SIM status:")
        
        resp = send_command(ser, "AT+CPIN?", 2)
        print(f"   SIM PIN status: {resp}")
        
        # Handle empty response
        if not resp or resp == 'AT+CPIN?':
            print("   ⚠ Empty response, trying again...")
            time.sleep(2)
            resp = send_command(ser, "AT+CPIN?", 3)
            print(f"   SIM PIN status (retry): {resp}")
        
        if 'SIM PIN' in resp:
            print("   → SIM requires PIN code")
            pin = input("   Enter SIM PIN: ")
            resp = send_command(ser, f'AT+CPIN="{pin}"', 5)
            print(f"   PIN result: {resp}")
            
            # Check again after PIN
            time.sleep(2)
            resp = send_command(ser, "AT+CPIN?", 2)
            print(f"   SIM status after PIN: {resp}")
            
        elif 'SIM PUK' in resp:
            print("   ✗ SIM is PUK locked - need PUK code")
            puk = input("   Enter PUK code: ")
            new_pin = input("   Enter new PIN: ")
            resp = send_command(ser, f'AT+CPIN="{puk}","{new_pin}"', 5)
            print(f"   PUK result: {resp}")
            
        elif 'NOT INSERTED' in resp:
            print("   ✗ SIM card not detected")
            print("   Actions to try:")
            print("   1. Power off Pi completely")
            print("   2. Remove and reinsert SIM card")
            print("   3. Check SIM card orientation")
            print("   4. Power on Pi again")
            return
            
        elif 'NOT READY' in resp:
            print("   ⚠ SIM initializing...")
            for i in range(10):
                time.sleep(2)
                resp = send_command(ser, "AT+CPIN?", 1)
                print(f"   Attempt {i+1}: {resp}")
                if 'READY' in resp:
                    break
            
        elif 'READY' in resp:
            print("   ✓ SIM is ready")
        else:
            print(f"   ? Unknown status: {resp}")
        
        # Check SIM card info
        print("\n4. SIM card information:")
        
        resp = send_command(ser, "AT+CIMI", 2)
        print(f"   IMSI: {resp}")
        
        resp = send_command(ser, "AT+CCID", 2)
        print(f"   SIM ID: {resp}")
        
        resp = send_command(ser, "AT+CGSN", 1)
        print(f"   IMEI: {resp}")
        
        # Check operator and signal
        print("\n5. Network status:")
        
        resp = send_command(ser, "AT+COPS?", 2)
        print(f"   Operator: {resp}")
        
        resp = send_command(ser, "AT+CSQ", 1)
        print(f"   Signal: {resp}")
        
        # Parse signal strength
        if '+CSQ:' in resp:
            import re
            match = re.search(r'\+CSQ:\s*(\d+),(\d+)', resp)
            if match:
                rssi = int(match.group(1))
                if rssi == 99:
                    print("   ⚠ No signal detected")
                    print("   Check antenna connection!")
                    print("   Note: SMS may still work if registered on network")
                elif rssi < 10:
                    print(f"   ⚠ Weak signal (RSSI: {rssi})")
                else:
                    print(f"   ✓ Good signal (RSSI: {rssi})")
            else:
                print("   ⚠ Could not parse signal strength")
        else:
            print("   ⚠ No signal information available")
        
        resp = send_command(ser, "AT+CREG?", 1)
        print(f"   Registration: {resp}")
        
        if '+CREG: 0,1' in resp:
            print("   ✓ Registered on home network")
        elif '+CREG: 0,5' in resp:
            print("   ✓ Registered roaming")
        elif '+CREG: 0,2' in resp:
            print("   ⚠ Searching for network")
        else:
            print("   ✗ Not registered")
        
        # Test SMS capability
        print("\n6. SMS service test:")
        
        resp = send_command(ser, "AT+CSMS=1", 2)
        print(f"   SMS service: {resp}")
        
        resp = send_command(ser, "AT+CMGF=1", 1)
        print(f"   Text mode: {resp}")
        
        resp = send_command(ser, "AT+CSCA?", 1)
        print(f"   SMS center: {resp}")
        
        # Final summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        
        # Check final SIM status
        resp = send_command(ser, "AT+CPIN?", 1)
        
        # Handle empty response in final check
        if not resp or resp == 'AT+CPIN?':
            print("⚠ SIM status check returned empty, trying alternative method...")
            # Try alternative SIM check
            resp = send_command(ser, "AT+CIMI", 2)
            if resp and len(resp) > 10 and resp.isdigit():
                print("✓ SIM card is ready (verified via IMSI)")
                sim_ready = True
            else:
                print("✗ SIM card not responding")
                sim_ready = False
        elif 'READY' in resp:
            print("✓ SIM card is ready")
            sim_ready = True
        else:
            print(f"✗ SIM still not ready: {resp}")
            sim_ready = False
            
        if sim_ready:
            # Quick SMS test
            print("\nTrying quick SMS test...")
            ser.reset_input_buffer()
            ser.write(b'AT+CMGS="+306976518415"\r\n')
            time.sleep(2)
            resp = ser.read(200).decode('utf-8', errors='ignore')
            
            if '>' in resp:
                print("✓ SMS prompt received - modem ready for SMS!")
                ser.write(b'\x1B')  # Cancel
                time.sleep(1)
                ser.read(100)  # Clear any remaining response
            else:
                print(f"✗ SMS test failed: {resp}")
                # Try to check SMS center configuration
                sms_center_resp = send_command(ser, "AT+CSCA?", 1)
                if '+CSCA:' in sms_center_resp:
                    print(f"   SMS center is configured: {sms_center_resp}")
                else:
                    print("   ⚠ SMS center may not be configured")
        else:
            print("\nTroubleshooting steps:")
            print("1. Check SIM card is properly inserted")
            print("2. Try a different SIM card")
            print("3. Check SIM card is not damaged")
            print("4. Ensure SIM card is compatible with your network")
            print("5. Wait longer for SIM initialization (up to 2 minutes)")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()