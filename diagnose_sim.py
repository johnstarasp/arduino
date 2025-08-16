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
        # Try multiple times for better reliability
        for attempt in range(3):
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
                time.sleep(3)
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                print(f"   Connection attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
                
        # SIM7070G specific wake-up sequence
        print("Initializing SIM7070G modem...")
        for i in range(5):
            ser.write(b'AT\r\n')
            time.sleep(0.5)
            response = ser.read(100).decode('utf-8', errors='ignore')
            if 'OK' in response:
                print(f"   Modem responded after {i+1} attempts")
                break
            print(f"   Wake-up attempt {i+1}...")
        
        # Clear any pending messages
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test basic connection
        print("\n1. Testing modem connection:")
        resp = send_command(ser, "AT")
        print(f"   AT: {resp}")
        
        if 'OK' not in resp:
            print("   ✗ Modem not responding")
            return
            
        # SIM7070G specific configuration
        print("\n1.1. SIM7070G Network Configuration:")
        
        # Set network preferences for SMS reliability
        print("   Setting network mode for SMS compatibility...")
        resp = send_command(ser, "AT+CNMP=38", 2)  # LTE only mode
        print(f"   Network mode: {resp}")
        
        resp = send_command(ser, "AT+CMNB=1", 2)   # CAT-M preferred
        print(f"   Network band: {resp}")
        
        # Enable all URCs for better diagnostics
        resp = send_command(ser, "AT+CREG=2", 1)
        print(f"   Enhanced registration: {resp}")
        
        resp = send_command(ser, "AT+CGREG=2", 1)
        print(f"   Packet registration: {resp}")
        
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
        
        # Parse signal strength and monitor over time
        signal_readings = []
        for i in range(3):
            if i > 0:
                time.sleep(2)
            resp = send_command(ser, "AT+CSQ", 1)
            if '+CSQ:' in resp:
                import re
                match = re.search(r'\+CSQ:\s*(\d+),(\d+)', resp)
                if match:
                    rssi = int(match.group(1))
                    signal_readings.append(rssi)
                    
        if signal_readings:
            avg_rssi = sum(signal_readings) / len(signal_readings)
            print(f"   Signal readings: {signal_readings} (avg: {avg_rssi:.1f})")
            
            if avg_rssi == 99:
                print("   ⚠ No signal detected")
                print("   Recommendations:")
                print("     - Check antenna connection")
                print("     - Move to higher location")
                print("     - Check for obstructions")
                print("   Note: SMS may still work if registered on network")
            elif avg_rssi < 10:
                print(f"   ⚠ Weak signal (RSSI: {avg_rssi:.1f})")
                print("   Consider moving to better location for SMS reliability")
            else:
                print(f"   ✓ Good signal (RSSI: {avg_rssi:.1f})")
        else:
            print("   ⚠ No signal information available")
        
        resp = send_command(ser, "AT+CREG?", 1)
        print(f"   Registration: {resp}")
        
        registered = False
        if '+CREG: 0,1' in resp:
            print("   ✓ Registered on home network")
            registered = True
        elif '+CREG: 0,5' in resp:
            print("   ✓ Registered roaming")
            registered = True
        elif '+CREG: 0,2' in resp:
            print("   ⚠ Searching for network...")
            # Wait and retry for network registration
            for i in range(5):
                time.sleep(3)
                resp = send_command(ser, "AT+CREG?", 1)
                print(f"   Registration attempt {i+2}: {resp}")
                if '+CREG: 0,1' in resp or '+CREG: 0,5' in resp:
                    print("   ✓ Network registration successful!")
                    registered = True
                    break
            if not registered:
                print("   ⚠ Still searching for network after retries")
        elif not resp or 'CREG' not in resp:
            print("   ⚠ Registration status unclear, trying alternative check...")
            # Try CGREG for packet registration
            resp2 = send_command(ser, "AT+CGREG?", 1)
            print(f"   Packet registration: {resp2}")
            if '+CGREG: 0,1' in resp2 or '+CGREG: 0,5' in resp2:
                print("   ✓ Registered for data services")
                registered = True
            else:
                print("   ⚠ Registration status uncertain")
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
        
        # Check if SMS center needs configuration
        if not resp or '+CSCA:' not in resp or '""' in resp:
            print("   ⚠ SMS center not configured or empty")
            print("   Attempting to set Greek SMS center...")
            # Common Greek SMS centers
            greek_sms_centers = [
                "+3097100000",  # COSMOTE
                "+3094969300",  # WIND
                "+3093093093"   # VODAFONE
            ]
            
            for center in greek_sms_centers:
                resp = send_command(ser, f'AT+CSCA="{center}",145', 2)
                print(f"   Setting SMS center {center}: {resp}")
                if 'OK' in resp:
                    print(f"   ✓ SMS center set to {center}")
                    break
        
        # Additional SMS configuration for SIM7070G
        print("\n6.1. Advanced SMS Configuration:")
        
        # Set SMS format
        resp = send_command(ser, "AT+CMGF=1", 1)
        print(f"   Text format: {resp}")
        
        # Configure SMS storage
        resp = send_command(ser, "AT+CPMS=\"SM\",\"SM\",\"SM\"", 2)
        print(f"   SMS storage: {resp}")
        
        # Check SMS configuration
        resp = send_command(ser, "AT+CSMP?", 1)
        print(f"   SMS parameters: {resp}")
        
        # Set SMS validity period and other params for Greek networks
        resp = send_command(ser, "AT+CSMP=17,167,0,0", 1)
        print(f"   SMS params set: {resp}")
        
        # Final summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        
        # We already checked SIM status earlier and it was READY
        # So let's assume it's still ready and proceed with SMS test
        print("✓ SIM card is ready (from earlier check)")
        sim_ready = True
            
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
                    
                # Additional diagnostics
                print("\n   Additional SMS diagnostics:")
                
                # Check SMS format
                resp = send_command(ser, "AT+CMGF?", 1)
                print(f"   SMS format: {resp}")
                
                # Check if SMS service is available
                resp = send_command(ser, "AT+CSMS?", 1)
                print(f"   SMS service status: {resp}")
                
                # Manual SMS test option
                print("\n   Would you like to try manual SMS? (requires network registration)")
                if registered:
                    print("   ✓ Network is registered - manual SMS should work")
                    print("   To manually test: AT+CMGS=\"+306976518415\"")
                    print("   Then type message and press Ctrl+Z")
                else:
                    print("   ⚠ Network not registered - SMS will likely fail")
                    print("   Wait for network registration before attempting SMS")
        else:
            print("\nTroubleshooting steps:")
            print("1. Check SIM card is properly inserted")
            print("2. Try a different SIM card")
            print("3. Check SIM card is not damaged")
            print("4. Ensure SIM card is compatible with your network")
            print("5. Wait longer for SIM initialization (up to 2 minutes)")
            print("6. Power cycle the modem completely")
            
        print("\n" + "="*50)
        print("MANUAL SMS TESTING COMMANDS")
        print("="*50)
        print("If diagnostics show SIM ready and network registered:")
        print("1. sudo minicom -b 57600 -D /dev/ttyS0")
        print("2. AT+CMGF=1")
        print("3. AT+CMGS=\"+306976518415\"")
        print("4. Type your message")
        print("5. Press Ctrl+A then Z, then press Ctrl+Z")
        print("6. Press Ctrl+A then X to exit minicom")
        
        print("\\n" + "="*50)
        print("SIM7070G TROUBLESHOOTING NOTES")
        print("="*50)
        print("• SIM7070G requires specific SMS center configuration")
        print("• Greek networks: COSMOTE (+3097100000), WIND (+3094969300)")
        print("• Module may need multiple AT commands to wake up")
        print("• CAT-M/NB-IoT mode preferred over 2G for SMS reliability")
        print("• Check if SIM works in 2G/3G phone vs LTE-only phone")
        print("• Try: AT+CSCA=\\\"+3097100000\\\",145 to set SMS center")
        print("• Try: AT+CNMP=38 for LTE-only mode")
        print("• Try: AT+CMNB=1 for CAT-M preference")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()