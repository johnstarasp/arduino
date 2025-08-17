#!/usr/bin/env python3
"""
SIM7070G Voice Call Script for Waveshare SIM7070G Cat-M/NB-IoT/GPRS HAT
Handles voice calls including dialing, status monitoring, and hangup
"""
import serial
import time
import sys

class WaveshareSIM7070GCall:
    def __init__(self, port='/dev/serial0', baudrate=57600, timeout=10):
        """Initialize SIM7070G module for voice calls"""
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
        """Initialize SIM7070G module for voice calls"""
        print("Initializing SIM7070G module for voice calls...")
        
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
        
        # Check SIM card status
        print("Checking SIM card status...")
        for attempt in range(10):
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
            print("Continuing without SIM READY confirmation...")
        
        # Wait for network registration
        print("Waiting for network registration...")
        for attempt in range(30):
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
            
        # Check signal strength
        response = self.send_at_command("AT+CSQ")
        print(f"✓ Signal strength: {response}")
        
        return True
        
    def configure_audio(self):
        """Configure audio settings for voice calls"""
        print("Configuring audio settings...")
        
        # Set audio channel (0=main audio channel, 1=aux audio channel)
        response = self.send_at_command("AT+CHFA=0")
        print(f"Audio channel: {response}")
        
        # Set volume level (0-9)
        response = self.send_at_command("AT+CLVL=5")
        print(f"Volume level: {response}")
        
        # Enable calling line identification
        response = self.send_at_command("AT+CLIP=1")
        print(f"Caller ID enabled: {response}")
        
        # Set ring indication
        response = self.send_at_command("AT+CFGRI=1")
        print(f"Ring indication: {response}")
        
        return True
        
    def make_call(self, phone_number):
        """Make a voice call to the specified number"""
        print(f"\n📞 Dialing {phone_number}...")
        
        # Clear any pending data
        self.ser.reset_input_buffer()
        
        # Make the call using ATD command
        # The semicolon at the end indicates a voice call
        cmd = f"ATD{phone_number};"
        print(f"Sending command: {cmd}")
        
        response = self.send_at_command(cmd, wait_time=5)
        print(f"Call response: {response}")
        
        if "OK" in response:
            print("✓ Call initiated successfully")
            return True
        elif "NO CARRIER" in response:
            print("✗ Call failed - No carrier")
            return False
        elif "BUSY" in response:
            print("✗ Line is busy")
            return False
        elif "NO ANSWER" in response:
            print("✗ No answer")
            return False
        elif "ERROR" in response:
            print("✗ Call failed - Error")
            return False
        else:
            print(f"Unexpected response: {response}")
            return True  # Might still be connecting
            
    def check_call_status(self):
        """Check the current call status"""
        response = self.send_at_command("AT+CLCC")
        
        if "+CLCC:" in response:
            # Parse call status
            # Format: +CLCC: <id>,<dir>,<stat>,<mode>,<mpty>[,<number>,<type>[,<alpha>]]
            # stat: 0=active, 1=held, 2=dialing, 3=alerting, 4=incoming, 5=waiting
            if ",0," in response:
                status = "Active call"
            elif ",1," in response:
                status = "Call on hold"
            elif ",2," in response:
                status = "Dialing..."
            elif ",3," in response:
                status = "Ringing..."
            elif ",4," in response:
                status = "Incoming call"
            elif ",5," in response:
                status = "Call waiting"
            else:
                status = "Unknown status"
                
            print(f"Call status: {status}")
            print(f"Full status: {response}")
            return True
        elif "OK" in response:
            print("No active calls")
            return False
        else:
            print(f"Status check response: {response}")
            return False
            
    def answer_call(self):
        """Answer an incoming call"""
        print("Answering incoming call...")
        response = self.send_at_command("ATA")
        
        if "OK" in response:
            print("✓ Call answered")
            return True
        else:
            print(f"✗ Failed to answer: {response}")
            return False
            
    def hangup_call(self):
        """Hang up the current call"""
        print("Hanging up call...")
        response = self.send_at_command("ATH")
        
        if "OK" in response:
            print("✓ Call ended")
            return True
        else:
            print(f"✗ Failed to hang up: {response}")
            return False
            
    def monitor_call(self, duration=60):
        """Monitor call status for a specified duration"""
        print(f"\nMonitoring call for up to {duration} seconds...")
        print("Press Ctrl+C to end call\n")
        
        start_time = time.time()
        last_check = 0
        
        try:
            while time.time() - start_time < duration:
                # Check status every 5 seconds
                if time.time() - last_check > 5:
                    if not self.check_call_status():
                        print("Call has ended")
                        break
                    last_check = time.time()
                    
                # Check for any unsolicited messages
                if self.ser.in_waiting > 0:
                    msg = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    if msg.strip():
                        print(f"Module message: {msg.strip()}")
                        
                    # Check for call end indicators
                    if "NO CARRIER" in msg or "BUSY" in msg:
                        print("Call has ended")
                        break
                        
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nCall monitoring interrupted by user")
            
        return True
        
    def send_dtmf(self, digits):
        """Send DTMF tones during a call"""
        print(f"Sending DTMF tones: {digits}")
        
        for digit in digits:
            cmd = f"AT+VTS={digit}"
            response = self.send_at_command(cmd, wait_time=1)
            print(f"DTMF {digit}: {response}")
            time.sleep(0.5)  # Small delay between tones
            
        return True

def main():
    """Main function for voice calls"""
    # Configuration
    phone_number = "+306976518415"  # Change this to your target number
    call_duration = 30  # Maximum call duration in seconds
    
    # You can also use the number without + for some networks
    # phone_number = "306976518415"
    
    # Initialize module
    call = WaveshareSIM7070GCall(port='/dev/serial0', baudrate=57600)
    
    if not call.connect():
        print("Failed to connect to SIM7070G")
        sys.exit(1)
        
    try:
        # Initialize module
        if not call.initialize_module():
            print("Module initialization failed")
            return
            
        # Configure audio
        if not call.configure_audio():
            print("Audio configuration failed")
            
        # Make the call
        if call.make_call(phone_number):
            # Monitor the call
            call.monitor_call(duration=call_duration)
            
            # Optionally send DTMF tones (useful for automated systems)
            # call.send_dtmf("1234")
            
            # Check final status
            call.check_call_status()
            
            # Hang up if still connected
            call.hangup_call()
        else:
            print("Failed to initiate call")
            
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        call.hangup_call()  # Ensure call is ended
    except Exception as e:
        print(f"Error: {e}")
        call.hangup_call()  # Ensure call is ended
    finally:
        call.disconnect()
        
    print("\n✅ Call session completed")

if __name__ == "__main__":
    main()