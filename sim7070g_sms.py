#!/usr/bin/env python3
import serial
import time
import sys

class SIM7070G:
    def __init__(self, port='/dev/serial0', baudrate=57600, timeout=10):
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
        
    def initialize_sms(self):
        print("Initializing SMS configuration...")
        
        # Set SMS text mode
        if not self.set_sms_text_mode():
            print("Failed to set SMS text mode")
            return False
            
        # Set SMS storage to SIM
        response = self.send_at_command("AT+CPMS=\"SM\",\"SM\",\"SM\"")
        print(f"SMS storage config: {response}")
        
        # Set SMS character set
        response = self.send_at_command("AT+CSCS=\"GSM\"")
        print(f"Character set: {response}")
        
        # Check SMS service center (should be auto-configured)
        response = self.send_at_command("AT+CSCA?")
        print(f"SMS service center: {response}")
        
        return True

    def send_sms(self, phone_number, message):
        if not self.check_connection():
            print("AT command test failed")
            return False
            
        # Clear any pending data
        while self.ser.in_waiting > 0:
            self.ser.read(self.ser.in_waiting)
            time.sleep(0.1)
            
        if not self.initialize_sms():
            print("Failed to initialize SMS")
            return False
            
        self.check_signal_strength()
        self.check_network_registration()
        
        # Clear buffer again
        while self.ser.in_waiting > 0:
            self.ser.read(self.ser.in_waiting)
            time.sleep(0.1)
        
        print(f"Sending AT+CMGS command...")
        at_command = f'AT+CMGS="{phone_number}"'
        self.ser.write((at_command + '\r\n').encode())
        
        # Wait for prompt with longer timeout
        response = ""
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.ser.in_waiting > 0:
                new_data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += new_data
                print(f"Received: '{new_data.strip()}'")
            time.sleep(0.2)
            if ">" in response:
                break
        
        print(f"Full response to CMGS: '{response.strip()}'")
        
        if ">" not in response:
            print(f"Failed to get SMS prompt. Response: '{response.strip()}'")
            return False
            
        print("Got SMS prompt, sending message...")
        self.ser.write((message + '\x1A').encode())
        time.sleep(1)  # Give module time to process
        
        # Wait for final response with extended timeout
        response = ""
        start_time = time.time()
        print("Waiting for SMS send confirmation...")
        
        while time.time() - start_time < 60:  # Extended to 60 seconds
            if self.ser.in_waiting > 0:
                new_data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += new_data
                print(f"SMS Response: '{new_data.strip()}'")
                
                # Check for success indicators
                if "+CMGS:" in response and "OK" in response:
                    print("SMS sent successfully!")
                    return True
                elif "ERROR" in response:
                    print("SMS send failed with ERROR")
                    return False
                    
            time.sleep(0.5)  # Longer polling interval
            
        print(f"Final SMS send response: '{response.strip()}'")
        
        # If we got a +CMGS response, consider it successful even without OK
        if "+CMGS:" in response:
            print("Got +CMGS response, SMS likely sent")
            return True
            
        print("SMS send timeout - no response received")
        return False

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