#!/usr/bin/env python3
"""
Targeted SMS test for SIM7070G
Using known working configuration: /dev/serial0 at 57600 baud
"""
import serial
import time
import sys

print("=== TARGETED SIM7070G SMS TEST ===")
print("Configuration: /dev/serial0 @ 57600 baud")

# Power control
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(4, GPIO.OUT)
    
    print("\nPower cycling module...")
    GPIO.output(4, GPIO.LOW)
    time.sleep(3)
    GPIO.output(4, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(4, GPIO.LOW)
    
    print("Waiting 15 seconds for boot...")
    time.sleep(15)
    print("Power sequence complete")
    
except Exception as e:
    print(f"GPIO error: {e}")

# Connect to module
print(f"\nConnecting to /dev/serial0 @ 57600 baud...")
try:
    ser = serial.Serial('/dev/serial0', 57600, timeout=5)
    time.sleep(2)
    print("Serial connection established")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)

# Test AT communication
print("\nTesting AT communication...")
for attempt in range(5):
    ser.reset_input_buffer()
    ser.write(b'AT\r\n')
    time.sleep(2)
    
    response = ser.read(ser.in_waiting or 100)
    print(f"AT attempt {attempt+1}: {response}")
    
    if b'OK' in response or b'AT' in response:
        print("✓ Module responding!")
        break
else:
    print("✗ Module not responding to AT commands")
    ser.close()
    sys.exit(1)

# Initialize module
print("\nInitializing module...")
commands = [
    ("ATE0", "Disable echo"),
    ("AT+CGMM", "Get model"),
    ("AT+CPIN?", "Check SIM"),
    ("AT+CSQ", "Signal strength"),
    ("AT+CREG?", "Network status"),
]

for cmd, desc in commands:
    print(f"{desc}...")
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(2)
    
    response = ser.read(ser.in_waiting or 200).decode('utf-8', errors='ignore')
    print(f"  {cmd}: {response.strip()}")

# Send SMS
print("\n=== SENDING SMS ===")
phone = "+306976518415"
message = "SUCCESS! SMS from Pi via SIM7070G at 57600 baud on /dev/serial0"

print(f"To: {phone}")
print(f"Message: {message}")

# Set text mode
print("\nSetting SMS text mode...")
ser.reset_input_buffer()
ser.write(b"AT+CMGF=1\r\n")
time.sleep(2)
resp = ser.read(ser.in_waiting or 100)
print(f"Text mode: {resp}")

# Send SMS command
print("\nSending SMS command...")
ser.reset_input_buffer()
ser.write(f'AT+CMGS="{phone}"\r'.encode())

# Wait for prompt
print("Waiting for SMS prompt...")
time.sleep(3)
prompt = ser.read(ser.in_waiting or 100)
print(f"Prompt response: {prompt}")

# Send message text
print("Sending message text...")
ser.write(message.encode())
time.sleep(1)
ser.write(b'\x1A')  # Ctrl+Z

# Wait for confirmation
print("Waiting for SMS confirmation...")
final_response = b''
for i in range(30):
    time.sleep(1)
    if ser.in_waiting:
        chunk = ser.read(ser.in_waiting)
        final_response += chunk
        print(f"Response: {chunk}")

final_str = final_response.decode('utf-8', errors='ignore')

if "+CMGS" in final_str or "OK" in final_str:
    print("\n🎉 SMS SENT SUCCESSFULLY! 🎉")
    print("Check your phone for the message!")
    success = True
else:
    print(f"\n❌ SMS failed. Full response: {final_str}")
    success = False

# Cleanup
ser.close()
try:
    GPIO.cleanup()
except:
    pass

print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
sys.exit(0 if success else 1)