#!/usr/bin/env python3
import serial
import time
import sys

def send_cmd(ser, cmd, wait=1):
    """Send command and return response"""
    ser.reset_input_buffer()
    ser.write((cmd + '\r\n').encode())
    time.sleep(wait)
    response = b''
    while ser.in_waiting:
        response += ser.read(ser.in_waiting)
    return response.decode('utf-8', errors='ignore')

# Try to connect
print("Connecting to SIM7070G...")
ser = None

for baud in [115200, 57600, 9600]:
    try:
        print(f"Trying {baud} baud...")
        ser = serial.Serial('/dev/serial0', baud, timeout=5)
        time.sleep(2)
        
        # Test connection
        resp = send_cmd(ser, "AT")
        if "OK" in resp or "AT" in resp:
            print(f"✓ Connected at {baud} baud")
            break
        ser.close()
    except Exception as e:
        print(f"Error: {e}")
        if ser:
            ser.close()

if not ser or not ser.is_open:
    print("Failed to connect!")
    sys.exit(1)

# Configure module
print("\nConfiguring module...")
send_cmd(ser, "ATE0")  # Disable echo
print("SIM Status:", send_cmd(ser, "AT+CPIN?"))
print("Signal:", send_cmd(ser, "AT+CSQ"))
print("Network:", send_cmd(ser, "AT+CREG?"))

# Configure SMS
print("\nConfiguring SMS...")
resp = send_cmd(ser, "AT+CMGF=1")  # Text mode
print("Text mode:", "OK" in resp)

# Send SMS
phone = "+306976518415"
message = "Test SMS from Raspberry Pi"

print(f"\nSending SMS to {phone}...")

# Clear buffer
ser.reset_input_buffer()

# Send CMGS command
ser.write(f'AT+CMGS="{phone}"\r'.encode())

# Wait for prompt (> character)
time.sleep(3)
prompt_resp = ser.read(ser.in_waiting or 100)
print(f"After CMGS: {prompt_resp}")

# Send message regardless of prompt
print("Sending message text...")
ser.write(message.encode())
time.sleep(0.5)
ser.write(b'\x1A')  # Ctrl+Z

# Wait for confirmation
print("Waiting for confirmation...")
time.sleep(15)

final_resp = ser.read(ser.in_waiting or 1000).decode('utf-8', errors='ignore')
print(f"Response: {final_resp}")

if "+CMGS" in final_resp or "OK" in final_resp:
    print("\n✓✓✓ SMS SENT SUCCESSFULLY! ✓✓✓")
else:
    print("\n✗ SMS send failed")
    
    # Try alternative method without quotes
    print("\nTrying alternative format...")
    ser.reset_input_buffer()
    ser.write(f'AT+CMGS={phone[1:]}\r'.encode())  # Remove + sign
    time.sleep(3)
    ser.write(message.encode())
    ser.write(b'\x1A')
    time.sleep(10)
    alt_resp = ser.read(ser.in_waiting or 1000).decode('utf-8', errors='ignore')
    print(f"Alternative response: {alt_resp}")

ser.close()
print("\nTest complete!")
