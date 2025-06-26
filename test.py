import serial
import time

# Use serial0 (which maps to ttyAMA0 or ttyS0)
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

def send_at(command, delay=1):
    ser.write((command + '\r\n').encode())
    time.sleep(delay)
    while ser.in_waiting:
        print(ser.readline().decode(errors='ignore').strip())

# Configure for SMS
send_at('AT')  # Basic check
send_at('AT+CMGF=1')  # Set SMS to text mode
send_at('AT+CSCS="GSM"')  # Use GSM character set
send_at('AT+CMGS="+6980531698"')  # Replace with real number
time.sleep(1)
ser.write(b"Magnet triggered!\x1A")  # Ctrl+Z to send
time.sleep(5)
