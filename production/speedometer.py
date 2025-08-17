#!/usr/bin/env python3
"""
Production Speedometer with SMS Updates (Clean ASCII Version)
Waveshare SIM7070G HAT on Raspberry Pi

Features:
- Hall sensor speed monitoring on GPIO 17
- SMS updates every 30 seconds
- Automatic SIM7070G power control
- SMS service center auto-configuration
- Robust error handling and recovery
- Plain ASCII text only (no emojis)
"""

import serial
import time
import sys
from datetime import datetime

class Speedometer:
    def __init__(self):
        # Configuration
        self.hall_pin = 17                    # GPIO pin for hall sensor
        self.wheel_circumference = 2.1        # meters (adjust for your wheel)
        self.phone_number = "+306980531698"   # SMS recipient
        self.update_interval = 30             # seconds between SMS updates
        
        # Internal state
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.current_speed = 0.0
        self.ser = None
        self.running = True
        self.last_pin_state = 1
        self.GPIO = None
        
    def init_gpio(self):
        """Initialize GPIO for hall sensor and SIM module power"""
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
            GPIO.setup(4, GPIO.OUT)  # SIM power control
            
            print(f"[OK] GPIO initialized - Hall sensor on pin {self.hall_pin}")
            return True
        except Exception as e:
            print(f"[ERROR] GPIO init failed: {e}")
            return False
    
    def init_sim_module(self):
        """Initialize SIM7070G module with SMS fix"""
        try:
            print("[POWER] Powering SIM7070G module...")
            
            # Power cycle sequence
            self.GPIO.output(4, self.GPIO.LOW)
            time.sleep(3)
            self.GPIO.output(4, self.GPIO.HIGH)
            time.sleep(3)
            self.GPIO.output(4, self.GPIO.LOW)
            
            print("[WAIT] Waiting 15 seconds for module boot...")
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
                if b'OK' in response:
                    print("[OK] SIM module responding")
                    break
            else:
                print("[ERROR] SIM module not responding")
                return False
            
            # CRITICAL: Set SMS Service Center (fixes CMS ERROR 500)
            print("[CONFIG] Configuring SMS service center...")
            self.ser.write(b'AT+CSCA="+3097100000"\r\n')
            time.sleep(2)
            resp = self.ser.read(100)
            if b'OK' in resp:
                print("[OK] SMS service center configured (+3097100000)")
            else:
                print(f"[WARNING] SMSC warning: {resp}")
            
            # Configure SMS settings
            commands = [
                (b"ATE0\r\n", "Disable echo"),
                (b'AT+CMEE=2\r\n', "Enable verbose errors"),
                (b'AT+CMGF=1\r\n', "Set SMS text mode"),
                (b'AT+CPMS="SM","SM","SM"\r\n', "Set SMS storage"),
            ]
            
            for cmd, desc in commands:
                self.ser.write(cmd)
                time.sleep(1)
                self.ser.read(200)  # Clear response
            
            print("[OK] SIM module ready for SMS")
            return True
            
        except Exception as e:
            print(f"[ERROR] SIM init failed: {e}")
            return False
    
    def send_sms(self, message):
        """Send SMS with retry logic"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                if not self.ser or not self.ser.is_open:
                    print("[ERROR] SIM module not connected")
                    return False
                
                print(f"[SMS] Sending SMS (attempt {attempt + 1}): {message}")
                
                # Ensure text mode
                self.ser.reset_input_buffer()
                self.ser.write(b"AT+CMGF=1\r\n")
                time.sleep(2)
                self.ser.read(100)
                
                # Send SMS command
                self.ser.reset_input_buffer()
                self.ser.write(f'AT+CMGS="{self.phone_number}"\r'.encode())
                
                # Wait for prompt
                time.sleep(3)
                prompt = self.ser.read(100)
                
                if b'>' in prompt:
                    # Send message text
                    self.ser.write(message.encode())
                    time.sleep(1)
                    self.ser.write(b'\x1A')  # Ctrl+Z
                    
                    # Wait for confirmation
                    time.sleep(15)
                    response = self.ser.read(300).decode('utf-8', errors='ignore')
                    
                    if "+CMGS" in response:
                        print("[OK] SMS sent successfully")
                        return True
                    elif "CMS ERROR" in response:
                        error = response.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in response else "unknown"
                        print(f"[ERROR] CMS ERROR {error}")
                        if error == "500":
                            print("   SMS service center may need reconfiguration")
                    else:
                        print(f"[ERROR] SMS failed: {response}")
                else:
                    print("[ERROR] No SMS prompt received")
                    
            except Exception as e:
                print(f"[ERROR] SMS error (attempt {attempt + 1}): {e}")
            
            if attempt < max_attempts - 1:
                print("[WAIT] Retrying in 5 seconds...")
                time.sleep(5)
        
        print("[ERROR] All SMS attempts failed")
        return False
    
    def check_hall_sensor(self):
        """Poll hall sensor for state changes (falling edge detection)"""
        try:
            current_state = self.GPIO.input(self.hall_pin)
            
            # Detect falling edge (magnet passing sensor)
            if self.last_pin_state == 1 and current_state == 0:
                current_time = time.time()
                
                if self.last_pulse_time > 0:
                    time_diff = current_time - self.last_pulse_time
                    if time_diff > 0.1:  # Debounce: ignore pulses < 100ms apart
                        # Calculate instantaneous speed
                        speed_ms = self.wheel_circumference / time_diff  # m/s
                        self.current_speed = speed_ms * 3.6  # Convert to km/h
                        print(f"[PULSE] Speed: {self.current_speed:.1f} km/h")
                
                self.last_pulse_time = current_time
                self.pulse_count += 1
            
            self.last_pin_state = current_state
        except Exception as e:
            print(f"[ERROR] Hall sensor error: {e}")
    
    def monitor_speed(self, duration):
        """Monitor speed for specified duration using polling"""
        start_count = self.pulse_count
        start_time = time.time()
        end_time = start_time + duration
        
        print(f"[MONITOR] Monitoring speed for {duration} seconds...")
        
        while time.time() < end_time and self.running:
            self.check_hall_sensor()
            time.sleep(0.01)  # Poll every 10ms
        
        pulses = self.pulse_count - start_count
        time_elapsed = time.time() - start_time
        
        if pulses > 0:
            distance = pulses * self.wheel_circumference
            avg_speed = (distance / time_elapsed) * 3.6  # km/h
            return avg_speed, pulses
        else:
            return 0.0, 0
    
    def run(self):
        """Main speedometer application"""
        print("====== SPEEDOMETER WITH SMS UPDATES ======")
        print("=" * 50)
        print(f"Phone: {self.phone_number}")
        print(f"Wheel circumference: {self.wheel_circumference}m")
        print(f"Hall sensor: GPIO {self.hall_pin}")
        print(f"Update interval: {self.update_interval}s")
        print("=" * 50)
        
        # Initialize hardware
        if not self.init_gpio():
            print("[ERROR] Failed to initialize GPIO")
            return
        
        if not self.init_sim_module():
            print("[ERROR] Failed to initialize SIM module")
            return
        
        print("\n[SUCCESS] ALL SYSTEMS READY!")
        print("[INFO] Start riding to generate speed data...")
        print("[TEST] To test: short GPIO 17 to ground")
        print("[STOP] Press Ctrl+C to stop")
        print()
        
        # Send startup notification
        startup_msg = f"Speedometer started at {datetime.now().strftime('%H:%M:%S')} - Ready to track!"
        success = self.send_sms(startup_msg)
        if success:
            print("[OK] Startup notification sent")
        else:
            print("[WARNING] Startup SMS failed - continuing anyway")
        
        # Main monitoring loop
        cycle = 0
        try:
            while self.running:
                cycle += 1
                print(f"\n===== Monitoring Cycle {cycle} =====")
                
                # Monitor speed for specified interval
                avg_speed, pulses = self.monitor_speed(self.update_interval)
                
                # Create status message (NO EMOJIS!)
                timestamp = datetime.now().strftime('%H:%M:%S')
                if pulses > 0:
                    message = f"Speed: {avg_speed:.1f} km/h ({pulses} pulses) at {timestamp}"
                else:
                    pin_state = self.GPIO.input(self.hall_pin)
                    message = f"Stationary at {timestamp} (sensor: {pin_state})"
                
                # Send SMS update
                success = self.send_sms(message)
                if not success:
                    print("[WARNING] SMS failed - continuing monitoring...")
                
                # Display current status
                print(f"[STATUS] Total pulses: {self.pulse_count}")
                print(f"[STATUS] Current speed: {self.current_speed:.1f} km/h")
                print(f"[STATUS] Sensor state: {self.GPIO.input(self.hall_pin)}")
                
        except KeyboardInterrupt:
            print("\n[STOP] Stopping speedometer...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Send shutdown notification
            if self.ser and self.ser.is_open:
                shutdown_msg = f"Speedometer stopped at {datetime.now().strftime('%H:%M:%S')}"
                print("[SMS] Sending shutdown notification...")
                
                # Quick SMS without retry logic
                self.ser.reset_input_buffer()
                self.ser.write(b"AT+CMGF=1\r\n")
                time.sleep(1)
                self.ser.read(100)
                
                self.ser.write(f'AT+CMGS="{self.phone_number}"\r'.encode())
                time.sleep(2)
                if b'>' in self.ser.read(100):
                    self.ser.write(shutdown_msg.encode())
                    self.ser.write(b'\x1A')
                    time.sleep(5)
                
                self.ser.close()
            
            if self.GPIO:
                self.GPIO.cleanup()
            
            print("[OK] Cleanup complete")
        except:
            pass

def main():
    """Application entry point"""
    speedometer = Speedometer()
    speedometer.run()

if __name__ == "__main__":
    main()