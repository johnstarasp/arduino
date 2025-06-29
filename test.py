import serial
import time

PORT = '/dev/serial0'
BAUD = 115200
PHONE = '+306946192873'
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
        at('AT+CPIN?')
        at('AT+CSQ')
        at('AT+CREG?')
        at('AT+CSCA?')         # Check SMS center number
        at('AT+CMGF=1')        # Set SMS text mode
        at(f'AT+CMGS="{PHONE}"', wait=2)
        ser.write((MESSAGE + '\x1A').encode())
        time.sleep(5)
        resp = ser.read_all().decode(errors='ignore')
        print(resp)

if __name__ == '__main__':
    send_sms()

