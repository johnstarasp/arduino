#!/usr/bin/env python3
"""
Final SMS attempt - comprehensive test with extended timeouts
"""
import serial
import time
import os
import sys

print("=== FINAL SIM7070G SMS TEST ===")
print("Timestamp:", time.strftime("%Y-%m-%d %H:%M:%S"))

# Power control with verification
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(4, GPIO.OUT)
    
    print("\n1. Power Control Sequence")
    print("   Ensuring module is OFF...")
    GPIO.output(4, GPIO.LOW)
    time.sleep(5)
    
    print("   Powering ON (3-second pulse)...")
    GPIO.output(4, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(4, GPIO.LOW)
    
    print("   Waiting 20 seconds for module boot...")
    for i in range(20):
        print(f"   Boot wait: {i+1}/20 seconds", end='\r')
        time.sleep(1)
    print("\n   Power sequence complete")
    
except Exception as e:
    print(f"   GPIO Error: {e}")
    print("   Continuing without power control...")

# Serial port discovery
print("\n2. Serial Port Discovery")
test_ports = [
    # ('/dev/ttyS0', [115200, 57600, 9600]),
    ('/dev/serial0', [57600]),
    # ('/dev/ttyAMA0', [115200, 57600]),
]

module_found = False
working_serial = None

for port, bauds in test_ports:
    if not os.path.exists(port):
        print(f"   {port}: Not found")
        continue
    
    for baud in bauds:
        print(f"   Testing {port} @ {baud} baud...")
        try:
            ser = serial.Serial(port, baud, timeout=5)
            time.sleep(2)
            
            # Send AT command multiple times
            for attempt in range(5):
                ser.reset_input_buffer()
                ser.write(b'AT\r\n')
                time.sleep(2)
                
                response = ser.read(ser.in_waiting or 150)
                
                if response:
                    print(f"      Attempt {attempt+1}: {response}")
                    
                    if b'OK' in response or b'AT' in response or b'SIM7070G' in response:
                        print(f"   ✓ Module found at {port} @ {baud}!")
                        working_serial = ser
                        module_found = True
                        break
                else:
                    print(f"      Attempt {attempt+1}: No response")
            
            if module_found:
                break
            else:
                ser.close()
                
        except Exception as e:
            print(f"      Error: {e}")
    
    if module_found:
        break

if not module_found:
    print("\n❌ MODULE NOT RESPONDING")
    print("Troubleshooting steps:")
    print("1. Check physical connections")
    print("2. Verify SIM card is inserted")
    print("3. Check antenna connection") 
    print("4. Manually press power button on module")
    print("5. Check power supply (5V)")
    sys.exit(1)

# Module initialization
print(f"\n3. Module Initialization")
ser = working_serial

# Basic commands
commands = [
    ("ATE0", "Disable echo", 1),
    ("AT+CGMM", "Get model", 2),
    ("ATI", "Module info", 2),
    ("AT+CPIN?", "Check SIM", 3),
    ("AT+CSQ", "Signal strength", 2),
    ("AT+COPS?", "Network operator", 3),
    ("AT+CREG?", "Network registration", 2),
]

for cmd, desc, wait in commands:
    print(f"   {desc}...")
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(wait)
    
    response = ser.read(ser.in_waiting or 200).decode('utf-8', errors='ignore')
    print(f"      {cmd}: {response.strip()}")

# SMS Test
print(f"\n4. SMS Test")
phone = "+306980531698" #306976518415 #306980531698
message = "SUCCESS! SMS from Raspberry Pi SIM7070G module working!"

print(f"   Recipient: {phone}")
print(f"   Message: {message}")

# Set text mode
print("   Setting SMS text mode...")
ser.reset_input_buffer()
ser.write(b"AT+CMGF=1\r\n")
time.sleep(2)
resp = ser.read(ser.in_waiting or 100)
print(f"   Text mode response: {resp}")

# Send SMS
print("   Sending SMS command...")
ser.reset_input_buffer()
ser.write(f'AT+CMGS="{phone}"\r'.encode())

# Wait for prompt with extended timeout
print("   Waiting for SMS prompt...")
prompt_found = False
for i in range(10):  # 10 second timeout
    time.sleep(1)
    if ser.in_waiting:
        prompt_resp = ser.read(ser.in_waiting)
        print(f"   Prompt response: {prompt_resp}")
        if b'>' in prompt_resp:
            prompt_found = True
            break

if prompt_found or True:  # Continue even without prompt
    print("   Sending message text...")
    ser.write(message.encode())
    time.sleep(1)
    ser.write(b'\x1A')  # Ctrl+Z
    
    print("   Waiting for SMS confirmation (30 seconds)...")
    final_response = b''
    for i in range(30):
        time.sleep(1)
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting)
            final_response += chunk
            print(f"   Response chunk: {chunk}")
    
    final_str = final_response.decode('utf-8', errors='ignore')
    print(f"\n   Final SMS response: {final_str}")
    
    if "+CMGS" in final_str or "OK" in final_str:
        print("\n🎉 SMS SENT SUCCESSFULLY! 🎉")
        print("Check your phone for the message!")
        success = True
    else:
        print("\n❌ SMS send failed")
        success = False
else:
    print("\n❌ No SMS prompt received")
    success = False

# Cleanup
ser.close()
try:
    GPIO.cleanup()
except:
    pass

print(f"\n=== TEST COMPLETE ===")
print(f"Result: {'SUCCESS' if success else 'FAILED'}")
print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if success:
    sys.exit(0)
else:
    sys.exit(1)