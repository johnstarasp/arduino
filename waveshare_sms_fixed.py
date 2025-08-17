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
        
        # Set character set to GSM
        response = self.send_at_command("AT+CSCS=\"GSM\"")
        if "OK" not in response:
            print(f"Warning: Failed to set character set: {response}")
        else:
            print("✓ Character set configured")
        
        # Check SMS service center
        response = self.send_at_command("AT+CSCA?")
        print(f"SMS service center: {response}")
        
    def send_sms(self, phone_number, message):
        """Send SMS message using manual control for better debugging"""
        print(f"Sending SMS to {phone_number}: '{message}'")
        
        # Clear any pending data first
        self.ser.reset_input_buffer()
        time.sleep(0.5)
        
        # Send AT+CMGS command
        cmd = f'AT+CMGS="{phone_number}"\r'
        print(f"Sending command: {cmd.strip()}")
        self.ser.write(cmd.encode('utf-8'))
        
        # Wait for the > prompt
        response = ""
        start_time = time.time()
        got_prompt = False
        
        while time.time() - start_time < 5:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += data
                print(f"Response chunk: {repr(data)}")
                
                if ">" in data:
                    got_prompt = True
                    break
                elif "ERROR" in data:
                    print(f"SMS command error: {response}")
                    return False
            time.sleep(0.1)
        
        if not got_prompt:
            print(f"Failed to get SMS prompt. Full response: {repr(response)}")
            # Try to cancel the command
            self.ser.write(b'\x1B')  # ESC character
            time.sleep(1)
            return False
            
        print("✓ Got SMS prompt, sending message...")
        
        # Send the message text followed by Ctrl+Z
        msg_with_terminator = message + '\x1A'
        self.ser.write(msg_with_terminator.encode('utf-8'))
        print(f"Sent message with terminator (Ctrl+Z)")
        
        # Wait for confirmation with longer timeout
        response = ""
        start_time = time.time()
        
        while time.time() - start_time < 60:  # Increased timeout to 60 seconds
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += data
                print(f"SMS Response chunk: {repr(data)}")
                
                # Check for success
                if "+CMGS:" in response:
                    if "OK" in response:
                        print("✓ SMS sent successfully!")
                        # Extract message reference number if available
                        if "+CMGS:" in response:
                            try:
                                ref_num = response.split("+CMGS:")[1].split("\n")[0].strip()
                                print(f"Message reference: {ref_num}")
                            except:
                                pass
                        return True
                    
                # Check for errors
                if "ERROR" in response or "+CMS ERROR" in response:
                    print(f"✗ SMS send failed with error: {response}")
                    # Parse CMS error if present
                    if "+CMS ERROR:" in response:
                        try:
                            error_code = response.split("+CMS ERROR:")[1].split("\n")[0].strip()
                            print(f"CMS Error code: {error_code}")
                            # Common CMS error codes
                            error_meanings = {
                                "304": "Invalid PDU mode parameter",
                                "305": "Invalid text mode parameter",
                                "330": "SMSC address unknown",
                                "500": "Unknown error",
                                "513": "Unable to store",
                                "514": "Invalid status",
                                "515": "Device busy"
                            }
                            if error_code in error_meanings:
                                print(f"Error meaning: {error_meanings[error_code]}")
                        except:
                            pass
                    return False
                    
            time.sleep(0.5)
            
        print(f"✗ SMS send timeout after 60 seconds")
        print(f"Final response: {repr(response)}")
        return False

def main():
    """Main function"""
    phone_number = "+306976518415"
    message = "Test SMS from Pi"  # Shorter message for testing
    
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