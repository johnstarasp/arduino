import serial
import time

# Use UART interface
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

def send_at(command, delay=1):
    """Send AT command and print response."""
    print(f">>> {command}")
    ser.write((command + '\r\n').encode())
    time.sleep(delay)
    while ser.in_waiting:
        response = ser.readline().decode(errors='ignore').strip()
        if response:
            print(response)

# Initialize communication
send_at('AT')                  # Check modem is responsive
send_at('AT+CMGF=1')           # Set SMS to Text mode
send_at('AT+CSCS="GSM"')       # Use GSM character set
send_at('AT+CMGS="+6980531698"')  # Set recipient number (replace with real one)
time.sleep(1)

# Send message body and Ctrl+Z to send
ser.write(b"Magnet triggered!\x1A")  # \x1A is Ctrl+Z
print("Message sent, waiting for confirmation...")
time.sleep(5)

ser.close()
