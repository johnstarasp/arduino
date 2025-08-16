#!/usr/bin/env python3
import serial
import time
import sys

class SIM7070G:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, timeout=10):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to SIM7070G on {self.port}")
            time.sleep(2)
            return True
        except serial.SerialException as e:
            print(f"Error connecting to SIM7070G: {e}")
            return False
            
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected from SIM7070G")
            
    def send_at_command(self, command, wait_time=2):
        if not self.ser or not self.ser.is_open:
            print("Serial connection not open")
            return None
            
        self.ser.write((command + '\r\n').encode())
        time.sleep(wait_time)
        
        response = ""
        while self.ser.in_waiting > 0:
            response += self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
            time.sleep(0.1)
            
        return response.strip()
        
    def check_connection(self):
        response = self.send_at_command("AT")
        return "OK" in response
        
    def check_signal_strength(self):
        response = self.send_at_command("AT+CSQ")
        print(f"Signal strength: {response}")
        return response
        
    def check_network_registration(self):
        response = self.send_at_command("AT+CREG?")
        print(f"Network registration: {response}")
        return response
        
    def set_sms_text_mode(self):
        response = self.send_at_command("AT+CMGF=1")
        return "OK" in response
        
    def send_sms(self, phone_number, message):
        if not self.check_connection():
            print("AT command test failed")
            return False
            
        if not self.set_sms_text_mode():
            print("Failed to set SMS text mode")
            return False
            
        self.check_signal_strength()
        self.check_network_registration()
        
        at_command = f'AT+CMGS="{phone_number}"'
        response = self.send_at_command(at_command, wait_time=1)
        
        if ">" not in response:
            print(f"Failed to initiate SMS send: {response}")
            return False
            
        self.ser.write((message + '\x1A').encode())
        time.sleep(5)
        
        response = ""
        start_time = time.time()
        while time.time() - start_time < 30:
            if self.ser.in_waiting > 0:
                response += self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
            time.sleep(0.1)
            if "OK" in response or "ERROR" in response:
                break
                
        print(f"SMS send response: {response}")
        return "OK" in response

def main():
    phone_number = "+306976518415"
    message = "Hello from Raspberry Pi with SIM7070G!"
    
    sim = SIM7070G()
    
    if not sim.connect():
        print("Failed to connect to SIM7070G")
        sys.exit(1)
        
    try:
        print(f"Sending SMS to {phone_number}")
        success = sim.send_sms(phone_number, message)
        
        if success:
            print("SMS sent successfully!")
        else:
            print("Failed to send SMS")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sim.disconnect()

if __name__ == "__main__":
    main()