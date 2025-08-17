#!/usr/bin/env python3
"""
SIM7070G SMS Script for Waveshare SIM7070G Cat-M/NB-IoT/GPRS HAT
Based on Waveshare documentation and SIM7070G specifications
"""
import serial
import time
import sys

class WaveshareSIM7070G:
    def __init__(self, port='/dev/serial0', baudrate=57600, timeout=10):
        """
        Initialize SIM7070G module
        Waveshare default: 115200 baud, but module auto-detects from 9600-3686400
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        
    def connect(self):
        """Connect to the SIM7070G module"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to SIM7070G on {self.port} at {self.baudrate} baud")
            time.sleep(3)  # Allow module to stabilize
            return True
        except serial.SerialException as e:
            print(f"Error connecting: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the module"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected from SIM7070G")
            
    def send_at_command(self, command, wait_time=2, expected_response="OK"):
        """Send AT command and wait for response"""
        if not self.ser or not self.ser.is_open:
            return None
            
        # Clear input buffer
        self.ser.reset_input_buffer()
        
        # Send command
        self.ser.write((command + '\r\n').encode('utf-8'))
        time.sleep(wait_time)
        
        # Read response
        response = ""
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if self.ser.in_waiting > 0:
                response += self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
            time.sleep(0.1)
            if expected_response in response or "ERROR" in response:
                break
                
        return response.strip()
        
    def initialize_module(self):
        """Initialize SIM7070G module with proper sequence"""
        print("Initializing SIM7070G module...")
        
        # Basic AT test
        response = self.send_at_command("AT")
        if "OK" not in response:
            print(f"AT test failed: {response}")
            return False
        print("✓ AT command test passed")
        
        # Turn off echo
        response = self.send_at_command("ATE0")
        print("✓ Echo disabled")
        
        # Check module info
        response = self.send_at_command("ATI")
        print(f"✓ Module info: {response}")
        
        # Check SIM card status with retries
        print("Checking SIM card status...")
        for attempt in range(10):  # Try for 10 seconds
            response = self.send_at_command("AT+CPIN?", wait_time=2)
            print(f"SIM status attempt {attempt + 1}: {response}")
            
            if "READY" in response:
                print("✓ SIM card ready")
                break
            elif "+CPIN: SIM PIN" in response:
                print("SIM card requires PIN - please remove PIN lock")
                return False
            elif "+CPIN: SIM PUK" in response:
                print("SIM card is PUK locked")
                return False
            elif "ERROR" in response:
                print("SIM card error - check if SIM is properly inserted")
                return False
            
            time.sleep(1)
        else:
            print("SIM card not ready after 10 attempts")
            # Continue anyway - some modules work without CPIN response
            print("Continuing without SIM READY confirmation...")
        
        # Wait for network registration
        print("Waiting for network registration...")
        for attempt in range(30):  # 30 second timeout
            response = self.send_at_command("AT+CREG?")
            print(f"Network registration attempt {attempt + 1}: {response}")
            
            if "+CREG: 0,1" in response or "+CREG: 0,5" in response:
                print("✓ Network registered")
                break
            elif "+CREG: 0,2" in response:
                print("Searching for network...")
            elif "+CREG: 0,3" in response:
                print("Network registration denied")
            elif "+CREG: 0,0" in response:
                print("Network registration disabled")
                
            time.sleep(2)
        else:
            print("Network registration failed - continuing anyway...")
            # Don't return False, continue with SMS attempt
            
        # Check signal strength
        response = self.send_at_command("AT+CSQ")
        print(f"✓ Signal strength: {response}")
        
        return True
        
    def configure_sms(self):
        response = self.send_at_command("AT+CMGF=1")
        if "OK" not in response:
            print(f"Failed to set SMS text mode: {response}")
            return False
        print("✓ SMS text mode enabled")
        return True
        """Configure SMS settings for SIM7070G"""
        print("Configuring SMS settings...")
        
        # Enable error reporting
        response = self.send_at_command("AT+CMEE=2")
        print(f"Error reporting: {response}")
        
        # Set SMS text mode
        response = self.send_at_command("AT+CMGF=1")
        if "OK" not in response:
            print(f"Failed to set SMS text mode: {response}")
            return False
        print("✓ SMS text mode enabled")
        
        # Set character set to IRA (International Reference Alphabet)
        response = self.send_at_command("AT+CSCS=\"IRA\"")
        if "OK" not in response:
            # Try GSM if IRA fails
            response = self.send_at_command("AT+CSCS=\"GSM\"")
            if "OK" not in response:
                print(f"Failed to set character set: {response}")
                return False
        print("✓ Character set configured")
        
        # Set preferred message storage to SIM card
        response = self.send_at_command("AT+CPMS=\"SM\",\"SM\",\"SM\"")
        print(f"Message storage: {response}")
        
        # Check and configure SMS service center
        response = self.send_at_command("AT+CSCA?")
        print(f"SMS service center: {response}")
        
        # If no service center is set, try to set a Greek one
        if "+CSCA:" not in response or '""' in response:
            print("Setting SMS service center for Greek network...")
            # Common Greek SMS service centers
            response = self.send_at_command('AT+CSCA="+3097100000",145')
            print(f"SMS service center set: {response}")
        
        # Enable SMS notification
        response = self.send_at_command("AT+CNMI=1,1,0,0,0")
        print(f"SMS notification: {response}")
        
        return True
        
    def send_sms(self, phone_number, message):
        """Send SMS message"""
        print(f"Sending SMS to {phone_number}: '{message}'")
        
        # Clear any pending data first
        while self.ser.in_waiting > 0:
            old_data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"Clearing old data: {old_data.strip()}")
            time.sleep(0.1)
        
        # Initialize AT+CMGS command
        cmd = f'AT+CMGS="{phone_number}"'
        print(f"Sending command: {cmd}")
        
        # Use the send_at_command method instead of manual approach
        response = self.send_at_command(cmd, wait_time=5, expected_response=">")
        print(f"CMGS command response: '{response.strip()}'")
        
        if ">" not in response:
            print(f"Failed to get SMS prompt. Full response: '{response}'")
            
            # Check for specific error
            if "ERROR" in response:
                print("SMS command returned ERROR - check network and service center configuration")
            elif not response.strip():
                print("No response to SMS command - module may be busy or unresponsive")
            
            return False
            
        print("✓ Got SMS prompt, sending message...")
        
        # Send message followed by Ctrl+Z
        self.ser.write((message + '\x1A').encode('utf-8'))
        
        # Wait for confirmation
        response = ""
        start_time = time.time()
        while time.time() - start_time < 30:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += data
                print(f"SMS Response: {data.strip()}")
                
            # Check for success
            if "+CMGS:" in response and "OK" in response:
                print("✓ SMS sent successfully!")
                return True
            elif "ERROR" in response:
                print(f"✗ SMS send failed: {response}")
                return False
                
            time.sleep(0.5)
            
        print(f"✗ SMS send timeout: {response}")
        return False

def main():
    """Main function"""
    phone_number = "+306976518415"
    message = "Hello from Raspberry Pi with Waveshare SIM7070G HAT!"
    
    # Initialize module
    sim = WaveshareSIM7070G(port='/dev/serial0', baudrate=57600)
    
    if not sim.connect():
        print("Failed to connect to SIM7070G")
        sys.exit(1)
        
    try:
        # Initialize module
        if not sim.initialize_module():
            print("Module initialization failed")
            return
            
        # Configure SMS
        if not sim.configure_sms():
            print("SMS configuration failed")
            return
            
        # Send SMS
        success = sim.send_sms(phone_number, message)
        
        if success:
            print("\n🎉 SMS sent successfully!")
        else:
            print("\n❌ Failed to send SMS")
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sim.disconnect()

if __name__ == "__main__":
    main()