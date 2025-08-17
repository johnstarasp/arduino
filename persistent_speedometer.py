#!/usr/bin/env python3
"""
Persistent Bike Speedometer - Keeps trying until it works
"""
import serial
import time
import sys
from datetime import datetime

class PersistentSpeedometer:
    def __init__(self):
        self.hall_pin = 17
        self.wheel_circumference = 2.1
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.current_speed = 0.0
        self.ser = None
        self.phone_number = "+306972290333"
        self.running = True
        self.last_pin_state = 1
        self.GPIO = None
        
    def init_gpio(self):
        """Initialize GPIO with retry logic"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                import RPi.GPIO as GPIO
                self.GPIO = GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Clean up any existing setup
                try:
                    GPIO.cleanup()
                except:
                    pass
                
                # Setup pins
                GPIO.setup(self.hall_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(4, GPIO.OUT)
                
                print(f"✓ GPIO initialized (attempt {attempt+1}) - Hall sensor on pin {self.hall_pin}")
                return True
                
            except Exception as e:
                print(f"✗ GPIO init attempt {attempt+1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                
        return False
    
    def init_sim_module(self):
        """Initialize SIM module with retry logic"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"\n--- SIM Init Attempt {attempt+1} ---")
                
                # Power cycle
                print("Power cycling SIM module...")
                self.GPIO.output(4, self.GPIO.LOW)
                time.sleep(3)
                self.GPIO.output(4, self.GPIO.HIGH)
                time.sleep(3)
                self.GPIO.output(4, self.GPIO.LOW)
                
                print("Waiting 20 seconds for boot...")
                for i in range(20):
                    print(f"Boot wait: {i+1}/20", end='\r')
                    time.sleep(1)
                print()
                
                # Try to connect
                if self.ser:
                    self.ser.close()
                
                self.ser = serial.Serial('/dev/serial0', 57600, timeout=5)
                time.sleep(2)
                print("Serial connection established")
                
                # Test AT commands
                print("Testing AT communication...")
                for at_attempt in range(10):
                    self.ser.reset_input_buffer()
                    self.ser.write(b'AT\r\n')
                    time.sleep(2)
                    
                    response = self.ser.read(self.ser.in_waiting or 100)
                    print(f"AT attempt {at_attempt+1}: {response}")
                    
                    if b'OK' in response or b'AT' in response:
                        print("✓ SIM module responding!")
                        
                        # Disable echo
                        self.ser.write(b"ATE0\r\n")
                        time.sleep(1)
                        self.ser.read(self.ser.in_waiting or 100)
                        
                        print("✓ SIM module ready")
                        return True
                
                print(f"✗ SIM module not responding on attempt {attempt+1}")
                
            except Exception as e:
                print(f"✗ SIM init attempt {attempt+1} failed: {e}")
            
            if attempt < max_attempts - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
        
        return False
    
    def send_sms(self, message):
        """Send SMS with retry logic"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                print(f"SMS attempt {attempt+1}: {message}")
                
                # Set text mode
                self.ser.reset_input_buffer()
                self.ser.write(b"AT+CMGF=1\r\n")
                time.sleep(2)
                resp = self.ser.read(self.ser.in_waiting or 100)
                print(f"Text mode: {resp}")
                
                # Send SMS command
                self.ser.reset_input_buffer()
                self.ser.write(f'AT+CMGS="{self.phone_number}"\r'.encode())
                time.sleep(3)
                prompt = self.ser.read(self.ser.in_waiting or 100)
                print(f"Prompt: {prompt}")
                
                # Send message
                self.ser.write(message.encode())
                time.sleep(1)
                self.ser.write(b'\x1A')
                
                # Wait for response
                print("Waiting for SMS confirmation...")
                time.sleep(15)
                response = self.ser.read(self.ser.in_waiting or 300)
                print(f"SMS response: {response}")
                
                if b'+CMGS' in response or b'OK' in response:
                    print("✓ SMS sent successfully!")
                    return True
                else:
                    print(f"✗ SMS failed (attempt {attempt+1})")
                    
            except Exception as e:
                print(f"SMS error (attempt {attempt+1}): {e}")
            
            if attempt < max_attempts - 1:
                print("Retrying SMS in 3 seconds...")
                time.sleep(3)
        
        return False
    
    def check_hall_sensor(self):
        """Poll hall sensor"""
        try:
            current_state = self.GPIO.input(self.hall_pin)
            
            if self.last_pin_state == 1 and current_state == 0:
                current_time = time.time()
                if self.last_pulse_time > 0:
                    time_diff = current_time - self.last_pulse_time
                    if time_diff > 0.1:
                        speed_ms = self.wheel_circumference / time_diff
                        self.current_speed = speed_ms * 3.6
                        print(f"PULSE! Speed: {self.current_speed:.1f} km/h")
                
                self.last_pulse_time = current_time
                self.pulse_count += 1
            
            self.last_pin_state = current_state
        except Exception as e:
            print(f"Hall sensor error: {e}")
    
    def monitor_speed(self, duration=30):
        """Monitor speed for specified duration"""
        start_count = self.pulse_count
        start_time = time.time()
        end_time = start_time + duration
        
        print(f"Monitoring for {duration} seconds...")
        
        while time.time() < end_time and self.running:
            self.check_hall_sensor()
            time.sleep(0.01)
        
        pulses = self.pulse_count - start_count
        time_elapsed = time.time() - start_time
        
        if pulses > 0:
            distance = pulses * self.wheel_circumference
            avg_speed = (distance / time_elapsed) * 3.6
            return avg_speed, pulses
        else:
            return 0.0, 0
    
    def run(self):
        """Main loop - keeps trying until everything works"""
        print("=== PERSISTENT BIKE SPEEDOMETER ===")
        print(f"Phone: {self.phone_number}")
        print(f"Wheel: {self.wheel_circumference}m")
        print(f"Hall sensor: GPIO {self.hall_pin}")
        
        # Initialize GPIO
        while not self.init_gpio():
            print("Retrying GPIO init in 5 seconds...")
            time.sleep(5)
        
        # Initialize SIM module
        while not self.init_sim_module():
            print("Retrying SIM init in 10 seconds...")
            time.sleep(10)
        
        print("\n🎉 ALL SYSTEMS READY! 🎉")
        print("Speedometer is now running...")
        print("To test: short GPIO 17 to ground")
        print("Press Ctrl+C to stop")
        
        # Send startup message
        startup_msg = f"Speedometer started at {datetime.now().strftime('%H:%M:%S')} - All systems working!"
        while not self.send_sms(startup_msg):
            print("Retrying startup SMS in 5 seconds...")
            time.sleep(5)
        
        # Main monitoring loop
        cycle = 0
        try:
            while self.running:
                cycle += 1
                print(f"\n=== Cycle {cycle} ===")
                
                # Monitor speed
                avg_speed, pulses = self.monitor_speed(30)
                
                # Create message
                timestamp = datetime.now().strftime('%H:%M:%S')
                if pulses > 0:
                    message = f"Speed: {avg_speed:.1f} km/h ({pulses} pulses) at {timestamp}"
                else:
                    pin_state = self.GPIO.input(self.hall_pin)
                    message = f"Stationary at {timestamp} (pin: {pin_state})"
                
                # Send SMS (retry until successful)
                while not self.send_sms(message) and self.running:
                    print("SMS failed, retrying in 10 seconds...")
                    time.sleep(10)
                
                print(f"Total pulses: {self.pulse_count}")
                print(f"Current speed: {self.current_speed:.1f} km/h")
                
        except KeyboardInterrupt:
            print("\nStopping speedometer...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.ser:
                self.ser.close()
            if self.GPIO:
                self.GPIO.cleanup()
            print("Cleanup complete")
        except:
            pass

def main():
    speedometer = PersistentSpeedometer()
    speedometer.run()

if __name__ == "__main__":
    main()