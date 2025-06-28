import serial
import time

SERIAL_PORT = "/dev/serial0"  # Change if needed (e.g., /dev/ttyS0 for UART)
BAUDRATE = 115200
PHONE_NUMBER = "+6980531698"  # ← Replace with your actual phone number
MESSAGE = "Hello from SIM7070G on Raspberry Pi!"

# Initialize serial
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
time.sleep(1)

def send_at(cmd, expected=None, timeout=3):
    ser.write((cmd + "\r\n").encode())
    time.sleep(0.5)
    end_time = time.time() + timeout
    response = ""
    while time.time() < end_time:
        if ser.in_waiting:
            response += ser.read(ser.in_waiting)
        if expected and expected.encode() in response:
            break
    print(f">>> {cmd}")
    print(response.decode(errors='ignore'))
    return response.decode(errors='ignore')

# === 1. Basic modem init ===
send_at("AT", "OK")
send_at("ATE0", "OK")           # Disable echo
send_at("AT+CMEE=2", "OK")      # Verbose error messages
send_at("AT+CPIN?", "READY")    # SIM check

# === 2. Set full functionality and auto network selection ===
send_at("AT+CFUN=1", "OK")      # Full functionality
send_at("AT+COPS=0", "OK")      # Auto operator selection

# === 3. Wait for network registration ===
def wait_network(timeout=120):
    print("⏳ Waiting for network...")
    start = time.time()
    resp = ""
    while time.time() - start < timeout:
        resp += send_at("AT+CREG?", "+CREG", timeout=2)
        if "+CREG: 0,1" in resp or "+CREG: 0,5" in resp:
            print("✅ Network registered.")
            return True
        time.sleep(3)
    print("❌ Network registration timeout.")
    return False

if not wait_network():
    ser.close()
    raise SystemExit("Exiting: Network not available.")

# === 4. Send SMS ===
send_at("AT+CMGF=1", "OK")  # Set SMS text mode
resp = send_at(f'AT+CMGS="{PHONE_NUMBER}"', ">", timeout=5)
if ">" in resp:
    ser.write((MESSAGE + "\x1A").encode())  # Ctrl+Z to send
    print("📨 Sending SMS...")
    time.sleep(5)
else:
    print("❌ Failed to enter SMS input mode.")

# Close port
ser.close()
