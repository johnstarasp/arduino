#!/usr/bin/env python3
import serial
import time

def test_baud_rate(port, baud_rate):
    print(f"\n--- Testing baud rate: {baud_rate} ---")
    try:
        ser = serial.Serial(port, baud_rate, timeout=3)
        time.sleep(2)
        
        # Send AT command
        ser.write(b'AT\r\n')
        time.sleep(1)
        
        response = ""
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        
        print(f"Response: '{response.strip()}'")
        
        if "OK" in response:
            print(f"SUCCESS: Module responds at {baud_rate} baud")
            ser.close()
            return True
        else:
            print(f"No OK response at {baud_rate} baud")
            
        ser.close()
        return False
        
    except Exception as e:
        print(f"Error at {baud_rate} baud: {e}")
        return False

def detailed_test(port, baud_rate):
    print(f"\n--- Detailed test at {baud_rate} baud ---")
    try:
        ser = serial.Serial(port, baud_rate, timeout=5)
        time.sleep(3)
        
        commands = [
            "AT",
            "ATI",
            "AT+CGMI",
            "AT+CGMM", 
            "AT+CGSN",
            "AT+CPIN?",
            "AT+CSQ",
            "AT+CREG?"
        ]
        
        for cmd in commands:
            print(f"\nSending: {cmd}")
            ser.write((cmd + '\r\n').encode())
            time.sleep(2)
            
            response = ""
            start_time = time.time()
            while time.time() - start_time < 3:
                if ser.in_waiting > 0:
                    response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                time.sleep(0.1)
            
            print(f"Response: '{response.strip()}'")
            
        ser.close()
        
    except Exception as e:
        print(f"Error in detailed test: {e}")

def main():
    port = '/dev/serial0'
    
    print("SIM7070G Diagnostic Tool")
    print("=" * 30)
    
    # Test common baud rates
    baud_rates = [9600, 19200, 38400, 57600, 115200]
    
    working_baud = None
    for baud in baud_rates:
        if test_baud_rate(port, baud):
            working_baud = baud
            break
    
    if working_baud:
        print(f"\nModule found working at {working_baud} baud")
        detailed_test(port, working_baud)
    else:
        print("\nNo response from module at any tested baud rate")
        print("Check:")
        print("1. Physical connections")
        print("2. Power supply")
        print("3. Module is powered on")
        print("4. UART is enabled on Raspberry Pi")

if __name__ == "__main__":
    main()