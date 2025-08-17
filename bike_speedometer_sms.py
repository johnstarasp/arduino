#!/usr/bin/env python3
"""
Bike Speedometer with SMS Updates
Reads hall sensor and sends speed via SMS every 30 seconds
"""
import serial
import time
import sys
import threading
from datetime import datetime

class BikeSpeedometer:
    def __init__(self):
        self.hall_pin = 18  # GPIO pin for hall sensor
        self.wheel_circumference = 2.1  # meters (adjust for your wheel)
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.current_speed = 0.0
        self.ser = None
        self.phone_number = "+306972290333"  # Updated phone number
        self.running = True
        
    def init_gpio(self):
        """Initialize GPIO for hall sensor and SIM module power"""
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Hall sensor pin (with pull-up resistor)
            GPIO.setup(self.hall_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.hall_pin, GPIO.FALLING, 
                                callback=self.hall_pulse, bouncetime=50)
            
            # SIM module power pin
            GPIO.setup(4, GPIO.OUT)
            print("GPIO initialized")
            return True
        except Exception as e:
            print(f"GPIO init failed: {e}")
            return False
    
    def hall_pulse(self, channel):
        """Hall sensor pulse callback"""
        current_time = time.time()
        
        if self.last_pulse_time > 0:
            time_diff = current_time - self.last_pulse_time
            if time_diff > 0.1:  # Debounce: ignore pulses < 100ms apart
                # Calculate speed: distance/time = circumference/time_diff
                speed_ms = self.wheel_circumference / time_diff  # m/s
                self.current_speed = speed_ms * 3.6  # Convert to km/h
        
        self.last_pulse_time = current_time
        self.pulse_count += 1
    
    def get_average_speed(self, duration=30):
        """Calculate average speed over duration seconds"""
        start_count = self.pulse_count
        start_time = time.time()
        
        time.sleep(duration)
        
        end_count = self.pulse_count
        end_time = time.time()
        
        pulses = end_count - start_count
        time_elapsed = end_time - start_time
        
        if pulses > 0 and time_elapsed > 0:
            distance = pulses * self.wheel_circumference
            avg_speed = (distance / time_elapsed) * 3.6  # km/h
            return avg_speed, pulses
        else:
            return 0.0, 0
    
    def init_sim_module(self):
        """Initialize SIM7070G module"""
        try:
            print("Powering SIM module...")
            self.GPIO.output(4, GPIO.LOW)
            time.sleep(3)
            self.GPIO.output(4, GPIO.HIGH)
            time.sleep(3)
            self.GPIO.output(4, GPIO.LOW)
            
            print("Waiting for module boot...")
            time.sleep(15)
            
            # Connect to module
            self.ser = serial.Serial('/dev/serial0', 57600, timeout=5)
            time.sleep(2)
            
            # Test communication
            for attempt in range(5):
                self.ser.reset_input_buffer()
                self.ser.write(b'AT\r\n')
                time.sleep(2)
                
                response = self.ser.read(self.ser.in_waiting or 100)
                if b'OK' in response or b'AT' in response:
                    print("✓ SIM module ready")
                    
                    # Initialize SMS
                    self.ser.write(b"ATE0\r\n")
                    time.sleep(1)
                    self.ser.read(self.ser.in_waiting or 100)
                    
                    return True
            
            print("✗ SIM module not responding")
            return False
            
        except Exception as e:
            print(f"SIM init failed: {e}")
            return False
    
    def send_sms(self, message):
        """Send SMS using working method"""
        try:
            if not self.ser or not self.ser.is_open:
                print("SIM module not connected")
                return False
            
            print(f"Sending SMS: {message}")
            
            # Set text mode
            self.ser.reset_input_buffer()
            self.ser.write(b"AT+CMGF=1\r\n")
            time.sleep(2)
            self.ser.read(self.ser.in_waiting or 100)
            
            # Send SMS command
            self.ser.reset_input_buffer()
            self.ser.write(f'AT+CMGS="{self.phone_number}"\r'.encode())
            
            # Wait for prompt
            time.sleep(3)
            self.ser.read(self.ser.in_waiting or 100)
            
            # Send message
            self.ser.write(message.encode())
            time.sleep(1)
            self.ser.write(b'\x1A')  # Ctrl+Z
            
            # Wait for confirmation
            time.sleep(10)
            response = self.ser.read(self.ser.in_waiting or 200)
            
            if b'+CMGS' in response or b'OK' in response:
                print("✓ SMS sent successfully")
                return True
            else:
                print(f"✗ SMS failed: {response}")
                return False
                
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    def run(self):
        """Main monitoring loop"""
        print("=== BIKE SPEEDOMETER WITH SMS ===")
        print(f"Phone number: {self.phone_number}")
        print(f"Wheel circumference: {self.wheel_circumference}m")
        
        # Initialize hardware
        if not self.init_gpio():
            print("Failed to initialize GPIO")
            return
        
        if not self.init_sim_module():
            print("Failed to initialize SIM module")
            return
        
        print("\n✓ All systems ready!")
        print("Start riding to generate speed data...")
        print("Press Ctrl+C to stop")
        
        # Send startup message
        startup_msg = f"Bike speedometer started at {datetime.now().strftime('%H:%M:%S')}"
        self.send_sms(startup_msg)
        
        try:
            cycle_count = 0
            while self.running:
                cycle_count += 1
                print(f"\n--- Monitoring Cycle {cycle_count} ---")
                
                # Monitor for 30 seconds
                avg_speed, pulse_count = self.get_average_speed(30)
                
                # Prepare SMS message
                timestamp = datetime.now().strftime('%H:%M:%S')
                if pulse_count > 0:
                    message = f"Speed: {avg_speed:.1f} km/h ({pulse_count} pulses) at {timestamp}"
                else:
                    message = f"Stationary (0 km/h) at {timestamp}"
                
                print(f"Sending: {message}")
                
                # Send SMS
                success = self.send_sms(message)
                if not success:
                    print("SMS send failed, continuing...")
                
                # Show current status
                print(f"Total pulses: {self.pulse_count}")
                print(f"Current speed: {self.current_speed:.1f} km/h")
                
        except KeyboardInterrupt:
            print("\nStopping speedometer...")
            self.running = False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.ser:
                self.ser.close()
            self.GPIO.cleanup()
            print("Cleanup complete")
        except:
            pass

def main():
    speedometer = BikeSpeedometer()
    speedometer.run()

if __name__ == "__main__":
    main()