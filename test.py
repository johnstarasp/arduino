import serial
import time

# Use UART interface (connected via GPIO)
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

def send_at(command, delay=1, read_all=True):
    """Send AT command and return the response."""
    print(f">>> {command}")
    ser.write((command + '\r\n').encode())
    time.sleep(delay)

    response = []
    while ser.in_waiting:
        line = ser.readline().decode(errors='ignore').strip()
        if line:
            print(line)
            response.append(line)
    return response if read_all else response[-1] if response else ""

def wait_for_network(timeout=60):
    """Wait until SIM7070G is registered on the network."""
    print("Waiting for network registration...")
    start = time.time()
    while time.time() - start < timeout:
        response = send_at('AT+CREG?', delay=2)
        for line in response:
            if '+CREG:' in line and (',1' in line or ',5' in line):
                print("✅ Network registered.")
                return True
        print("⏳ Not registered, retrying...")
        time.sleep(3)
    print("❌ Network registration timeout.")
    return False

# Start communication and wait for registration
send_at('AT')  # Basic check
send_at('AT+CREG?') 
send_at('AT+CFUN=1') 

if not wait_for_network():
    ser.close()
    exit(1)

# Configure SMS
send_at('AT+CMGF=1')            # Text mode
send_at('AT+CSCS="GSM"')        # GSM charset

# Send SMS
recipient = "+6980531698"       # Replace with real phone number
send_at(f'AT+CMGS="{recipient}"')
time.sleep(1)
ser.write(b"Magnet triggered!\x1A")  # Message + Ctrl+Z
print("📨 Message sent, waiting for confirmation...")
time.sleep(5)

ser.close()
