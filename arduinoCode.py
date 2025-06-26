import serial
import time

# Open UART connection (use GPIO UART: /dev/serial0)
sim7070 = serial.Serial('/dev/serial0', baudrate=19200, timeout=1)

def send_command(cmd, delay=1.0):
    """Send an AT command and print the response."""
    print(f">>> {cmd}")
    sim7070.write((cmd + '\r\n').encode())
    time.sleep(delay)

    response = []
    while sim7070.in_waiting:
        line = sim7070.readline().decode(errors='ignore').strip()
        if line:
            print(line)
            response.append(line)
    return response

def wait_for_network(timeout=30):
    """Wait for network registration with AT+CREG?"""
    print("⏳ Waiting for network registration...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        send_command("AT+CREG?", delay=2)
        time.sleep(1)

        # Read response manually
        response = []
        while sim7070.in_waiting:
            line = sim7070.readline().decode(errors='ignore').strip()
            if line:
                print(line)
                response.append(line)

        if any("+CREG: 0,1" in r or "+CREG: 0,5" in r for r in response):
            print("✅ Registered to network.")
            return True

    print("❌ Failed to register to network.")
    return False

# ---------- MAIN ----------
print("Initializing SIM7070G...")
time.sleep(2)

send_command("AT")
send_command("AT+CREG?")
send_command("AT+CFUN=1")
# send_command("AT+CNMP=38")    # LTE only (optional)
# send_command("AT+COPS=0")     # Auto operator selection (optional)
# send_command("AT+CBANDCFG='LTE',3,20")  # Band config (optional)
# send_command("AT+CSQ")        # Check signal quality (optional)

send_command("AT+CMGF=1")       # SMS text mode

# Optional: wait for network registration
wait_for_network(timeout=30)

# Send SMS
recipient = "+306980531698"  # Replace with your number
send_command(f'AT+CMGS="{recipient}"')
time.sleep(1)
sim7070.write(b"Hello from SIM7070G!\x1A")  # Message + Ctrl+Z
print("📨 SMS Sent!")

# Optionally read more responses after sending
time.sleep(5)
while sim7070.in_waiting:
    print(sim7070.readline().decode(errors='ignore').strip())
