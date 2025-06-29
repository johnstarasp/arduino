import serial
import time

# === CONFIGURATION ===
SERIAL_PORT = "/dev/serial0"        # Change if using UART (e.g. /dev/ttyS0)
BAUDRATE = 115200
PHONE_NUMBER = "+6980531698"        # <-- Replace with real number (international format)
SMS_TEXT = "Hello from SIM7070G on Raspberry Pi!"


# === Open serial port ===
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
time.sleep(1)

# === Function to send AT command and read response ===
def send_at(command, expected=None, timeout=3):
    ser.write((command + "\r\n").encode())
    time.sleep(0.5)
    # end_time = time.time() + timeout
    # response = ""
    # while time.time() < end_time:
    #     if ser.in_waiting:
    #         response += ser.read(ser.in_waiting).decode(errors="ignore")
    #         if expected and expected in response:
    #             break
    # print(f">>> {command}")
    # print(response.strip())
    # return response.strip()

# === Wait for network registration ===
def wait_for_network(timeout=120):
    print("⏳ Waiting for network registration...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        send_at("AT+CREG?", "+CREG", timeout=2)
    #     if "+CREG: 0,1" in resp or "+CREG: 0,5" in resp:
    #         print("✅ Network registered!")
    #         return True
    #     time.sleep(3)
    # print("❌ Network registration failed.")
    return True


# === STEP 1: Modem Initialization ===
send_at("AT", "OK")
send_at("ATE0", "OK")            # Disable echo
send_at("AT+CMEE=2", "OK")       # Verbose error messages
send_at("AT+CPIN?", "READY")     # Check SIM card
send_at("AT+CFUN=1", "OK")       # Full functionality
send_at("AT+COPS=0", "OK")       # Auto operator selection

# === STEP 2: Wait for Network ===
# if not wait_for_network():
#     ser.close()
#     raise SystemExit("❌ Could not register on network. Exiting.")

# === STEP 3: Send SMS ===
send_at("AT+CMGF=1", "OK")       # Text mode
send_at(f'AT+CMGS="{PHONE_NUMBER}"', ">", timeout=5)
send_at("AT+CREG?", "+CREG", timeout=2)
# if ">" in response:
#     ser.write((SMS_TEXT + "\x1A").encode())  # Send message with Ctrl+Z
#     print("📨 Sending SMS...")
#     time.sleep(5)
# else:
#     print("❌ Failed to get SMS prompt (no '>')")
ser.write((SMS_TEXT + "\x1A").encode()) 
# === Done ===
ser.close()
print("✅ Done. SMS should be sent.")
