#!/usr/bin/env python3
"""
Standalone SMS Sender for SIM7070G
Can be imported by other scripts or used independently
"""

import serial
import time

class SIM7070G_SMS:
    def __init__(self, port='/dev/serial0', baudrate=57600, phone_number=None):
        self.port = port
        self.baudrate = baudrate
        self.phone_number = phone_number
        self.ser = None
        
    def connect(self):
        """Connect to SIM7070G module"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=5)
            time.sleep(2)
            
            # Test connection
            self.ser.reset_input_buffer()
            self.ser.write(b'AT\r\n')
            time.sleep(2)
            
            response = self.ser.read(100)
            if b'OK' in response:
                print("✅ SIM7070G connected")
                return True
            else:
                print("❌ SIM7070G not responding")
                return False
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def configure_sms(self):
        """Configure SMS settings with fix for CMS ERROR 500"""
        try:
            # Set SMS service center (CRITICAL for new SIM cards)
            self.ser.write(b'AT+CSCA="+3097100000"\r\n')
            time.sleep(2)
            resp = self.ser.read(100)
            if b'OK' in resp:
                print("✅ SMS service center configured")
            
            # Configure SMS settings
            commands = [
                b"ATE0\r\n",                    # Disable echo
                b'AT+CMEE=2\r\n',             # Verbose errors
                b'AT+CMGF=1\r\n',             # Text mode
                b'AT+CPMS="SM","SM","SM"\r\n', # SIM storage
            ]
            
            for cmd in commands:
                self.ser.write(cmd)
                time.sleep(1)
                self.ser.read(200)
            
            print("✅ SMS configured")
            return True
            
        except Exception as e:
            print(f"❌ SMS configuration failed: {e}")
            return False
    
    def send_sms(self, phone_number=None, message=""):
        """Send SMS message"""
        recipient = phone_number or self.phone_number
        if not recipient:
            print("❌ No phone number specified")
            return False
        
        try:
            print(f"📱 Sending SMS to {recipient}: {message}")
            
            # Ensure text mode
            self.ser.reset_input_buffer()
            self.ser.write(b"AT+CMGF=1\r\n")
            time.sleep(2)
            self.ser.read(100)
            
            # Send SMS command
            self.ser.reset_input_buffer()
            self.ser.write(f'AT+CMGS="{recipient}"\r'.encode())
            
            # Wait for prompt
            time.sleep(3)
            prompt = self.ser.read(100)
            
            if b'>' in prompt:
                # Send message
                self.ser.write(message.encode())
                time.sleep(1)
                self.ser.write(b'\x1A')  # Ctrl+Z
                
                # Wait for confirmation
                time.sleep(15)
                response = self.ser.read(300).decode('utf-8', errors='ignore')
                
                if "+CMGS" in response:
                    print("✅ SMS sent successfully")
                    return True
                elif "CMS ERROR" in response:
                    error = response.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in response else "unknown"
                    print(f"❌ CMS ERROR {error}")
                    return False
                else:
                    print(f"❌ SMS failed: {response}")
                    return False
            else:
                print("❌ No SMS prompt received")
                return False
                
        except Exception as e:
            print(f"❌ SMS error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from module"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("📴 Disconnected")

def main():
    """Example usage"""
    # Configuration
    phone = "+306980531698"
    message = "Test SMS from SIM7070G SMS sender"
    
    # Create SMS sender
    sms = SIM7070G_SMS(phone_number=phone)
    
    try:
        if sms.connect():
            if sms.configure_sms():
                sms.send_sms(message=message)
    finally:
        sms.disconnect()

if __name__ == "__main__":
    main()