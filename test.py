import serial
import time

# Set your serial port here
SERIAL_PORT = "/dev/serial0"  # Or /dev/ttyUSB0 depending on connection
BAUDRATE = 115200           # Default for SIM7070G

# Your target phone number
PHONE_NUMBER = "+6980531698"  # Replace with your phone number
MESSAGE = "Hello from Raspberry Pi and SIM7070G!"

def send_at(command, expected_response, timeout=3):
    """Send AT command and wait for the expected response."""
    ser.write((command + '\r\n').encode())
    time.sleep(0.5)
    deadline = time.time() + timeout
    response = b""
    while time.time() < deadline:
        if ser.in_waiting:
            response += ser.read(ser.in_waiting)
        if expected_response.encode() in response:
            print("✅ " + response.decode(errors='ignore'))
            return True
    print("❌ Timeout or unexpected response:\n" + response.decode(errors='ignore'))
    return False

# Open serial connection
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
time.sleep(1)

# Initialize modem
send_at("AT", "OK")
send_at("CREG?", "0,1")  # Check if modem is ready
#send_at("ATE0", "OK")  # Echo off (optional)
send_at("AT+CMGF=1", "OK")  # Set SMS text mode

# Send the SMS
send_at(f'AT+CMGS="{PHONE_NUMBER}"', ">")  # Wait for > prompt
ser.write((MESSAGE + "\x1A").encode())  # Ctrl+Z to send
time.sleep(3)

# Close the serial connection
ser.close()
