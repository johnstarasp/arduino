import serial
import time

# Open UART connection (use GPIO UART: /dev/serial0)
sim7070 = serial.Serial('/dev/serial0', baudrate=19200, timeout=1)

def send_command(cmd, delay=5.0):
    """Send an AT command and return response lines."""
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
    """Wait for network registration by checking AT+CREG? in a loop."""
    print("⏳ Waiting for network registration...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        send_command("AT+CREG?", delay=2)
        response = send_command("AT+CREG?", delay=2)
        if any("+CREG: 0,1" in r or "+CREG: 0,5" in r for r in response):
            print("✅ Registered to network.")
            return True
        print("📡 Still not registered, retrying...")
        time.sleep(2)

    print("❌ Failed to register to network.")
    return False

# ---------- MAIN ----------
print("📟 Initializing SIM7070G...")
time.sleep(2)

send_command("AT")
send_command("AT+CFUN=1")
send_command("AT+CNMP=38")
send_command("AT+COPS=0")
send_command("AT+CSQ")
send_command("AT+CPIN?")          # Check SIM status
send_command("AT+CMGF=1")         # SMS text mode

# Wait until network is registered
if not wait_for_network(timeout=30):
    sim7070.close()
    exit(1)

# Send SMS
recipient = "+306980531698"       # Replace with your number
send_command(f'AT+CMGS="{recipient}"')
time.sleep(1)
sim7070.write(b"Hello from SIM7070G!\x1A")  # Message + Ctrl+Z (ASCII 26)
print("📨 SMS Sent!")

# Read response
time.sleep(5)
while sim7070.in_waiting:
    print(sim7070.readline().decode(errors='ignore').strip())

sim7070.close()
