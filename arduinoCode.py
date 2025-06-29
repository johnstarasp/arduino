import serial
import time

# Open UART connection (use GPIO UART: /dev/serial0)
sim7070 = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

def send_command(cmd, timeout=5):
    """Send AT command and wait for full response (any kind)."""
    print(f">>> {cmd}")
    sim7070.write((cmd + '\r\n').encode())

    response = []
    start_time = time.time()
    time.sleep(0.2)  # small delay to start getting data

    while time.time() - start_time < timeout:
        while sim7070.in_waiting:
            line = sim7070.readline().decode(errors='ignore').strip()
            if line:
                print(line)
                response.append(line)

        # Break if we got any response (optional) — comment this if you want full timeout always
        if response:
            break

        time.sleep(0.1)

    return response

def wait_for_network(timeout=30):
    """Wait for network registration with AT+CREG?"""
    print("⏳ Waiting for network registration...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        response = send_command("AT+CREG?")
        if any("+CREG: 0,1" in r or "+CREG: 0,5" in r for r in response):
            print("✅ Registered to network.")
            return True
        print("📡 Still searching...")
        time.sleep(2)

    print("❌ Failed to register to network.")
    return False

# ---------- MAIN ----------
print("📟 Initializing SIM7070G...")
time.sleep(2)

send_command("AT")
send_command("AT+CFUN=1")
send_command("AT+CPIN?")
send_command("AT+CNMP=38")                 # LTE only (optional)
send_command("AT+COPS=0")                  # Auto network selection
send_command('AT+CBANDCFG="LTE",3,20')     # Set LTE bands (optional)
send_command("AT+CSQ")                     # Signal strength
send_command("AT+CMGF=1")                  # SMS text mode

# Wait for network
if not wait_for_network(timeout=30):
    sim7070.close()
    exit(1)

# Send SMS
recipient = "+306980531698"               # Replace with real number
send_command(f'AT+CMGS="{recipient}"')

# Wait for '>' prompt to send SMS body
start = time.time()
while time.time() - start < 5:
    if sim7070.in_waiting:
        char = sim7070.read().decode(errors='ignore')
        print(char, end="")
        if '>' in char:
            break
    time.sleep(0.1)

sim7070.write(b"Hello from SIM7070G!\x1A")  # Message + Ctrl+Z
print("\n📨 SMS Sent!")

# Wait for confirmation
time.sleep(5)
while sim7070.in_waiting:
    print(sim7070.readline().decode(errors='ignore').strip())

sim7070.close()
