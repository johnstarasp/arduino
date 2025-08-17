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
        
        # Set SMS text mode (1 = text mode, 0 = PDU mode)
        response = self.send_at_command("AT+CMGF=1")
        if "OK" not in response:
            print(f"Failed to set SMS text mode: {response}")
            return False
        print("✓ SMS text mode enabled")
        
        # Check SMS service center (optional but useful for debugging)
        response = self.send_at_command("AT+CSCA?")
        print(f"SMS Service Center: {response}")
        
        return True
        
    def send_sms(self, phone_number, message):
        """Send SMS message"""
        print(f"Sending SMS to {phone_number}: '{message}'")
        
        # Clear any pending data first
        self.ser.reset_input_buffer()
        time.sleep(0.5)
        
        # Send AT+CMGS command directly (don't use send_at_command for this)
        cmd = f'AT+CMGS="{phone_number}"\r'
        print(f"Sending command: {cmd.strip()}")
        
        # Send the command
        self.ser.write(cmd.encode('utf-8'))
        
        # Wait for the '>' prompt (module needs time to process)
        response = ""
        start_time = time.time()
        prompt_found = False
        
        while time.time() - start_time < 5:  # 5 second timeout for prompt
            if self.ser.in_waiting > 0:
                char = self.ser.read(1).decode('utf-8', errors='ignore')
                response += char
                print(f"Received: {repr(char)}", end="")
                
                # Check for the prompt character
                if char == '>' or response.endswith('> '):
                    prompt_found = True
                    print("\n✓ Got SMS prompt")
                    break
                    
            # Check for errors
            if "ERROR" in response or "CME ERROR" in response:
                print(f"\nError received: {response}")
                return False
                
            time.sleep(0.01)  # Small delay to prevent CPU spinning
        
        if not prompt_found:
            print(f"\nFailed to get SMS prompt. Response: '{response}'")
            return False
            
        # Small delay before sending message
        time.sleep(0.5)
        
        print("Sending message text...")
        # Send the message text followed by Ctrl+Z (0x1A)
        self.ser.write(message.encode('utf-8'))
        time.sleep(0.1)
        self.ser.write(b'\x1A')  # Ctrl+Z to send the message
        
        print("Waiting for send confirmation...")
        
        # Wait for confirmation
        response = ""
        start_time = time.time()
        while time.time() - start_time < 30:  # 30 second timeout
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += data
                print(f"Response: {data.strip()}")
                
            # Check for success - looking for +CMGS response followed by OK
            if "+CMGS:" in response:
                if "OK" in response:
                    print("✓ SMS sent successfully!")
                    # Extract message reference if available
                    if "+CMGS:" in response:
                        try:
                            ref = response.split("+CMGS:")[1].split("\n")[0].strip()
                            print(f"Message reference: {ref}")
                        except:
                            pass
                    return True
            elif "ERROR" in response or "CME ERROR" in response:
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