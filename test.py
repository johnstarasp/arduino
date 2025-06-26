import serial
import time

# Serial setup (adjust device if using USB or UART)
ser = serial.Serial('/dev/ttyUSB2', baudrate=115200, timeout=1)

def send_at(command, delay=1):
    ser.write((command + '\r\n').encode())
    time.sleep(delay)
    while ser.in_waiting:
        print(ser.readline().decode(errors='ignore').strip())

# Configure for SMS
send_at('AT')  # Basic check
send_at('AT+CMGF=1')  # Set SMS to text mode
send_at('AT+CSCS="GSM"')  # Use GSM character set
send_at('AT+CMGS="+6980531698"')  # Replace with destination number
time.sleep(1)
ser.write(b"Magnet triggered!\x1A")  # Ctrl+Z to send
time.sleep(5)