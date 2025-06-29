import serial
import time

PORT = '/dev/serial0'
BAUD = 115200
PHONE = '+306980531698'
MESSAGE = 'Hello from Raspberry Pi and SIM7070G!'

def send_sms():
    with serial.Serial(PORT, BAUD, timeout=2) as ser:
        def at(cmd, wait=1):
            ser.write((cmd + '\r\n').encode())
            time.sleep(wait)
            resp = ser.read_all().decode(errors='ignore')
            print(f'> {cmd}\n{resp}')
            return resp

        at('AT')
        at('AT+CSQ')
        at('AT+CREG?')
        at('AT+CFUN=1')
        at('AT+CMGF=1')        # Set SMS text mode
        at(f'AT+CMGS="{PHONE}"', wait=2)
        time.sleep(3)
        ser.write((MESSAGE + '\x1A').encode())
        time.sleep(5)
        resp = ser.read_all().decode(errors='ignore')
        print(resp)

if __name__ == '__main__':
    send_sms()

