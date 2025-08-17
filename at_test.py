#!/usr/bin/env python3
import serial
import time
import sys

print("Direct AT Command Test for SIM7070G")
print("-" * 40)

# Test different serial configurations
configs = [
    ('/dev/serial0', 115200),
    ('/dev/serial0', 57600),
    ('/dev/serial0', 9600),
    ('/dev/ttyS0', 115200),
    ('/dev/ttyS0', 57600),
    ('/dev/ttyAMA0', 115200),
]

ser = None
for port, baud in configs:
    print(f"\nTrying {port} at {baud} baud...")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(1)
        
        # Send AT command
        ser.write(b'AT\r\n')
        time.sleep(0.5)
        
        # Read response
        response = ser.read(ser.in_waiting or 100)
        
        if b'OK' in response:
            print(f"✓ SUCCESS! Connected at {port} {baud} baud")
            print(f"Response: {response}")
            break
        else:
            print(f"No valid response: {response}")
            ser.close()
            
    except Exception as e:
        print(f"Error: {e}")
        if ser and ser.is_open:
            ser.close()
else:
    print("\n✗ Failed to connect to module!")
    sys.exit(1)

print("\n" + "="*40)
print("Module connected successfully!")
print("Running diagnostics...")

# Now run a series of test commands
commands = [
    ("AT", "Basic test"),
    ("ATE0", "Disable echo"),
    ("AT+CGMM", "Model info"),
    ("AT+CPIN?", "SIM status"),
    ("AT+CSQ", "Signal quality"),
    ("AT+CREG?", "Network registration"),
    ("AT+COPS?", "Operator info"),
    ("AT+CMGF=1", "Set SMS text mode"),
]

for cmd, desc in commands:
    print(f"\n{desc}: {cmd}")
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(1)
    response = ser.read(ser.in_waiting or 100).decode('utf-8', errors='ignore')
    print(f"Response: {response.strip()}")

# Now try to send SMS
print("\n" + "="*40)
print("Attempting to send SMS...")

phone = "+306976518415"
message = "Test from Pi"

# Ensure text mode
ser.write(b"AT+CMGF=1\r\n")
time.sleep(1)
ser.read(ser.in_waiting)

# Send SMS command
print(f"Sending to {phone}...")
ser.reset_input_buffer()
ser.write(f'AT+CMGS="{phone}"\r'.encode())

# Wait for prompt
time.sleep(2)
response = ser.read(ser.in_waiting or 100)
print(f"After CMGS: {response}")

if b'>' in response or len(response) == 0:
    print("Sending message text...")
    ser.write(message.encode())
    ser.write(b'\x1A')  # Ctrl+Z
    
    # Wait for confirmation
    time.sleep(10)
    response = ser.read(ser.in_waiting or 1000).decode('utf-8', errors='ignore')
    print(f"Final response: {response}")
    
    if "+CMGS" in response or "OK" in response:
        print("\n✓ SMS SENT SUCCESSFULLY!")
    else:
        print("\n✗ SMS send failed")
else:
    print("Failed to get SMS prompt")

ser.close()
