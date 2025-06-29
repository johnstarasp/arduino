import serial
import time

# Replace with the correct serial port for your setup
SERIAL_PORT = '/dev/serial0'  # or '/dev/serial0'
BAUD_RATE = 115200
PHONE_NUMBER = '+6980531698'  # Replace with the destination number
MESSAGE = b'Hello from Raspberry Pi and SIM7070G!'

def send_sms():
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        def send_cmd(cmd, delay=1):
            ser.write((cmd + '\r\n').encode())
            time.sleep(delay)
            print(ser.read_all().decode(errors='ignore'))

        send_cmd('AT')                       # Check module is responding
        send_cmd('AT+CREG?')

        send_cmd('AT+CMGF=1')                # Set SMS mode to text
        send_cmd(f'AT+CMGS="{PHONE_NUMBER}"')
        time.sleep(1)
        ser.write(b'Hello from Raspberry Pi and SIM7070G!\x1A')  # \x1A is Ctrl+Z to send the message
        time.sleep(3)
        print(ser.read_all().decode(errors='ignore'))

if __name__ == '__main__':
    send_sms()
