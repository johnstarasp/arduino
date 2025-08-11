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
SERIAL_PORT = "/dev/serial0"  # or "/dev/ttyS0" depending on your setup
BAUD_RATE = 115200
SMS_INTERVAL = 10  # seconds
DEBOUNCE_TIME = 0.05  # seconds
MAX_RETRIES = 3
SPEED_HISTORY_SIZE = 10

# -----------------------------
# SETUP
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

class ModemManager:
    def __init__(self, serial_port, baud_rate):
        self.ser = None
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.lock = threading.Lock()
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            time.sleep(2)
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port: {e}")
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
                self.ser.write(command)
                time.sleep(0.5)
                response = self.ser.read(100).decode('utf-8', errors='ignore')
                if 'OK' in response:
                    logger.info(f"{description}: Success")
                    return True
                elif 'ERROR' in response:
                    logger.error(f"{description}: Failed - {response}")
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
    
    modem = ModemManager(SERIAL_PORT, BAUD_RATE)
    sensor = SpeedSensor(HALL_SENSOR_PIN, CIRCUMFERENCE)
    
    if not modem.connect():
        logger.error("Failed to connect to modem. Exiting.")
        return
    
    if not modem.init_modem():
        logger.error("Failed to initialize modem. Continuing without SMS...")
        modem_available = False
    else:
        modem_available = True
        logger.info("Modem initialized successfully")
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    try:
        while True:
            logger.info(f"Counting wheel pulses for {SMS_INTERVAL} seconds...")
            
            last_state = GPIO.input(HALL_SENSOR_PIN)
            start_time = time.time()
            
            while (time.time() - start_time) < SMS_INTERVAL:
                current_state = GPIO.input(HALL_SENSOR_PIN)
                sensor.detect_pulse(last_state, current_state)
                last_state = current_state
                time.sleep(0.001)
            
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
    finally:
        GPIO.cleanup()
        modem.close()
        logger.info("Cleanup complete")

if __name__ == "__main__":
    main()
