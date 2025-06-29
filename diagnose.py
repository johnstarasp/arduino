import serial
import time

# Use UART port (adjust if needed)
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)

def send_at(cmd, delay=3):
    """Send AT command and return list of response lines."""
    print(f">>> {cmd}")
    ser.write((cmd + "\r\n").encode())
    time.sleep(delay)

    # lines = []
    # while ser.in_waiting:
    #     line = ser.readline().decode(errors='ignore').strip()
    #     if line:
    #         print(line)
    #         lines.append(line)
    # return lines

def check_module():
    response = send_at('AT')
    return "OK" in response

def check_sim():
    response = send_at('AT+CPIN?')
    return any("READY" in line for line in response)

def check_signal():
    response = send_at('AT+CSQ')
    for line in response:
        if "+CSQ:" in line:
            parts = line.split(":")[1].split(",")
            rssi = int(parts[0].strip())
            print(f"📶 Signal strength: RSSI={rssi}")
            return rssi != 99
    return False

def check_network():
    for _ in range(10):  # retry up to 10 times
        response = send_at('AT+CREG?', delay=2)
        for line in response:
            if "+CREG:" in line and (",1" in line or ",5" in line):
                print("✅ Network registered.")
                return True
        print("⏳ Waiting for network...")
        time.sleep(3)
    print("❌ Network registration failed.")
    return False

def check_operator():
    response = send_at('AT+COPS?')
    return any("+COPS:" in line for line in response)

def configure_sms():
    send_at('AT+CMGF=1')         # Text mode
    send_at('AT+CSCS="GSM"')     # GSM charset

def send_test_sms(number, message="SIM test OK"):
    send_at(f'AT+CMGS="{number}"')
    time.sleep(1)
    ser.write((message + "\x1A").encode())  # Ctrl+Z
    print("📨 Sending SMS...")
    time.sleep(5)

# ---- Main Diagnostic Flow ----
print("🔍 Running SIM7070G diagnostics...\n")

send_at('AT')
# send_at('AT+CSQ')  # Check signal strength
# send_at('AT+CREG?')  # Check network registration
  # Check SIM card statu
# send_at('AT+CNMP=13')
# send_at('AT+CMNB=2')
# send_at('AT+CFUN=1')
send_at('AT+CSQ')  # Check signal strength
send_at('AT+CREG?')

# send_at('AT+CPIN?')  # Check SIM card status
# send_at('AT+CFUN=1')  # Set full functionality
# send_at('AT+CMNB?')  
# send_at('AT+CNMP?')  # Enable network registration notifications
# send_at('AT+COPS?')
# send_at('AT+CMGF=1')         # Text mode
# send_at('AT+CSCS="GSM"')     # GSM charset
# send_at('AT+CSQ')  # Check signal strength
# send_at('AT+CREG?') 
# send_at('AT+COPS=0')  # Check SIM card status
# send_at('AT+CREG?') 
# send_at('AT+CGDCONT=1,"IP","internet"') 
# send_at('AT+CREG?') 

print("\n✅ All checks passed. Ready to send SMS.")
ser.close()
