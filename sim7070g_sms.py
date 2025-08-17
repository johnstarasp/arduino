#!/usr/bin/env python3
"""
Optimized SMS Script for SIM7070G on Raspberry Pi
Handles power control and robust SMS sending
"""

import serial
import time
import sys
import os

def init_power():
    """Initialize GPIO power control for SIM7070G"""
    try:
        import RPi.GPIO as GPIO
        PWRKEY = 4  # BCM GPIO 4 (WiringPi P7)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PWRKEY, GPIO.OUT)
        
        print("Power cycling SIM7070G module...")
        GPIO.output(PWRKEY, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(PWRKEY, GPIO.LOW)
        time.sleep(2)
        GPIO.output(PWRKEY, GPIO.HIGH)
        
        print("Waiting for module initialization...")
        time.sleep(8)
        return GPIO
    except Exception as e:
        print(f"GPIO control failed: {e}")
        return None

def find_module():
    """Find and connect to the SIM7070G module"""
    configs = [
        ('/dev/ttyS0', 115200),
        ('/dev/ttyS0', 57600),
        ('/dev/serial0', 115200),
        ('/dev/serial0', 57600),
    ]
    
    for port, baud in configs:
        if not os.path.exists(port):
            continue
            
        try:
            print(f"Testing {port} at {baud} baud...")
            ser = serial.Serial(port, baud, timeout=3)
            time.sleep(1)
            
            # Test AT command
            ser.reset_input_buffer()
            ser.write(b'AT\r\n')
            time.sleep(1)
            
            response = ser.read(ser.in_waiting or 100)
            if b'OK' in response or b'AT' in response:
                print(f"✓ Module found at {port} @ {baud} baud")
                return ser
                
            ser.close()
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def send_at(ser, cmd, wait=2):
    """Send AT command and return response"""
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(wait)
    
    if ser.in_waiting:
        return ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    return ""

def send_sms(ser, phone, message):
    """Send SMS message"""
    print(f"\nSending SMS to {phone}")
    print(f"Message: {message}")
    
    # Set text mode
    resp = send_at(ser, "AT+CMGF=1", 1)
    if "OK" not in resp:
        print(f"Text mode failed: {resp}")
        return False
    
    # Send SMS command
    ser.reset_input_buffer()
    ser.write(f'AT+CMGS="{phone}"\r'.encode())
    
    # Wait for prompt
    time.sleep(3)
    prompt = ser.read(ser.in_waiting or 100)
    
    if b'>' in prompt or len(prompt) == 0:
        print("Sending message...")
        ser.write(message.encode())
        ser.write(b'\x1A')  # Ctrl+Z
        
        # Wait for confirmation
        time.sleep(15)
        response = ser.read(ser.in_waiting or 500).decode('utf-8', errors='ignore')
        
        if "+CMGS" in response or "OK" in response:
            print("✓ SMS SENT SUCCESSFULLY!")
            return True
        else:
            print(f"SMS failed: {response}")
    else:
        print(f"No SMS prompt: {prompt}")
    
    return False

def main():
    print("SIM7070G SMS Sender")
    print("=" * 50)
    
    # Initialize power control
    gpio = None
    if os.geteuid() == 0:
        gpio = init_power()
    else:
        print("Run with sudo for power control")
    
    # Find module
    ser = find_module()
    if not ser:
        print("\n✗ Module not found!")
        print("Try:")
        print("1. Check physical connections")
        print("2. Press power button manually")
        print("3. Check UART is enabled")
        sys.exit(1)
    
    try:
        # Basic initialization
        print("\nInitializing module...")
        send_at(ser, "ATE0", 1)  # Disable echo
        
        # Check status
        resp = send_at(ser, "AT+CPIN?", 2)
        print(f"SIM: {resp.strip()}")
        
        resp = send_at(ser, "AT+CSQ", 1)
        print(f"Signal: {resp.strip()}")
        
        # Send test SMS
        phone = "+306976518415"
        message = "Test SMS from Raspberry Pi SIM7070G"
        
        success = send_sms(ser, phone, message)
        
        if success:
            print("\n" + "=" * 50)
            print("🎉 SMS SENT SUCCESSFULLY! 🎉")
            print("=" * 50)
        else:
            print("\n❌ SMS FAILED")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ser.close()
        if gpio:
            gpio.cleanup()
        print("Done!")

if __name__ == "__main__":
    main()