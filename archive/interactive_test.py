#!/usr/bin/env python3
import serial
import time
import sys
import threading

def read_serial(ser):
    """Continuously read from serial port"""
    while True:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            print(f"<< {data.decode('utf-8', errors='ignore')}", end='')
        time.sleep(0.1)

print("SIM7070G Interactive Test")
print("Trying to connect...")

# Try common configurations
for baud in [115200, 57600, 9600]:
    try:
        ser = serial.Serial('/dev/serial0', baud, timeout=1)
        print(f"Testing at {baud} baud...")
        
        ser.write(b'AT\r\n')
        time.sleep(1)
        
        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            if b'OK' in response or b'AT' in response:
                print(f"Connected at {baud} baud!")
                break
        ser.close()
    except:
        pass
else:
    print("Could not connect!")
    sys.exit(1)

# Start reader thread
reader = threading.Thread(target=read_serial, args=(ser,), daemon=True)
reader.start()

print("\nCommands to try:")
print("1. AT - Test connection")
print("2. AT+CPIN? - Check SIM")
print("3. AT+CSQ - Signal strength")
print("4. AT+CREG? - Network registration")
print("5. AT+CMGF=1 - Set text mode")
print("6. AT+CMGS=\"+306976518415\" - Start SMS")
print("7. [Type message then Ctrl+Z to send]")
print("\nType 'quit' to exit\n")

try:
    while True:
        cmd = input(">> ")
        if cmd.lower() == 'quit':
            break
        elif cmd == '7':
            ser.write(b'\x1A')
        else:
            ser.write((cmd + '\r\n').encode())
        time.sleep(0.5)
except KeyboardInterrupt:
    pass

ser.close()
print("Disconnected")
