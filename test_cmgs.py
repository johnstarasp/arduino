#!/usr/bin/env python3
import serial
import time

def test_cmgs():
    port = '/dev/serial0'
    baudrate = 57600
    
    print("Testing AT+CMGS command only")
    print("=" * 30)
    
    try:
        ser = serial.Serial(port, baudrate, timeout=10)
        print(f"Connected to {port} at {baudrate} baud")
        time.sleep(2)
        
        # Test basic AT command first
        print("\nTesting basic AT command...")
        ser.write(b'AT\r\n')
        time.sleep(1)
        
        response = ""
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(f"AT response: '{response.strip()}'")
        
        if "OK" not in response:
            print("Basic AT command failed")
            return
            
        # Clear buffer
        while ser.in_waiting > 0:
            ser.read(ser.in_waiting)
            time.sleep(0.1)
            
        # Test CMGS command
        print("\nTesting AT+CMGS command...")
        cmgs_command = 'AT+CMGS="+306976518415"'
        print(f"Sending: {cmgs_command}")
        
        ser.write((cmgs_command + '\r\n').encode())
        
        # Wait for response
        response = ""
        start_time = time.time()
        while time.time() - start_time < 15:
            if ser.in_waiting > 0:
                new_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += new_data
                print(f"Received: '{new_data.strip()}'")
            time.sleep(0.2)
            if ">" in response or "ERROR" in response:
                break
                
        print(f"\nFinal response: '{response.strip()}'")
        
        if ">" in response:
            print("SUCCESS: Got SMS prompt!")
        elif "ERROR" in response:
            print("ERROR: CMGS command failed")
        else:
            print("TIMEOUT: No response to CMGS command")
            
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_cmgs()