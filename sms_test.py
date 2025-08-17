#!/usr/bin/env python3
import serial
import time
import sys

def send_at_command(ser, command, wait_time=2):
    """Send AT command and return response"""
    ser.reset_input_buffer()
    ser.write((command + '\r\n').encode('utf-8'))
    time.sleep(wait_time)
    
    response = ""
    while ser.in_waiting > 0:
        response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    
    return response.strip()

def main():
    print("SIM7070G SMS Test Script")
    print("-" * 40)
    
    # Try different baud rates
    baud_rates = [115200, 57600, 9600]
    
    for baud in baud_rates:
        print(f"\nTrying baud rate: {baud}")
        try:
            ser = serial.Serial('/dev/serial0', baud, timeout=5)
            time.sleep(2)
            
            # Test AT command
            response = send_at_command(ser, "AT", 1)
            if "OK" in response:
                print(f"✓ Connected at {baud} baud!")
                break
            else:
                print(f"No response at {baud} baud")
                ser.close()
        except Exception as e:
            print(f"Error at {baud}: {e}")
    else:
        print("Failed to connect at any baud rate")
        sys.exit(1)
    
    # Disable echo
    send_at_command(ser, "ATE0", 1)
    
    # Check SIM status
    print("\nChecking SIM card...")
    response = send_at_command(ser, "AT+CPIN?", 2)
    print(f"SIM Status: {response}")
    
    # Check network registration
    print("\nChecking network registration...")
    response = send_at_command(ser, "AT+CREG?", 2)
    print(f"Network: {response}")
    
    # Check signal strength
    response = send_at_command(ser, "AT+CSQ", 2)
    print(f"Signal: {response}")
    
    # Set SMS text mode
    print("\nConfiguring SMS...")
    response = send_at_command(ser, "AT+CMGF=1", 1)
    print(f"Text mode: {response}")
    
    # Try to send SMS
    phone = "+306976518415"  # International format
    message = "Test SMS from Pi"
    
    print(f"\nSending SMS to {phone}...")
    
    # Send CMGS command
    ser.reset_input_buffer()
    ser.write(f'AT+CMGS="{phone}"\r'.encode('utf-8'))
    
    # Wait for prompt
    time.sleep(2)
    response = ""
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    
    if '>' in response or not response:
        print("Got prompt, sending message...")
        ser.write(message.encode('utf-8'))
        ser.write(b'\x1A')  # Ctrl+Z
        
        # Wait for response
        time.sleep(10)
        response = ""
        while ser.in_waiting > 0:
            response += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        
        print(f"Response: {response}")
        
        if "+CMGS" in response or "OK" in response:
            print("✓ SMS sent successfully!")
        else:
            print("SMS send failed")
    else:
        print(f"Failed to get prompt: {response}")
    
    ser.close()

if __name__ == "__main__":
    main()
