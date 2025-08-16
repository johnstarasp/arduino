#!/bin/bash

# This script fixes the firstTry.py for SMS functionality
echo "Fixing firstTry.py for SMS functionality..."

# Create a test script to check modem connection
cat > test_modem.py << 'EOF'
import serial
import time
import sys

def test_modem():
    ports = ["/dev/serial0", "/dev/ttyS0", "/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    baud_rates = [9600, 115200]
    
    print("Testing modem connectivity...")
    
    for port in ports:
        for baud in baud_rates:
            try:
                print(f"\nTrying {port} at {baud} baud...")
                ser = serial.Serial(port, baud, timeout=2)
                time.sleep(2)
                
                # Send AT command
                ser.write(b'AT\r\n')
                time.sleep(1)
                response = ser.read(100).decode('utf-8', errors='ignore')
                
                if 'OK' in response or 'AT' in response:
                    print(f"SUCCESS! Modem found at {port} with {baud} baud")
                    print(f"Response: {response}")
                    
                    # Test more commands
                    commands = [
                        (b'AT+CGMI\r\n', "Manufacturer"),
                        (b'AT+CGMM\r\n', "Model"),
                        (b'AT+CGSN\r\n', "IMEI"),
                        (b'AT+CREG?\r\n', "Network Registration"),
                        (b'AT+CSQ\r\n', "Signal Quality"),
                        (b'AT+COPS?\r\n', "Operator")
                    ]
                    
                    for cmd, desc in commands:
                        ser.write(cmd)
                        time.sleep(1)
                        resp = ser.read(200).decode('utf-8', errors='ignore')
                        print(f"{desc}: {resp.strip()}")
                    
                    ser.close()
                    return port, baud
                    
                ser.close()
            except Exception as e:
                print(f"  Failed: {e}")
                continue
    
    print("\nNo modem found on any port!")
    return None, None

if __name__ == "__main__":
    port, baud = test_modem()
    if port:
        print(f"\n\nMODEM CONFIGURATION:")
        print(f"Port: {port}")
        print(f"Baud Rate: {baud}")
        print("\nUpdate your firstTry.py with these settings!")
EOF

echo "Test script created. Now creating improved firstTry.py..."

# Create improved version
cat > firstTry_fixed.py << 'EOF'
import RPi.GPIO as GPIO
import time
import serial
import logging
import threading
from collections import deque
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
HALL_SENSOR_PIN = 17
CIRCUMFERENCE = 0.5  # meters
SMS_PHONE_NUMBER = "+306980531698"  # Replace with your phone number
SERIAL_PORT = "/dev/serial0"  # Will be auto-detected
BAUD_RATE = 9600  # Will be auto-detected
SMS_INTERVAL = 10  # seconds
DEBOUNCE_TIME = 0.05  # seconds
MAX_RETRIES = 3
SPEED_HISTORY_SIZE = 10

# -----------------------------
# SETUP
# -----------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/bike_speedometer.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize GPIO with error handling
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    logger.info(f"GPIO initialized successfully on pin {HALL_SENSOR_PIN}")
except Exception as e:
    logger.error(f"Failed to initialize GPIO: {e}")
    logger.error("Make sure you're running with sudo and GPIO is available")
    raise

class ModemManager:
    def __init__(self, serial_port, baud_rate):
        self.ser = None
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.lock = threading.Lock()
        
    def auto_detect_modem(self):
        """Auto-detect modem port and baud rate"""
        ports = ["/dev/serial0", "/dev/ttyS0", "/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]
        baud_rates = [9600, 115200, 19200, 38400]
        
        for port in ports:
            for baud in baud_rates:
                try:
                    logger.info(f"Trying {port} at {baud} baud...")
                    test_ser = serial.Serial(port, baud, timeout=2)
                    time.sleep(1)
                    
                    # Clear any pending data
                    test_ser.reset_input_buffer()
                    test_ser.reset_output_buffer()
                    
                    # Send AT command
                    test_ser.write(b'AT\r\n')
                    time.sleep(0.5)
                    response = test_ser.read(100).decode('utf-8', errors='ignore')
                    
                    if 'OK' in response:
                        logger.info(f"Modem detected at {port} with {baud} baud")
                        self.serial_port = port
                        self.baud_rate = baud
                        test_ser.close()
                        return True
                    
                    test_ser.close()
                except:
                    continue
        
        logger.error("No modem detected on any port")
        return False
        
    def connect(self):
        try:
            # Try auto-detection first
            if not self.auto_detect_modem():
                logger.error("Auto-detection failed, trying configured port...")
                
            # Connect with detected or configured settings
            logger.info(f"Connecting to {self.serial_port} at {self.baud_rate} baud...")
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=5)
            time.sleep(2)
            
            # Clear buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # Test connection
            self.ser.write(b'AT\r\n')
            time.sleep(0.5)
            response = self.ser.read(100).decode('utf-8', errors='ignore')
            
            if 'OK' in response:
                logger.info("Modem connected successfully")
                return True
            else:
                logger.error(f"Modem not responding. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to modem: {e}")
            return False
    
    def init_modem(self):
        """Initialize modem with improved error handling"""
        try:
            # Clear buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            commands = [
                (b'AT\r\n', "Reset", True),
                (b'ATE0\r\n', "Disable echo", False),
                (b'AT+CMGF=1\r\n', "Set SMS text mode", True),
                (b'AT+CNMI=2,1,0,0,0\r\n', "SMS notification", False),
                (b'AT+CSCS="GSM"\r\n', "Character set", False),
                (b'AT+CPMS="SM","SM","SM"\r\n', "SMS storage", False)
            ]
            
            for cmd, desc, required in commands:
                success = self._send_at_command(cmd, desc)
                if not success and required:
                    logger.error(f"Required command failed: {desc}")
                    return False
            
            # Check network registration
            self._check_network()
            
            return True
            
        except Exception as e:
            logger.error(f"Modem initialization failed: {e}")
            return False
    
    def _check_network(self):
        """Check network registration status"""
        try:
            self.ser.write(b'AT+CREG?\r\n')
            time.sleep(1)
            response = self.ser.read(200).decode('utf-8', errors='ignore')
            
            if '+CREG: 0,1' in response or '+CREG: 0,5' in response:
                logger.info("Network registered (home or roaming)")
                
                # Check signal strength
                self.ser.write(b'AT+CSQ\r\n')
                time.sleep(1)
                signal_resp = self.ser.read(100).decode('utf-8', errors='ignore')
                logger.info(f"Signal quality: {signal_resp.strip()}")
                
                return True
            else:
                logger.warning(f"Not registered on network: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Network check failed: {e}")
            return False
    
    def _send_at_command(self, command, description="", timeout=2):
        with self.lock:
            try:
                if not self.ser or not self.ser.is_open:
                    logger.error("Serial port not open")
                    return False
                
                # Clear input buffer
                self.ser.reset_input_buffer()
                
                # Send command
                self.ser.write(command)
                time.sleep(0.5)
                
                # Read response
                response = self.ser.read(500).decode('utf-8', errors='ignore')
                logger.debug(f"{description} - Cmd: {command.strip()}")
                logger.debug(f"{description} - Response: {response.strip()}")
                
                if 'OK' in response:
                    logger.info(f"{description}: Success")
                    return True
                elif 'ERROR' in response:
                    logger.error(f"{description}: Error - {response}")
                    return False
                else:
                    logger.warning(f"{description}: Unclear response - {response}")
                    return 'AT' in response  # Basic check if modem responded
                    
            except Exception as e:
                logger.error(f"Command error ({description}): {e}")
                return False
    
    def send_sms(self, number, message):
        """Send SMS with improved error handling"""
        with self.lock:
            for attempt in range(MAX_RETRIES):
                try:
                    logger.info(f"SMS attempt {attempt + 1}/{MAX_RETRIES}")
                    
                    # Check network first
                    if not self._check_network():
                        logger.warning("Network not ready, waiting...")
                        time.sleep(5)
                        continue
                    
                    # Clear buffers
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                    
                    # Set text mode again (in case it was reset)
                    self.ser.write(b'AT+CMGF=1\r\n')
                    time.sleep(0.5)
                    self.ser.read(100)
                    
                    # Send SMS command
                    cmd = f'AT+CMGS="{number}"\r\n'
                    self.ser.write(cmd.encode())
                    time.sleep(1)
                    
                    response = self.ser.read(100).decode('utf-8', errors='ignore')
                    logger.debug(f"CMGS response: {response}")
                    
                    if '>' in response:
                        # Send message text
                        msg_with_ctrl_z = f'{message}\x1A'
                        self.ser.write(msg_with_ctrl_z.encode())
                        
                        # Wait for confirmation
                        time.sleep(5)
                        final_response = self.ser.read(500).decode('utf-8', errors='ignore')
                        logger.debug(f"SMS send response: {final_response}")
                        
                        if '+CMGS' in final_response or 'OK' in final_response:
                            logger.info(f"SMS sent successfully to {number}")
                            return True
                        else:
                            logger.warning(f"SMS send unclear: {final_response}")
                    else:
                        logger.warning(f"No prompt received: {response}")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"SMS send error: {e}")
                    time.sleep(2)
            
            logger.error(f"Failed to send SMS after {MAX_RETRIES} attempts")
            return False
    
    def close(self):
        if self.ser:
            try:
                self.ser.close()
                logger.info("Modem connection closed")
            except:
                pass

