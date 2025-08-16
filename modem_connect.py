#!/usr/bin/env python3
"""
Robust modem connection script for SIMCOM SIM7070
"""

import serial
import time
import sys
import os

def check_port_availability(port):
    """Check if port is available and not in use"""
    try:
        # Check if port exists
        if not os.path.exists(port):
            print(f"✗ Port {port} does not exist")
            return False
        
        # Check if we can access it
        if not os.access(port, os.R_OK | os.W_OK):
            print(f"✗ No read/write access to {port}")
            print(f"  Need sudo: sudo python3 {sys.argv[0]}")
            return False
        
        # Try to open it briefly
        try:
            test = serial.Serial(port, 9600, timeout=0.1)
            test.close()
            return True
        except serial.SerialException as e:
            print(f"✗ Port {port} is busy or locked")
            print(f"  Error: {e}")
            
            # Check what's using the port
            print("\n  Checking processes using serial ports:")
            os.system(f"lsof {port} 2>/dev/null")
            
            # Kill any firstTry.py processes
            print("\n  Checking for running firstTry.py:")
            os.system("ps aux | grep -E 'firstTry|sms_debug' | grep -v grep")
            
            return False
            
    except Exception as e:
        print(f"✗ Error checking port: {e}")
        return False

def find_working_settings():
    """Find the correct port and baud rate"""
    ports = ["/dev/serial0", "/dev/ttyS0", "/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/ttyACM0"]
    bauds = [57600, 9600, 115200, 19200, 38400]
    
    print("Scanning for modem...")
    print("-" * 40)
    
    for port in ports:
        if not os.path.exists(port):
            continue
            
        print(f"\nChecking {port}:")
        
        if not check_port_availability(port):
            continue
        
        for baud in bauds:
            try:
                print(f"  Trying {baud} baud...", end=" ")
                
                # Open port
                ser = serial.Serial(
                    port=port,
                    baudrate=baud,
                    timeout=2,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False
                )
                
                # Wait for port to stabilize
                time.sleep(1)
                
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Send simple AT
                ser.write(b'AT\r\n')
                time.sleep(0.5)
                
                # Read response
                response = ser.read(100).decode('utf-8', errors='ignore')
                
                if 'OK' in response or 'AT' in response:
                    print("✓ FOUND!")
                    return ser, port, baud
                else:
                    print("No response")
                    ser.close()
                    
            except Exception as e:
                print(f"Error: {str(e)[:30]}")
                
    return None, None, None

