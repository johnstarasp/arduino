#!/usr/bin/env python3
"""
Bike Speedometer with SMS Updates - Fixed for CMS ERROR 500
Includes SMSC configuration for new SIM cards
"""
import serial
import time
import sys
from datetime import datetime

class FixedSpeedometer:
    def __init__(self):
        self.hall_pin = 17
        self.wheel_circumference = 2.1
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.current_speed = 0.0
        self.ser = None
        self.phone_number = "+306980531698"
        self.running = True
        self.last_pin_state = 1
        self.GPIO = None
        
    def init_gpio(self):
        """Initialize GPIO"""
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
            GPIO.setup(4, GPIO.OUT)  # SIM power pin
            
            print(f"✓ GPIO initialized - Hall sensor on pin {self.hall_pin}")
            return True
        except Exception as e:
            print(f"✗ GPIO init failed: {e}")
            return False
    
    def init_sim_module(self):
        """Initialize SIM module with CMS ERROR 500 fix"""
        try:
            print("Powering SIM module...")
            self.GPIO.output(4, self.GPIO.LOW)
            time.sleep(3)
            self.GPIO.output(4, self.GPIO.HIGH)
            time.sleep(3)
            self.GPIO.output(4, self.GPIO.LOW)
            
            print("Waiting 15 seconds for boot...")
            time.sleep(15)
            
            # Connect
            self.ser = serial.Serial('/dev/serial0', 57600, timeout=5)
            time.sleep(2)
            
            # Test communication
            for attempt in range(5):
                self.ser.reset_input_buffer()
                self.ser.write(b'AT\r\n')
                time.sleep(2)
                
                response = self.ser.read(self.ser.in_waiting or 100)
                if b'OK' in response:
                    print("✓ SIM module responding")
                    break
            else:
                print("✗ SIM module not responding")
                return False
            
            # CRITICAL FIX: Configure SMS Service Center for new SIM
            print("Configuring SMS service center...")
            self.ser.write(b'AT+CSCA="+306942000000"\r\n')
            time.sleep(2)
            resp = self.ser.read(100)
            if b'OK' in resp:
                print("✓ SMS service center configured")
            else:
                print(f"⚠️  SMSC warning: {resp}")
            
            # Configure SMS settings
            self.ser.write(b"ATE0\r\n")  # Disable echo
            time.sleep(1)
            self.ser.read(100)
            
            self.ser.write(b'AT+CMEE=2\r\n')  # Verbose errors
            time.sleep(1)
            self.ser.read(100)
            
            self.ser.write(b'AT+CMGF=1\r\n')  # Text mode
            time.sleep(1)
            self.ser.read(100)
            
            self.ser.write(b'AT+CPMS="SM","SM","SM"\r\n')  # SIM storage
            time.sleep(2)
            self.ser.read(200)
            
            print("✓ SIM module ready for SMS")
            return True
            
        except Exception as e:
            print(f"SIM init failed: {e}")
            return False
    
    def send_sms(self, message):
        """Send SMS using fixed method"""
        try:
            if not self.ser or not self.ser.is_open:
                print("SIM module not connected")
                return False
            
            print(f"Sending SMS: {message}")
            
            # Ensure text mode is set
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
                # Send message
                self.ser.write(message.encode())
                time.sleep(1)
                self.ser.write(b'\x1A')  # Ctrl+Z
                
                # Wait for confirmation
                time.sleep(15)
                response = self.ser.read(300).decode('utf-8', errors='ignore')
                
                if "+CMGS" in response:
                    print("✓ SMS sent successfully")
                    return True
                elif "CMS ERROR" in response:
                    error = response.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in response else "unknown"
                    print(f"✗ CMS ERROR {error}")
                    if error == "500":
                        print("   SIM may need more activation time")
                    return False
                else:
                    print(f"✗ SMS failed: {response}")
                    return False
            else:
                print(f"✗ No SMS prompt: {prompt}")
                return False
                
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    def check_hall_sensor(self):
        """Poll hall sensor for state changes"""
        try:
            current_state = self.GPIO.input(self.hall_pin)
            
            # Detect falling edge (high to low transition)
            if self.last_pin_state == 1 and current_state == 0:
                current_time = time.time()
                if self.last_pulse_time > 0:
                    time_diff = current_time - self.last_pulse_time
                    if time_diff > 0.1:  # Debounce
                        speed_ms = self.wheel_circumference / time_diff
                        self.current_speed = speed_ms * 3.6  # km/h
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
            time.sleep(0.01)  # Poll every 10ms
        
        pulses = self.pulse_count - start_count
        time_elapsed = time.time() - start_time
        
        if pulses > 0:
            distance = pulses * self.wheel_circumference
            avg_speed = (distance / time_elapsed) * 3.6
            return avg_speed, pulses
        else:
            return 0.0, 0
    
    def run(self):
        """Main speedometer loop"""
        print("=== BIKE SPEEDOMETER WITH SMS FIX ===")
        print(f"Phone: {self.phone_number}")
        print(f"Wheel: {self.wheel_circumference}m")
        print(f"Hall sensor: GPIO {self.hall_pin}")
        
        # Initialize systems
        if not self.init_gpio():
            print("Failed to initialize GPIO")
            return
        
        if not self.init_sim_module():
            print("Failed to initialize SIM module")
            return
        
        print("\n🎉 ALL SYSTEMS READY! 🎉")
        print("Start riding to generate speed data...")
        print("To test: short GPIO 17 to ground")
        print("Press Ctrl+C to stop")
        
        # Send startup message
        startup_msg = f"Speedometer started at {datetime.now().strftime('%H:%M:%S')} - SMS fix applied!"
        success = self.send_sms(startup_msg)
        if success:
            print("✓ Startup SMS sent")
        else:
            print("⚠️  Startup SMS failed - continuing anyway")
        
        # Main monitoring loop
        cycle = 0
        try:
            while self.running:
                cycle += 1
                print(f"\n=== Cycle {cycle} ===")
                
                # Monitor speed for 30 seconds
                avg_speed, pulses = self.monitor_speed(30)
                
                # Create message
                timestamp = datetime.now().strftime('%H:%M:%S')
                if pulses > 0:
                    message = f"Speed: {avg_speed:.1f} km/h ({pulses} pulses) at {timestamp}"
                else:
                    pin_state = self.GPIO.input(self.hall_pin)
                    message = f"Stationary at {timestamp} (pin: {pin_state})"
                
                # Send SMS
                success = self.send_sms(message)
                if not success:
                    print("SMS failed, continuing monitoring...")
                
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
    speedometer = FixedSpeedometer()
    speedometer.run()

if __name__ == "__main__":
    main()