#!/usr/bin/env python3
"""
SMS Debug Script for SIM7070G
Diagnoses CMS ERROR 500 and other SMS issues
"""
import serial
import time
import sys

class SMSDebugger:
    def __init__(self):
        self.ser = None
        self.phone = "+306980531698"  # Updated phone number
        
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
            "500": "Unknown error (often SIM/network config issue)",
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
            print(f"   ❌ CMS Error {error_code}: {cms_errors[error_code]}")
        else:
            print(f"   ❌ Unknown CMS error code: {error_code}")
    
    def send_at(self, cmd, wait=2, show_raw=False):
        """Send AT command and return response"""
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\r\n".encode())
        time.sleep(wait)
        
        response = self.ser.read(self.ser.in_waiting or 300).decode('utf-8', errors='ignore')
        if show_raw:
            print(f"   Raw: {repr(response)}")
        print(f"   {cmd}: {response.strip()}")
        return response
    
    def init_module(self):
        """Initialize module with power control"""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(4, GPIO.OUT)
            
            print("Power cycling module...")
            GPIO.output(4, GPIO.LOW)
            time.sleep(3)
            GPIO.output(4, GPIO.HIGH)
            time.sleep(3)
            GPIO.output(4, GPIO.LOW)
            time.sleep(15)
            
        except Exception as e:
            print(f"GPIO error: {e}")
        
        # Connect
        self.ser = serial.Serial('/dev/serial0', 57600, timeout=5)
        time.sleep(2)
        
        # Test basic communication
        for i in range(5):
            response = self.send_at("AT", 1)
            if "OK" in response:
                print("✓ Module responding")
                break
        else:
            print("✗ Module not responding")
            return False
        
        # Disable echo
        self.send_at("ATE0", 1)
        return True
    
    def comprehensive_diagnosis(self):
        """Run comprehensive SMS diagnosis"""
        print("=== SMS COMPREHENSIVE DIAGNOSIS ===")
        
        # Basic module info
        print("\n1. Module Information")
        self.send_at("ATI")
        self.send_at("AT+CGMM") 
        self.send_at("AT+CGMR")  # Firmware version
        self.send_at("AT+CGSN")  # IMEI
        
        # SIM card detailed check
        print("\n2. SIM Card Diagnosis")
        self.send_at("AT+CPIN?")
        self.send_at("AT+CCID")   # SIM card ID
        self.send_at("AT+CIMI")   # IMSI
        self.send_at("AT+CPBS=?") # Phonebook storage options
        self.send_at("AT+CPMS=?") # SMS storage options
        
        # Network registration detailed
        print("\n3. Network Registration")
        self.send_at("AT+CREG?")
        self.send_at("AT+CREG=2")  # Enable network registration URC
        self.send_at("AT+CREG?")
        self.send_at("AT+COPS?")   # Current operator
        self.send_at("AT+COPS=?")  # Available operators (takes time)
        
        # Signal and network quality
        print("\n4. Signal and Network Quality")
        self.send_at("AT+CSQ")     # Signal quality
        self.send_at("AT+CESQ")    # Extended signal quality
        self.send_at("AT+CPSI?")   # Serving cell info
        
        # SMS configuration detailed
        print("\n5. SMS Configuration")
        self.send_at("AT+CMGF?")   # Current SMS format
        self.send_at("AT+CMGF=1")  # Set text mode
        self.send_at("AT+CMGF?")   # Verify text mode
        self.send_at("AT+CSCA?")   # SMS service center address
        self.send_at("AT+CPMS?")   # Current SMS storage
        self.send_at("AT+CPMS=\"SM\",\"SM\",\"SM\"")  # Set SMS storage to SIM
        self.send_at("AT+CPMS?")   # Verify SMS storage
        self.send_at("AT+CNMI?")   # SMS indication settings
        
        # Error reporting
        print("\n6. Error Reporting Configuration")
        self.send_at("AT+CMEE=2")  # Enable verbose error reporting
        self.send_at("AT+CMEE?")   # Check error reporting mode
    
    def test_different_sms_methods(self):
        """Test different SMS sending methods"""
        print("\n=== TESTING DIFFERENT SMS METHODS ===")
        
        methods = [
            ("Standard text mode", 'AT+CMGS="{}"', True),
            ("Without quotes", 'AT+CMGS={}', False),
            ("International format", 'AT+CMGS="+30{}"', True),
            ("National format", 'AT+CMGS="30{}"', True),
        ]
        
        phone_base = "6980531698"
        test_message = "Test SMS from debug script"
        
        for method_name, cmd_format, use_plus in methods:
            print(f"\n--- Testing: {method_name} ---")
            
            if use_plus and not self.phone.startswith('+'):
                test_phone = '+' + self.phone
            elif not use_plus:
                test_phone = self.phone.replace('+', '')
            else:
                test_phone = self.phone
            
            if '{}' in cmd_format:
                if use_plus and method_name == "International format":
                    cmd = cmd_format.format(phone_base)
                else:
                    cmd = cmd_format.format(test_phone)
            else:
                cmd = cmd_format
                
            print(f"Command: {cmd}")
            
            # Set text mode first
            self.send_at("AT+CMGF=1", 1)
            
            # Send command
            self.ser.reset_input_buffer()
            self.ser.write(f"{cmd}\r".encode())
            time.sleep(3)
            
            response = self.ser.read(self.ser.in_waiting or 200)
            print(f"Response: {response}")
            
            if b'>' in response:
                print("✓ Got SMS prompt")
                
                # Send message
                self.ser.write(test_message.encode())
                time.sleep(1)
                self.ser.write(b'\x1A')
                
                # Wait for result
                time.sleep(15)
                result = self.ser.read(self.ser.in_waiting or 300).decode('utf-8', errors='ignore')
                print(f"Result: {result}")
                
                if "+CMGS" in result:
                    print(f"✅ {method_name} WORKED!")
                    return True
                elif "CMS ERROR" in result:
                    error_code = result.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in result else "unknown"
                    self.print_cms_error_meaning(error_code)
                else:
                    print("❌ Unknown response")
            else:
                print("❌ No SMS prompt received")
                if b"ERROR" in response or b"CMS ERROR" in response:
                    if b"CMS ERROR" in response:
                        error_code = response.decode('utf-8', errors='ignore').split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in response else "unknown"
                        self.print_cms_error_meaning(error_code)
            
            print("Waiting before next attempt...")
            time.sleep(5)
        
        return False
    
    def test_sms_storage_and_format(self):
        """Test different SMS storage locations and formats"""
        print("\n=== TESTING SMS STORAGE AND FORMATS ===")
        
        # Test different storage locations
        storages = ["SM", "ME", "MT"]
        for storage in storages:
            print(f"\nTesting storage: {storage}")
            resp = self.send_at(f'AT+CPMS="{storage}","{storage}","{storage}"', 2)
            if "OK" in resp:
                print(f"✓ Storage {storage} available")
                # Try sending SMS with this storage
                self.send_at("AT+CMGF=1", 1)
                
                self.ser.reset_input_buffer()
                self.ser.write(f'AT+CMGS="{self.phone}"\r'.encode())
                time.sleep(3)
                
                response = self.ser.read(self.ser.in_waiting or 200)
                if b'>' in response:
                    self.ser.write(b'Storage test SMS\x1A')
                    time.sleep(10)
                    result = self.ser.read(self.ser.in_waiting or 200).decode('utf-8', errors='ignore')
                    if "+CMGS" in result:
                        print(f"✅ SMS sent successfully with {storage} storage!")
                        return True
                    else:
                        print(f"❌ SMS failed with {storage} storage")
            else:
                print(f"❌ Storage {storage} not available")
        
        return False
    
    def run_debug(self):
        """Run complete debug session"""
        print("=== SIM7070G SMS DEBUGGER ===")
        print(f"Target phone: {self.phone}")
        
        if not self.init_module():
            print("Failed to initialize module")
            return
        
        try:
            # Step 1: Comprehensive diagnosis
            self.comprehensive_diagnosis()
            
            # Step 2: Test different SMS methods
            if self.test_different_sms_methods():
                print("\n🎉 Found working SMS method!")
                return
            
            # Step 3: Test storage and formats
            if self.test_sms_storage_and_format():
                print("\n🎉 Found working SMS configuration!")
                return
            
            print("\n❌ All SMS methods failed")
            print("\nTroubleshooting suggestions:")
            print("1. Check if SIM card supports SMS")
            print("2. Verify SMS service center number")
            print("3. Try with a different SIM card")
            print("4. Check if SMS is enabled on this SIM plan")
            print("5. Try sending to a different phone number")
            
        except KeyboardInterrupt:
            print("\nDebug interrupted by user")
        finally:
            if self.ser:
                self.ser.close()
            print("\nDebug session complete")

def main():
    debugger = SMSDebugger()
    debugger.run_debug()

if __name__ == "__main__":
    main()