#!/usr/bin/env python3
"""
SMS Debug Script for Raspberry Pi
This script helps debug GSM modem SMS functionality step by step
Run with: sudo python3 sms_debug.py
"""

import serial
import time
import sys
import os

# Configuration - Modify these if needed
TEST_PHONE = "+306980531698"
DEBUG_MODE = True

class Colors:
    """Terminal colors for better readability"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_system():
    """Check system requirements"""
    print_header("SYSTEM CHECK")
    
    # Check if running as root
    if os.geteuid() != 0:
        print_warning("Not running as root. Some operations may fail.")
        print_info("Run with: sudo python3 sms_debug.py")
    else:
        print_success("Running as root")
    
    # Check for serial module
    try:
        import serial
        print_success(f"pyserial installed (version {serial.__version__})")
    except ImportError:
        print_error("pyserial not installed")
        print_info("Install with: sudo pip3 install pyserial")
        return False
    
    # Check for USB devices
    print_info("\nUSB Devices:")
    os.system("lsusb | grep -E 'GSM|Modem|Serial|UART|Qualcomm|Huawei|ZTE|Sierra'")
    
    return True

def scan_ports():
    """Scan all possible serial ports"""
    print_header("PORT SCAN")
    
    ports_to_check = [
        '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3',
        '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2',
        '/dev/serial0', '/dev/serial1',
        '/dev/ttyAMA0', '/dev/ttyAMA1',
        '/dev/ttyS0', '/dev/ttyS1'
    ]
    
    available_ports = []
    
    for port in ports_to_check:
        if os.path.exists(port):
            available_ports.append(port)
            print_success(f"Found port: {port}")
    
    if not available_ports:
        print_error("No serial ports found!")
        print_info("Check if modem is connected and powered on")
        return []
    
    return available_ports

def test_port(port, baud_rates=None):
    """Test a specific port with different baud rates"""
    if baud_rates is None:
        baud_rates = [9600, 115200, 19200, 38400, 57600]
    
    print(f"\n{Colors.BOLD}Testing {port}:{Colors.END}")
    
    for baud in baud_rates:
        try:
            print(f"  Trying {baud} baud...", end=" ")
            ser = serial.Serial(port, baud, timeout=2)
            time.sleep(1)
            
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Send AT command
            ser.write(b'AT\r\n')
            time.sleep(0.5)
            response = ser.read(200).decode('utf-8', errors='ignore')
            
            if 'OK' in response or 'AT' in response:
                print_success("CONNECTED!")
                ser.close()
                return baud, response
            else:
                print("No response")
            
            ser.close()
            
        except serial.SerialException as e:
            print(f"Port error: {str(e)[:30]}")
        except Exception as e:
            print(f"Error: {str(e)[:30]}")
    
    return None, None

def detect_modem():
    """Auto-detect modem port and settings"""
    print_header("MODEM DETECTION")
    
    available_ports = scan_ports()
    if not available_ports:
        return None, None
    
    for port in available_ports:
        baud, response = test_port(port)
        if baud:
            print_success(f"\nModem found at {port} ({baud} baud)")
            if DEBUG_MODE:
                print_info(f"Response: {response.strip()}")
            return port, baud
    
    print_error("\nNo modem responded on any port")
    return None, None

def get_modem_info(ser):
    """Get detailed modem information"""
    print_header("MODEM INFORMATION")
    
    commands = [
        (b'ATI\r\n', "Modem Identification"),
        (b'AT+CGMI\r\n', "Manufacturer"),
        (b'AT+CGMM\r\n', "Model"),
        (b'AT+CGSN\r\n', "IMEI"),
        (b'AT+CIMI\r\n', "IMSI"),
        (b'AT+CCID\r\n', "SIM Card ID"),
    ]
    
    for cmd, desc in commands:
        try:
            ser.write(cmd)
            time.sleep(0.5)
            response = ser.read(200).decode('utf-8', errors='ignore').strip()
            
            # Clean response
            lines = response.split('\n')
            result = [l.strip() for l in lines if l.strip() and 'OK' not in l and 'AT' not in l]
            
            if result:
                print(f"{Colors.BOLD}{desc}:{Colors.END} {', '.join(result)}")
            else:
                print_warning(f"{desc}: No data")
                
        except Exception as e:
            print_error(f"{desc}: {e}")

def check_network(ser):
    """Check network registration and signal"""
    print_header("NETWORK STATUS")
    
    # Check SIM card
    ser.write(b'AT+CPIN?\r\n')
    time.sleep(0.5)
    response = ser.read(200).decode('utf-8', errors='ignore')
    
    if 'READY' in response:
        print_success("SIM card ready")
    elif 'SIM PIN' in response:
        print_error("SIM card requires PIN")
        return False
    elif 'SIM PUK' in response:
        print_error("SIM card requires PUK")
        return False
    else:
        print_error(f"SIM card status: {response.strip()}")
        return False
    
    # Check network registration
    ser.write(b'AT+CREG?\r\n')
    time.sleep(0.5)
    response = ser.read(200).decode('utf-8', errors='ignore')
    
    if '+CREG: 0,1' in response:
        print_success("Registered on home network")
    elif '+CREG: 0,5' in response:
        print_success("Registered on roaming network")
    elif '+CREG: 0,2' in response:
        print_warning("Searching for network...")
        time.sleep(5)
        return check_network(ser)
    else:
        print_error(f"Not registered: {response.strip()}")
        print_info("Wait for network or check SIM/antenna")
        return False
    
    # Check signal strength
    ser.write(b'AT+CSQ\r\n')
    time.sleep(0.5)
    response = ser.read(200).decode('utf-8', errors='ignore')
    
    if '+CSQ:' in response:
        try:
            # Parse signal strength
            import re
            match = re.search(r'\+CSQ:\s*(\d+),(\d+)', response)
            if match:
                rssi = int(match.group(1))
                ber = int(match.group(2))
                
                if rssi == 99:
                    print_error("No signal detected")
                    return False
                elif rssi < 10:
                    print_warning(f"Weak signal (RSSI: {rssi})")
                elif rssi < 20:
                    print_success(f"Fair signal (RSSI: {rssi})")
                else:
                    print_success(f"Good signal (RSSI: {rssi})")
                
                # Signal bars representation
                bars = min(rssi // 6, 5)
                signal_visual = '█' * bars + '░' * (5 - bars)
                print_info(f"Signal strength: [{signal_visual}]")
        except:
            print_warning(f"Signal response: {response.strip()}")
    
    # Check operator
    ser.write(b'AT+COPS?\r\n')
    time.sleep(0.5)
    response = ser.read(200).decode('utf-8', errors='ignore')
    
    if '+COPS:' in response:
        import re
        match = re.search(r'"([^"]+)"', response)
        if match:
            print_success(f"Operator: {match.group(1)}")
    
    return True

def setup_sms_mode(ser):
    """Configure modem for SMS sending"""
    print_header("SMS CONFIGURATION")
    
    commands = [
        (b'ATE0\r\n', "Disable echo", False),
        (b'AT+CMGF=1\r\n', "Set text mode", True),
        (b'AT+CSCS="GSM"\r\n', "Set character set", False),
        (b'AT+CNMI=2,1,0,0,0\r\n', "SMS notifications", False),
        (b'AT+CPMS="SM","SM","SM"\r\n', "SMS storage", False),
    ]
    
    success = True
    for cmd, desc, required in commands:
        ser.write(cmd)
        time.sleep(0.5)
        response = ser.read(200).decode('utf-8', errors='ignore')
        
        if 'OK' in response:
            print_success(desc)
        elif 'ERROR' in response:
            if required:
                print_error(f"{desc} - REQUIRED")
                success = False
            else:
                print_warning(f"{desc} - optional")
        else:
            print_warning(f"{desc} - unclear response")
    
    return success

def send_test_sms(ser, phone_number):
    """Send a test SMS with detailed debugging"""
    print_header("SENDING TEST SMS")
    
    print_info(f"Recipient: {phone_number}")
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Ensure text mode
    ser.write(b'AT+CMGF=1\r\n')
    time.sleep(0.5)
    ser.read(100)
    
    # Start SMS
    print_info("Initiating SMS...")
    cmd = f'AT+CMGS="{phone_number}"\r\n'
    ser.write(cmd.encode())
    time.sleep(1)
    
    response = ser.read(200).decode('utf-8', errors='ignore')
    if DEBUG_MODE:
        print_info(f"Response: {response.strip()}")
    
    if '>' not in response:
        print_error("No SMS prompt received")
        print_info("Modem might not be ready or number format is wrong")
        
        # Try canceling any pending SMS
        ser.write(b'\x1B')  # ESC character
        time.sleep(0.5)
        return False
    
    print_success("SMS prompt received")
    
    # Send message
    message = f"Test SMS from RPi at {time.strftime('%H:%M:%S')}"
    print_info(f"Sending: {message}")
    
    ser.write(message.encode())
    ser.write(b'\x1A')  # Ctrl+Z to send
    
    # Wait for response
    print_info("Waiting for confirmation...")
    time.sleep(5)
    
    response = ser.read(500).decode('utf-8', errors='ignore')
    if DEBUG_MODE:
        print_info(f"Send response: {response.strip()}")
    
    if '+CMGS:' in response or 'OK' in response:
        print_success("SMS SENT SUCCESSFULLY!")
        return True
    elif 'ERROR' in response:
        print_error("SMS failed with ERROR")
        
        # Parse error code if available
        if '+CMS ERROR:' in response:
            import re
            match = re.search(r'\+CMS ERROR:\s*(\d+)', response)
            if match:
                error_code = match.group(1)
                print_error(f"Error code: {error_code}")
                print_info("Common error codes:")
                print_info("  330: SMSC address unknown")
                print_info("  500: Unknown error")
                print_info("  514: Invalid message format")
    else:
        print_warning("Unclear response - SMS may or may not have sent")
    
    return False

def interactive_test():
    """Run interactive SMS test"""
    print_header("INTERACTIVE SMS TEST")
    
    # Detect modem
    port, baud = detect_modem()
    if not port:
        print_error("Cannot proceed without modem")
        return
    
    try:
        # Connect to modem
        print_info(f"\nConnecting to {port} at {baud} baud...")
        ser = serial.Serial(port, baud, timeout=5)
        time.sleep(2)
        
        # Get modem info
        get_modem_info(ser)
        
        # Check network
        if not check_network(ser):
            print_error("Network not ready - cannot send SMS")
            ser.close()
            return
        
        # Setup SMS
        if not setup_sms_mode(ser):
            print_warning("SMS setup incomplete - trying anyway")
        
        # Ask for phone number
        print(f"\n{Colors.BOLD}Enter phone number (or press Enter for {TEST_PHONE}):{Colors.END} ", end="")
        phone = input().strip()
        if not phone:
            phone = TEST_PHONE
        
        # Send test SMS
        success = send_test_sms(ser, phone)
        
        if success:
            print_success("\n✓ SMS functionality working!")
            print_info(f"\nUpdate your firstTry.py with:")
            print(f'    SERIAL_PORT = "{port}"')
            print(f'    BAUD_RATE = {baud}')
        else:
            print_error("\n✗ SMS test failed")
            print_info("\nTroubleshooting:")
            print_info("1. Check SIM card has credit")
            print_info("2. Check phone number format (+country_code...)")
            print_info("3. Try different SMS center settings")
            print_info("4. Check antenna connection")
        
        ser.close()
        
    except Exception as e:
        print_error(f"Fatal error: {e}")
        import traceback
        if DEBUG_MODE:
            traceback.print_exc()

def main():
    """Main entry point"""
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print("╔══════════════════════════════════════════╗")
    print("║     SMS DEBUG TOOL FOR RASPBERRY PI      ║")
    print("║           Version 1.0                    ║")
    print("╚══════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    # System check
    if not check_system():
        print_error("System requirements not met")
        sys.exit(1)
    
    # Run interactive test
    interactive_test()
    
    print(f"\n{Colors.BOLD}Debug session complete{Colors.END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {e}{Colors.END}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()