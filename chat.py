import serial
import time

# configure serial port (adjust if needed)
ser = serial.Serial(
    port="/dev/serial0",  # or /dev/ttyAMA0 depending on your Pi setup
    baudrate=57600,
    timeout=1
)

def send_cmd(cmd, wait=0.5):
    """Send AT command and return response"""
    ser.write((cmd + "\r\n").encode())
    time.sleep(wait)
    reply = ser.read_all().decode(errors="ignore")
    print(reply.strip())
    return reply

# init modem
send_cmd("AT")
send_cmd("AT+CMGF=1")  # set text mode
send_cmd('AT+CSCA?')   # check SMSC

# set recipient
send_cmd('AT+CMGS="+306976518415"')
time.sleep(0.5)

# send message text, then Ctrl+Z (ASCII 26)
ser.write(b"Hello from Raspberry Pi and SIM7070G!\x1A")
time.sleep(5)

# read final response
print(ser.read_all().decode(errors="ignore"))

ser.close()