class SpeedSensor:
    def __init__(self, pin, circumference, debounce_time=DEBOUNCE_TIME):
        self.pin = pin
        self.circumference = circumference
        self.debounce_time = debounce_time
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.speed_history = deque(maxlen=SPEED_HISTORY_SIZE)
        self.lock = threading.Lock()
        
    def detect_pulse(self, last_state, current_state):
        current_time = time.time()
        
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            if current_time - self.last_pulse_time > self.debounce_time:
                with self.lock:
                    self.pulse_count += 1
                    self.last_pulse_time = current_time
                logger.debug(f"Pulse {self.pulse_count} detected")
                return True
        return False
    
    def calculate_speed(self, duration):
        with self.lock:
            pulses = self.pulse_count
            self.pulse_count = 0
            
        distance = pulses * self.circumference
        speed_mps = distance / duration if duration > 0 else 0
        speed_kph = speed_mps * 3.6
        
        self.speed_history.append(speed_kph)
        avg_speed = sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0
        
        return speed_kph, avg_speed, pulses

def format_sms_message(speed_kph, avg_speed, pulses, timestamp):
    return (
        f"Bike Speed\n"
        f"{timestamp}\n"
        f"Speed: {speed_kph:.1f}km/h\n"
        f"Avg: {avg_speed:.1f}km/h\n"
        f"Pulses: {pulses}"
    )

