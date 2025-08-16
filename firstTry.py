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
# Raspberry Pi 2 uses /dev/ttyAMA0 for UART
# Make sure to disable bluetooth on Pi 3+ or use /dev/serial0
SERIAL_PORT = "/dev/serial0"  # SIMCOM SIM7070 detected
BAUD_RATE = 57600  # Correct baud rate for SIM7070
SMS_INTERVAL = 10  # seconds
DEBOUNCE_TIME = 0.05  # seconds
MAX_RETRIES = 3
SPEED_HISTORY_SIZE = 10

# -----------------------------
# SETUP
# -----------------------------
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for better troubleshooting
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
        
    def connect(self):
        try:
            # Try multiple serial ports for compatibility
            ports_to_try = [self.serial_port, "/dev/ttyS0", "/dev/serial0", "/dev/ttyAMA0"]
            for port in ports_to_try:
                try:
                    logger.info(f"Trying to connect to {port}...")
                    self.ser = serial.Serial(port, self.baud_rate, timeout=2)
                    time.sleep(2)
                    # Test connection with AT command
                    self.ser.write(b'AT\r')
                    time.sleep(0.5)
                    response = self.ser.read(100).decode('utf-8', errors='ignore')
                    if 'OK' in response or 'AT' in response:
                        logger.info(f"Successfully connected to modem on {port}")
                        self.serial_port = port
                        return True
                    else:
                        self.ser.close()
                except (serial.SerialException, OSError) as e:
                    logger.debug(f"Failed to connect on {port}: {e}")
                    continue
            logger.error("Failed to connect to modem on any port")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to modem: {e}")
            return False
    
    def init_modem(self):
        commands = [
            (b'AT\r', "Basic AT test"),
            (b'AT+CMGF=1\r', "Set SMS text mode"),
            (b'AT+CFUN=1\r', "Set full functionality"),
            (b'AT+CSCS="GSM"\r', "Set character set")
        ]
        
        for cmd, desc in commands:
            if not self._send_at_command(cmd, desc):
                return False
        return True
    
    def _send_at_command(self, command, description=""):
        with self.lock:
            try:
                if not self.ser or not self.ser.is_open:
                    logger.error("Serial port not open")
                    return False
                    
                # Clear input buffer before sending
                self.ser.reset_input_buffer()
                self.ser.write(command)
                time.sleep(1)  # Give more time for response
                response = self.ser.read(500).decode('utf-8', errors='ignore')
                logger.debug(f"Command: {command.decode('utf-8', errors='ignore').strip()}")
                logger.debug(f"Response: {response}")
                
                if 'OK' in response:
                    logger.info(f"{description}: Success")
                    return True
                elif 'ERROR' in response:
                    logger.error(f"{description}: Failed - {response}")
                    return False
                elif not response:
                    logger.warning(f"{description}: No response")
                    return False
                return True
            except Exception as e:
                logger.error(f"Error sending command {description}: {e}")
                return False
    
    def send_sms(self, number, message):
        with self.lock:
            for attempt in range(MAX_RETRIES):
                try:
                    self.ser.write(f'AT+CMGS="{number}"\r'.encode())
                    time.sleep(2)
                    response = self.ser.read(100).decode('utf-8', errors='ignore')
                    
                    if '>' in response:
                        self.ser.write(f'{message}\x1A'.encode())
                        time.sleep(5)
                        response = self.ser.read(200).decode('utf-8', errors='ignore')
                        
                        if 'OK' in response or '+CMGS' in response:
                            logger.info(f"SMS sent successfully to {number}")
                            return True
                    
                    logger.warning(f"SMS send attempt {attempt + 1} failed")
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error sending SMS: {e}")
                    
            return False
    
    def close(self):
        if self.ser:
            self.ser.close()

    

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
        f"Bike Speed Report\n"
        f"Time: {timestamp}\n"
        f"Current: {speed_kph:.2f} km/h\n"
        f"Average: {avg_speed:.2f} km/h\n"
        f"Pulses: {pulses}"
    )

def main():
    logger.info("Starting enhanced bike speedometer...")
    logger.info(f"Configuration:")
    logger.info(f"  Hall Sensor Pin: {HALL_SENSOR_PIN}")
    logger.info(f"  Wheel Circumference: {CIRCUMFERENCE}m")
    logger.info(f"  SMS Interval: {SMS_INTERVAL}s")
    logger.info(f"  Serial Port: {SERIAL_PORT}")
    logger.info(f"  Baud Rate: {BAUD_RATE}")
    
    # Test GPIO first
    try:
        test_state = GPIO.input(HALL_SENSOR_PIN)
        logger.info(f"Initial GPIO pin state: {test_state}")
    except Exception as e:
        logger.error(f"Failed to read GPIO pin: {e}")
        return
    
    modem = ModemManager(SERIAL_PORT, BAUD_RATE)
    sensor = SpeedSensor(HALL_SENSOR_PIN, CIRCUMFERENCE)
    
    # Make modem optional - continue even if it fails
    modem_available = False
    try:
        if modem.connect():
            modem_available = modem.init_modem()
            if modem_available:
                logger.info("Modem connected and initialized")
            else:
                logger.warning("Modem connected but initialization failed")
        else:
            logger.warning("Could not connect to modem - continuing without SMS capability")
    except Exception as e:
        logger.warning(f"Modem setup failed: {e} - continuing without SMS")
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    try:
        while True:
            logger.info(f"Counting wheel pulses for {SMS_INTERVAL} seconds...")
            
            last_state = GPIO.input(HALL_SENSOR_PIN)
            start_time = time.time()
            
            pulse_check_count = 0
            while (time.time() - start_time) < SMS_INTERVAL:
                try:
                    current_state = GPIO.input(HALL_SENSOR_PIN)
                    sensor.detect_pulse(last_state, current_state)
                    last_state = current_state
                    pulse_check_count += 1
                    time.sleep(0.001)
                except Exception as e:
                    logger.error(f"Error reading GPIO: {e}")
                    break
            
            logger.debug(f"Checked GPIO {pulse_check_count} times in {SMS_INTERVAL} seconds")
            
            elapsed_time = time.time() - start_time
            speed_kph, avg_speed, pulses = sensor.calculate_speed(elapsed_time)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            logger.info(f"Speed: {speed_kph:.2f} km/h (avg: {avg_speed:.2f}), Pulses: {pulses}")
            
            if modem_available:
                msg = format_sms_message(speed_kph, avg_speed, pulses, timestamp)
                
                if modem.send_sms(SMS_PHONE_NUMBER, msg):
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    logger.warning(f"SMS send failed ({consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error("Too many consecutive SMS failures. Reinitializing modem...")
                        modem.close()
                        time.sleep(2)
                        
                        if modem.connect() and modem.init_modem():
                            consecutive_failures = 0
                            logger.info("Modem reinitialized successfully")
                        else:
                            modem_available = False
                            logger.error("Failed to reinitialize modem. Continuing without SMS.")
            
    except KeyboardInterrupt:
        logger.info("\nStopping program...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        try:
            GPIO.cleanup()
            logger.info("GPIO cleanup complete")
        except:
            pass
        try:
            if modem:
                modem.close()
                logger.info("Modem closed")
        except:
            pass
        logger.info("Program terminated")

if __name__ == "__main__":
    main()
