#!/usr/bin/env python3
"""
SIM7070G Internet Connectivity Test Script
Tests cellular data connection and makes HTTP requests to verify internet access
"""

import serial
import time
import sys
import json
from datetime import datetime

class SIM7070GInternetTest:
    def __init__(self):
        self.ser = None
        self.GPIO = None
        
    def init_gpio(self):
        """Initialize GPIO for SIM module power control"""
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup SIM power control pin
            GPIO.setup(4, GPIO.OUT)
            
            print("[OK] GPIO initialized")
            return True
        except Exception as e:
            print(f"[ERROR] GPIO init failed: {e}")
            return False
    
    def power_cycle_sim(self):
        """Power cycle the SIM7070G module"""
        print("[POWER] Power cycling SIM7070G module...")
        
        # Power cycle sequence
        self.GPIO.output(4, self.GPIO.LOW)
        time.sleep(3)
        self.GPIO.output(4, self.GPIO.HIGH)
        time.sleep(3)
        self.GPIO.output(4, self.GPIO.LOW)
        
        print("[WAIT] Waiting 20 seconds for module boot...")
        time.sleep(20)
    
    def init_serial(self):
        """Initialize serial connection to SIM7070G"""
        try:
            self.ser = serial.Serial('/dev/serial0', 57600, timeout=10)
            time.sleep(2)
            print("[OK] Serial connection established")
            return True
        except Exception as e:
            print(f"[ERROR] Serial init failed: {e}")
            return False
    
    def send_at_command(self, command, timeout=5, expected_response="OK"):
        """Send AT command and wait for response"""
        try:
            print(f"[CMD] Sending: {command.strip()}")
            
            # Clear input buffer
            self.ser.reset_input_buffer()
            
            # Send command
            self.ser.write(command.encode() + b'\r\n')
            
            # Wait and read response
            start_time = time.time()
            response = ""
            
            while time.time() - start_time < timeout:
                if self.ser.in_waiting > 0:
                    response += self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                
                if expected_response in response:
                    print(f"[RESP] {response.strip()}")
                    return True, response
                    
                time.sleep(0.1)
            
            print(f"[RESP] Timeout or unexpected response: {response.strip()}")
            return False, response
            
        except Exception as e:
            print(f"[ERROR] AT command failed: {e}")
            return False, str(e)
    
    def test_basic_communication(self):
        """Test basic AT communication with SIM7070G"""
        print("\n=== Testing Basic Communication ===")
        
        for attempt in range(5):
            print(f"[TEST] Communication attempt {attempt + 1}/5")
            success, response = self.send_at_command("AT", timeout=3)
            
            if success:
                print("✅ Basic communication working")
                return True
            
            time.sleep(2)
        
        print("❌ Basic communication failed")
        return False
    
    def check_sim_card(self):
        """Check SIM card status"""
        print("\n=== Checking SIM Card ===")
        
        # Check SIM card presence
        success, response = self.send_at_command("AT+CPIN?", timeout=5)
        if not success:
            print("❌ SIM card check failed")
            return False
        
        if "READY" in response:
            print("✅ SIM card is ready")
        elif "SIM PIN" in response:
            print("⚠️ SIM card requires PIN")
            return False
        else:
            print("❌ SIM card not ready")
            return False
        
        # Get SIM card info
        success, response = self.send_at_command("AT+CCID", timeout=5)
        if success and "CCID:" in response:
            ccid = response.split("CCID:")[1].strip().split()[0]
            print(f"📱 SIM CCID: {ccid}")
        
        return True
    
    def check_network_registration(self):
        """Check network registration status"""
        print("\n=== Checking Network Registration ===")
        
        # Check network registration
        for attempt in range(30):
            success, response = self.send_at_command("AT+CREG?", timeout=3)
            
            if success and "+CREG:" in response:
                # Parse response: +CREG: n,stat
                parts = response.split("+CREG:")[1].strip().split(",")
                if len(parts) >= 2:
                    status = parts[1].strip()
                    
                    if status == "1":
                        print("✅ Registered on home network")
                        return True
                    elif status == "5":
                        print("✅ Registered on roaming network")
                        return True
                    elif status == "2":
                        print("🔍 Searching for network...")
                    elif status == "0":
                        print("❌ Not registered, not searching")
                    elif status == "3":
                        print("❌ Registration denied")
                        return False
            
            print(f"⏳ Waiting for network registration... ({attempt + 1}/30)")
            time.sleep(2)
        
        print("❌ Network registration failed")
        return False
    
    def check_signal_quality(self):
        """Check signal quality"""
        print("\n=== Checking Signal Quality ===")
        
        success, response = self.send_at_command("AT+CSQ", timeout=5)
        
        if success and "+CSQ:" in response:
            # Parse response: +CSQ: rssi,ber
            parts = response.split("+CSQ:")[1].strip().split(",")
            if len(parts) >= 2:
                rssi = int(parts[0].strip())
                ber = parts[1].strip()
                
                if rssi == 99:
                    print("❌ No signal detected")
                    return False
                else:
                    # Convert to dBm: -113 + 2*rssi
                    dbm = -113 + (2 * rssi)
                    
                    print(f"📶 Signal strength: {rssi} ({dbm} dBm)")
                    
                    if dbm > -70:
                        print("✅ Excellent signal")
                    elif dbm > -85:
                        print("✅ Good signal")
                    elif dbm > -100:
                        print("⚠️ Fair signal")
                    else:
                        print("⚠️ Poor signal - may affect data connection")
                    
                    return True
        
        print("❌ Signal quality check failed")
        return False
    
    def setup_data_connection(self):
        """Set up data connection and attach to GPRS"""
        print("\n=== Setting Up Data Connection ===")
        
        # Set APN (adjust for your carrier)
        apn_commands = [
            ('AT+CGDCONT=1,"IP","internet"', "Set APN to 'internet'"),
            ('AT+CGDCONT=1,"IP","cosmote"', "Try APN 'cosmote'"),
            ('AT+CGDCONT=1,"IP","data.cosmote.gr"', "Try APN 'data.cosmote.gr'"),
        ]
        
        apn_set = False
        for cmd, desc in apn_commands:
            print(f"[TRY] {desc}")
            success, response = self.send_at_command(cmd, timeout=5)
            if success:
                print(f"✅ {desc} - OK")
                apn_set = True
                break
            else:
                print(f"⚠️ {desc} - Failed, trying next...")
        
        if not apn_set:
            print("❌ Failed to set any APN")
            return False
        
        # Attach to GPRS
        print("[SETUP] Attaching to GPRS network...")
        success, response = self.send_at_command("AT+CGATT=1", timeout=30)
        if not success:
            print("❌ GPRS attach failed")
            return False
        
        print("✅ GPRS attached successfully")
        
        # Check attachment status
        success, response = self.send_at_command("AT+CGATT?", timeout=5)
        if success and "+CGATT: 1" in response:
            print("✅ GPRS attachment confirmed")
        else:
            print("⚠️ GPRS attachment status unclear")
        
        return True
    
    def test_http_request(self, url="http://httpbin.org/get", test_name="HTTP Test"):
        """Test HTTP request to verify internet connectivity"""
        print(f"\n=== {test_name} ===")
        print(f"[HTTP] Testing connection to: {url}")
        
        try:
            # Initialize HTTP service
            success, response = self.send_at_command("AT+HTTPINIT", timeout=10)
            if not success:
                print("❌ HTTP initialization failed")
                return False
            
            # Set HTTP parameters
            success, response = self.send_at_command('AT+HTTPPARA="CID",1', timeout=5)
            if not success:
                print("❌ HTTP CID parameter failed")
                return False
            
            # Set URL
            success, response = self.send_at_command(f'AT+HTTPPARA="URL","{url}"', timeout=5)
            if not success:
                print("❌ HTTP URL parameter failed")
                return False
            
            # Perform GET request
            print("[HTTP] Sending GET request...")
            success, response = self.send_at_command("AT+HTTPACTION=0", timeout=30)
            
            if success:
                # Wait for response and check status
                time.sleep(5)
                success, response = self.send_at_command("AT+HTTPREAD", timeout=10)
                
                if success and "200" in response:
                    print("✅ HTTP request successful!")
                    print("[RESP] Response received (showing first 200 chars):")
                    
                    # Extract and display response content
                    lines = response.split('\n')
                    content_started = False
                    content = ""
                    
                    for line in lines:
                        if '+HTTPREAD:' in line:
                            content_started = True
                            continue
                        if content_started and line.strip():
                            content += line + "\n"
                    
                    # Show first 200 characters of response
                    if content:
                        print(content[:200] + "..." if len(content) > 200 else content)
                    
                    # Terminate HTTP
                    self.send_at_command("AT+HTTPTERM", timeout=5)
                    return True
                else:
                    print("❌ HTTP request failed or no response")
            else:
                print("❌ HTTP action failed")
            
            # Terminate HTTP
            self.send_at_command("AT+HTTPTERM", timeout=5)
            return False
            
        except Exception as e:
            print(f"❌ HTTP test error: {e}")
            self.send_at_command("AT+HTTPTERM", timeout=5)
            return False
    
    def test_dns_resolution(self):
        """Test DNS resolution"""
        print("\n=== Testing DNS Resolution ===")
        
        # Test DNS resolution
        success, response = self.send_at_command('AT+CDNSGIP="google.com"', timeout=15)
        
        if success and "CDNSGIP:" in response:
            print("✅ DNS resolution working")
            
            # Extract IP address
            lines = response.split('\n')
            for line in lines:
                if '+CDNSGIP:' in line and '.' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        ip = parts[1].strip().strip('"')
                        print(f"🌐 google.com resolved to: {ip}")
                        break
            return True
        else:
            print("❌ DNS resolution failed")
            return False
    
    def comprehensive_test(self):
        """Run comprehensive internet connectivity test"""
        print("🚀 SIM7070G Internet Connectivity Test")
        print("=" * 50)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        test_results = {}
        
        # Initialize hardware
        if not self.init_gpio():
            return False
        
        self.power_cycle_sim()
        
        if not self.init_serial():
            return False
        
        # Run tests
        tests = [
            ("basic_communication", self.test_basic_communication),
            ("sim_card", self.check_sim_card),
            ("network_registration", self.check_network_registration),
            ("signal_quality", self.check_signal_quality),
            ("data_connection", self.setup_data_connection),
            ("dns_resolution", self.test_dns_resolution),
            ("http_test_1", lambda: self.test_http_request("http://httpbin.org/get", "Basic HTTP Test")),
            ("http_test_2", lambda: self.test_http_request("http://google.com", "Google Connectivity Test")),
            ("http_test_3", lambda: self.test_http_request("http://api.github.com", "API Endpoint Test")),
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                test_results[test_name] = result
                
                if not result:
                    print(f"\n⚠️ Test '{test_name}' failed - continuing with remaining tests...")
                
            except Exception as e:
                print(f"\n❌ Test '{test_name}' crashed: {e}")
                test_results[test_name] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<25} {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Internet connectivity is working!")
            return True
        elif passed >= 6:  # If basic connectivity works
            print("⚠️ Basic internet connectivity working, some advanced features may have issues")
            return True
        else:
            print("❌ Internet connectivity has issues - check SIM card, APN settings, and signal")
            return False
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            if self.GPIO:
                self.GPIO.cleanup()
            
            print("\n[OK] Cleanup complete")
        except:
            pass

def main():
    """Main test function"""
    tester = SIM7070GInternetTest()
    
    try:
        success = tester.comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()