def setup_and_test(ser):
    """Setup modem and test SMS"""
    print("\n" + "="*50)
    print("MODEM SETUP AND TEST")
    print("="*50)
    
    # Get modem info
    print("\n1. Modem Information:")
    ser.write(b'ATI\r\n')
    time.sleep(0.5)
    info = ser.read(200).decode('utf-8', errors='ignore')
    print(f"   {info.strip()}")
    
    # Check SIM
    print("\n2. SIM Card Status:")
    ser.write(b'AT+CPIN?\r\n')
    time.sleep(0.5)
    sim = ser.read(200).decode('utf-8', errors='ignore')
    print(f"   {sim.strip()}")
    
    if 'READY' not in sim:
        print("   ✗ SIM not ready")
        
        if 'NOT INSERTED' in sim:
            print("\n   Action needed:")
            print("   1. Power off the Pi")
            print("   2. Check SIM card is inserted correctly")
            print("   3. Power on and try again")
        elif 'SIM PIN' in sim:
            print("\n   SIM requires PIN code")
            pin = input("   Enter PIN: ")
            ser.write(f'AT+CPIN="{pin}"\r\n'.encode())
            time.sleep(3)
            resp = ser.read(200).decode('utf-8', errors='ignore')
            print(f"   Result: {resp.strip()}")
        
        return False
    
    print("   ✓ SIM ready")
    
    # Power cycle modem
    print("\n3. Resetting modem module...")
    
    # Minimum functionality
    ser.write(b'AT+CFUN=0\r\n')
    time.sleep(2)
    ser.read(100)
    
    # Full functionality
    ser.write(b'AT+CFUN=1\r\n')
    time.sleep(3)
    ser.read(100)
    
    print("   ✓ Reset complete")
    
    # Wait for network
    print("\n4. Waiting for network (this may take 30 seconds)...")
    
    for i in range(15):
        ser.write(b'AT+CREG?\r\n')
        time.sleep(0.5)
        resp = ser.read(200).decode('utf-8', errors='ignore')
        
        if '+CREG: 0,1' in resp:
            print(f"   ✓ Registered on home network (attempt {i+1})")
            break
        elif '+CREG: 0,5' in resp:
            print(f"   ✓ Registered on roaming (attempt {i+1})")
            break
        elif '+CREG: 0,2' in resp:
            print(f"   ... Searching (attempt {i+1}/15)")
            time.sleep(2)
        else:
            print(f"   ... Status: {resp.strip()}")
            time.sleep(2)
    else:
        print("   ✗ Network registration failed")
        
        # Try manual operator selection
        print("\n5. Trying manual network selection...")
        ser.write(b'AT+COPS=?\r\n')
        time.sleep(10)  # This can take a while
        networks = ser.read(1000).decode('utf-8', errors='ignore')
        print(f"   Available networks: {networks.strip()}")
        
        # Auto select
        ser.write(b'AT+COPS=0\r\n')
        time.sleep(5)
        
        return False
    
    # Check signal
    print("\n5. Signal Quality:")
    ser.write(b'AT+CSQ\r\n')
    time.sleep(0.5)
    signal = ser.read(200).decode('utf-8', errors='ignore')
    print(f"   {signal.strip()}")
    
    # Setup SMS
    print("\n6. Configuring SMS:")
    
    commands = [
        (b'ATE0\r\n', "Disable echo"),
        (b'AT+CMGF=1\r\n', "Text mode"),
        (b'AT+CSCS="GSM"\r\n', "GSM charset"),
    ]
    
    for cmd, desc in commands:
        ser.write(cmd)
        time.sleep(0.5)
        resp = ser.read(100).decode('utf-8', errors='ignore')
        status = "✓" if 'OK' in resp else "✗"
        print(f"   {status} {desc}")
    
    # Test SMS
    print("\n7. Sending test SMS:")
    phone = "+306980531698"
    print(f"   To: {phone}")
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Send SMS command
    ser.write(f'AT+CMGS="{phone}"\r\n'.encode())
    time.sleep(1)
    resp = ser.read(100).decode('utf-8', errors='ignore')
    
    if '>' in resp:
        print("   ✓ SMS prompt received")
        
        # Send message
        msg = f"Modem test OK at {time.strftime('%H:%M:%S')}"
        ser.write(msg.encode())
        ser.write(b'\x1A')  # Ctrl+Z
        
        print("   ... Sending")
        time.sleep(7)
        
        resp = ser.read(500).decode('utf-8', errors='ignore')
        if 'OK' in resp or '+CMGS' in resp:
            print("   ✓ SMS SENT SUCCESSFULLY!")
            return True
        else:
            print(f"   ✗ Send failed: {resp.strip()}")
    else:
        print(f"   ✗ No prompt: {resp.strip()}")
    
    return False

def main():
    print("="*60)
    print("SIMCOM SIM7070 MODEM CONNECTION AND TEST")
    print("="*60)
    
    # Check if running as root
    if os.geteuid() != 0:
        print("\n⚠ Warning: Not running as root")
        print("  If connection fails, run with: sudo python3", sys.argv[0])
    
    # Find modem
    ser, port, baud = find_working_settings()
    
    if not ser:
        print("\n✗ No modem found!")
        print("\nTroubleshooting:")
        print("1. Check modem is connected to USB or GPIO")
        print("2. Check modem has power (LED should be on)")
        print("3. Run with sudo: sudo python3", sys.argv[0])
        print("4. Check no other program is using the port:")
        print("   ps aux | grep -E 'firstTry|serial'")
        print("5. Try rebooting the Pi")
        return
    
    print(f"\n✓ Modem found at {port} ({baud} baud)")
    
    # Test modem
    try:
        if setup_and_test(ser):
            print("\n" + "="*60)
            print("SUCCESS! Modem is working!")
            print("="*60)
            print(f"\nUpdate your firstTry.py with:")
            print(f'SERIAL_PORT = "{port}"')
            print(f'BAUD_RATE = {baud}')
        else:
            print("\n" + "="*60)
            print("Modem connected but SMS test failed")
            print("="*60)
            print("\nPossible issues:")
            print("- SIM card has no credit")
            print("- Wrong phone number format")
            print("- Network coverage issues")
            print("- SIM card not activated")
        
        ser.close()
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
        if ser:
            ser.close()

if __name__ == "__main__":
    main()