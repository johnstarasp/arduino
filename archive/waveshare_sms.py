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
        
    def print_cms_error_meaning(self, error_code):
        """Print CMS error code meaning"""
        cms_errors = {
            "300": "ME failure",
            "301": "SMS service of ME reserved",
            "302": "Operation not allowed",
            "303": "Operation not supported",
            "304": "Invalid PDU mode parameter",
            "305": "Invalid text mode parameter",
            "310": "SIM not inserted",
            "311": "SIM PIN required",
            "312": "PH-SIM PIN required",
            "313": "SIM failure",
            "314": "SIM busy",
            "315": "SIM wrong",
            "316": "SIM PUK required",
            "317": "SIM PIN2 required",
            "318": "SIM PUK2 required",
            "320": "Memory failure",
            "321": "Invalid memory index",
            "322": "Memory full",
            "330": "SMSC address unknown",
            "331": "No network service",
            "332": "Network timeout",
            "500": "Unknown error",
            "512": "SIM not ready",
            "513": "Message length exceeds",
            "514": "Invalid request parameters",
            "515": "ME storage failure",
            "517": "Invalid service mode",
            "528": "More message to send state error",
            "529": "MO SMS is not allow",
            "530": "GPRS is suspended",
            "531": "ME storage full"
        }
        
        if error_code in cms_errors:
            print(f"Error meaning: {cms_errors[error_code]}")
        else:
            print(f"Unknown CMS error code: {error_code}")
            
    def send_sms_alternative(self, phone_number, message):
        """Alternative SMS sending method without international format"""
        print(f"\nTrying alternative SMS method with number: {phone_number}")
        
        # Clear buffer
        self.ser.reset_input_buffer()
        time.sleep(0.5)
        
        # Try sending without quotes or with different format
        cmd = f'AT+CMGS={phone_number}\r'
        print(f"Sending command: {cmd.strip()}")
        
        self.ser.write(cmd.encode('utf-8'))
        
        # Wait for prompt
        response = ""
        start_time = time.time()
        
        while time.time() - start_time < 5:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                
                if '>' in response:
                    print("✓ Got SMS prompt (alternative method)")
                    # Send message
                    time.sleep(0.5)
                    self.ser.write(message.encode('utf-8'))
                    time.sleep(0.1)
                    self.ser.write(b'\x1A')
                    
                    # Wait for confirmation
                    conf_response = ""
                    conf_start = time.time()
                    while time.time() - conf_start < 30:
                        if self.ser.in_waiting > 0:
                            data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                            conf_response += data
                            print(f"Response: {data.strip()}")
                            
                        if "+CMGS:" in conf_response and "OK" in conf_response:
                            print("✓ SMS sent successfully (alternative method)!")
                            return True
                        elif "ERROR" in conf_response:
                            print(f"✗ SMS send failed: {conf_response}")
                            return False
                        time.sleep(0.5)
                    return False
                    
            if "ERROR" in response:
                print(f"Alternative method failed: {response}")
                return False
                
            time.sleep(0.1)
        
        print("Alternative method timeout")
        return False
        
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
        
        # Check for interference from other processes
        if self.ser.in_waiting > 100:
            print("WARNING: Detected buffered data - another process may be using the serial port")
            print("Consider stopping other serial applications (picocom, minicom, etc.)")
            self.ser.reset_input_buffer()
            time.sleep(1)
        
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

        # Set SMS text mode (1 = text mode, 0 = PDU mode)
        response = self.send_at_command("AT+CMGF=1")
        if "OK" not in response:
            print(f"Failed to set SMS text mode: {response}")
            return False
        print("✓ SMS text mode enabled")
        
        # Enable error reporting
        response = self.send_at_command("AT+CMEE=2")
        print(f"Error reporting: {response}")
        

        
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
        
        # CRITICAL: Set text mode right before sending SMS
        # The module seems to lose this setting
        print("Setting SMS text mode immediately before sending...")
        response = self.send_at_command("AT+CMGF=1", wait_time=1)
        if "OK" not in response:
            print(f"Failed to set text mode: {response}")
            return False
        print("✓ Text mode set")
        
        # Small delay to ensure mode is set
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
        empty_response_count = 0
        
        while time.time() - start_time < 5:  # 5 second timeout for prompt
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                
                # Check for the prompt character
                if '>' in response:
                    prompt_found = True
                    print("\n✓ Got SMS prompt")
                    break
                    
            # Check for errors
            if "CMS ERROR" in response or "CME ERROR" in response or "+CMS ERROR" in response:
                print(f"\nError received: {response}")
                # Parse error code if available
                if "CMS ERROR:" in response:
                    try:
                        error_code = response.split("CMS ERROR:")[1].strip().split()[0]
                        print(f"CMS Error Code: {error_code}")
                        self.print_cms_error_meaning(error_code)
                    except:
                        pass
                return False
            
            # If we've waited a bit and still have empty response, assume we're at prompt
            if time.time() - start_time > 2 and not response:
                empty_response_count += 1
                if empty_response_count > 5:  # After several checks with no response
                    print("\nNo response detected - assuming module is waiting at prompt")
                    prompt_found = True
                    break
                
            time.sleep(0.1)  # Small delay to prevent CPU spinning
        
        if not prompt_found:
            print(f"\nFailed to get SMS prompt. Response: '{response}'")
            # If response is completely empty after timeout, try sending message anyway
            if not response:
                print("Empty response - attempting to send message anyway...")
                prompt_found = True  # Force continuation
            else:
                # Try alternative approach - send without international format
                if phone_number.startswith("+"):
                    alt_number = phone_number[1:]  # Remove the +
                    print(f"Trying alternative number format: {alt_number}")
                    return self.send_sms_alternative(alt_number, message)
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
    phone_number = "00306976518415"
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