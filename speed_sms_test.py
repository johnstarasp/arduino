#!/usr/bin/env python3
"""
Simple test for speed SMS functionality
Simulates hall sensor readings and sends test SMS every 30 seconds
"""
import serial
import time
import sys
from datetime import datetime

class SpeedSMSTest:
    def __init__(self):
        self.ser = None
        self.phone_number = "+306972290333"
        self.test_cycle = 0
        
    def init_sim_module(self):
        """Initialize SIM module using working method"""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(4, GPIO.OUT)
            
            print("Powering SIM module...")
            GPIO.output(4, GPIO.LOW)
            time.sleep(3)
            GPIO.output(4, GPIO.HIGH)
            time.sleep(3)
            GPIO.output(4, GPIO.LOW)
            time.sleep(15)
            
            self.ser = serial.Serial('/dev/serial0', 57600, timeout=5)
            time.sleep(2)
            
            # Test AT
            for attempt in range(5):
                self.ser.reset_input_buffer()
                self.ser.write(b'AT\r\n')
                time.sleep(2)
                
                response = self.ser.read(self.ser.in_waiting or 100)
                if b'OK' in response:
                    print("✓ SIM module ready")
                    self.ser.write(b"ATE0\r\n")
                    time.sleep(1)
                    self.ser.read(self.ser.in_waiting or 100)
                    return True
            
            return False
        except Exception as e:
            print(f"Init failed: {e}")
            return False
    
    def send_sms(self, message):
        """Send SMS using proven working method"""
        try:
            print(f"Sending: {message}")
            
            # Set text mode
            self.ser.reset_input_buffer()
            self.ser.write(b"AT+CMGF=1\r\n")
            time.sleep(2)
            self.ser.read(self.ser.in_waiting or 100)
            
            # Send command
            self.ser.reset_input_buffer()
            self.ser.write(f'AT+CMGS="{self.phone_number}"\r'.encode())
            time.sleep(3)
            self.ser.read(self.ser.in_waiting or 100)
            
            # Send message
            self.ser.write(message.encode())
            time.sleep(1)
            self.ser.write(b'\x1A')
            
            # Wait for response
            time.sleep(10)
            response = self.ser.read(self.ser.in_waiting or 200)
            
            if b'+CMGS' in response or b'OK' in response:
                print("✓ SMS sent")
                return True
            else:
                print(f"✗ Failed: {response}")
                return False
                
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    def simulate_speed_reading(self):
        """Simulate speed calculation"""
        import random
        # Simulate different speeds
        speeds = [0, 15.5, 23.2, 18.7, 0, 12.1, 25.8]
        return random.choice(speeds)
    
    def run_test(self):
        """Run the speed SMS test"""
        print("=== SPEED SMS TEST ===")
        
        if not self.init_sim_module():
            print("Failed to initialize SIM module")
            return
        
        print("Starting speed monitoring test...")
        print("Will send SMS every 30 seconds")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                self.test_cycle += 1
                
                # Simulate speed reading
                speed = self.simulate_speed_reading()
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                if speed > 0:
                    message = f"Bike Speed: {speed:.1f} km/h at {timestamp} (Test #{self.test_cycle})"
                else:
                    message = f"Bike stationary at {timestamp} (Test #{self.test_cycle})"
                
                success = self.send_sms(message)
                
                if success:
                    print(f"Test {self.test_cycle} completed successfully")
                else:
                    print(f"Test {self.test_cycle} failed")
                
                print("Waiting 30 seconds for next update...")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\nTest stopped by user")
        finally:
            if self.ser:
                self.ser.close()
            print("Test complete")

def main():
    test = SpeedSMSTest()
    test.run_test()

if __name__ == "__main__":
    main()