def main():
    logger.info("=" * 50)
    logger.info("Starting Enhanced Bike Speedometer v2.0")
    logger.info("=" * 50)
    logger.info(f"Configuration:")
    logger.info(f"  Hall Sensor Pin: {HALL_SENSOR_PIN}")
    logger.info(f"  Wheel Circumference: {CIRCUMFERENCE}m")
    logger.info(f"  SMS Interval: {SMS_INTERVAL}s")
    logger.info(f"  SMS Number: {SMS_PHONE_NUMBER}")
    
    # Test GPIO
    try:
        test_state = GPIO.input(HALL_SENSOR_PIN)
        logger.info(f"GPIO test successful. Initial state: {test_state}")
    except Exception as e:
        logger.error(f"GPIO test failed: {e}")
        return
    
    # Initialize modem
    modem = ModemManager(SERIAL_PORT, BAUD_RATE)
    sensor = SpeedSensor(HALL_SENSOR_PIN, CIRCUMFERENCE)
    
    modem_available = False
    try:
        if modem.connect():
            modem_available = modem.init_modem()
            if modem_available:
                logger.info("✓ Modem ready for SMS")
                # Send test SMS
                logger.info("Sending test SMS...")
                if modem.send_sms(SMS_PHONE_NUMBER, "Bike speedometer started!"):
                    logger.info("✓ Test SMS sent successfully")
                else:
                    logger.warning("Test SMS failed")
            else:
                logger.warning("Modem initialization failed")
        else:
            logger.warning("Modem connection failed - continuing without SMS")
    except Exception as e:
        logger.error(f"Modem setup error: {e}")
    
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    try:
        logger.info("Starting main loop...")
        
        while True:
            logger.info(f"\n--- Measuring for {SMS_INTERVAL} seconds ---")
            
            last_state = GPIO.input(HALL_SENSOR_PIN)
            start_time = time.time()
            
            while (time.time() - start_time) < SMS_INTERVAL:
                try:
                    current_state = GPIO.input(HALL_SENSOR_PIN)
                    sensor.detect_pulse(last_state, current_state)
                    last_state = current_state
                    time.sleep(0.001)
                except Exception as e:
                    logger.error(f"GPIO error: {e}")
                    break
            
            elapsed_time = time.time() - start_time
            speed_kph, avg_speed, pulses = sensor.calculate_speed(elapsed_time)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            logger.info(f"Results: Speed={speed_kph:.2f}km/h, Avg={avg_speed:.2f}km/h, Pulses={pulses}")
            
            if modem_available and pulses > 0:  # Only send SMS if there's movement
                msg = format_sms_message(speed_kph, avg_speed, pulses, timestamp)
                
                if modem.send_sms(SMS_PHONE_NUMBER, msg):
                    consecutive_failures = 0
                    logger.info("✓ SMS sent")
                else:
                    consecutive_failures += 1
                    logger.warning(f"SMS failed ({consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error("Reinitializing modem...")
                        modem.close()
                        time.sleep(2)
                        
                        if modem.connect() and modem.init_modem():
                            consecutive_failures = 0
                            logger.info("✓ Modem reinitialized")
                        else:
                            modem_available = False
                            logger.error("Modem lost - continuing without SMS")
            
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        GPIO.cleanup()
        if modem:
            modem.close()
        logger.info("Cleanup complete. Goodbye!")

if __name__ == "__main__":
    main()
EOF

echo "Scripts created successfully!"
echo ""
echo "To use these scripts on your Raspberry Pi:"
echo "1. First run: sudo python3 test_modem.py"
echo "   This will detect your modem's correct port and baud rate"
echo ""
echo "2. Then run: sudo python3 firstTry_fixed.py"
echo "   This is the improved version with better SMS handling"
echo ""
echo "The scripts will create a log file at /tmp/bike_speedometer.log"