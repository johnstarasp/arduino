#!/usr/bin/env python3
import serial
import time
import sys
import RPi.GPIO as GPIO

# GPIO pin for PWRKEY (WiringPi P7 = BCM GPIO 4)
PWRKEY_PIN = 4

def power_on_module():
    """Power on the SIM7070G module using PWRKEY"""
    print("Powering on SIM7070G module...")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PWRKEY_PIN, GPIO.OUT)
    
    # Toggle PWRKEY to power on
    GPIO.output(PWRKEY_PIN, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(PWRKEY_PIN, GPIO.LOW)
    time.sleep(2)
    GPIO.output(PWRKEY_PIN, GPIO.HIGH)
    time.sleep(3)
    
    print("Module powered on, waiting for initialization...")
    time.sleep(5)

def send_cmd(ser, cmd, wait=2):
    """Send AT command and return response"""
    ser.reset_input_buffer()
    ser.write((cmd + '\r\n').encode())
    time.sleep(wait)
    response = b''
    while ser.in_waiting:
        response += ser.read(ser.in_waiting)
    return response.decode('utf-8', errors='ignore')

def main():
    # Power on the module
    power_on_module()
    
    # Try to connect
    print("\nConnecting to SIM7070G...")
    ser = None
    
    # Try different baud rates
    for baud in [115200, 57600, 9600]:
        try:
            print(f"Trying {baud} baud...")
            ser = serial.Serial('/dev/ttyS0', baud, timeout=5)
            time.sleep(2)
            
            # Test connection
            resp = send_cmd(ser, "AT")
            if "OK" in resp or "AT" in resp:
                print(f"✓ Connected at {baud} baud")
                print(f"Response: {resp}")
                break
            ser.close()
        except Exception as e:
            print(f"Error at {baud}: {e}")
            if ser:
                ser.close()
    
    if not ser or not ser.is_open:
        print("Failed to connect! Module may need more time to boot.")
        GPIO.cleanup()
        sys.exit(1)
    
    # Configure module
    print("\n" + "="*40)
    print("Configuring module...")
    
    # Disable echo
    resp = send_cmd(ser, "ATE0")
    print(f"Echo off: {'OK' in resp}")
    
    # Check module info
    resp = send_cmd(ser, "AT+CGMM")
    print(f"Module: {resp.strip()}")
    
    # Check SIM status
    print("\nChecking SIM card...")
    for i in range(10):
        resp = send_cmd(ser, "AT+CPIN?")
        print(f"SIM Status: {resp.strip()}")
        if "READY" in resp:
            break
        time.sleep(2)
    
    # Check signal
    resp = send_cmd(ser, "AT+CSQ")
    print(f"Signal: {resp.strip()}")
    
    # Check network registration
    print("\nChecking network registration...")
    for i in range(20):
        resp = send_cmd(ser, "AT+CREG?")
        print(f"Network: {resp.strip()}")
        if "+CREG: 0,1" in resp or "+CREG: 0,5" in resp:
            print("✓ Network registered!")
            break
        time.sleep(2)
    
    # Configure SMS
    print("\n" + "="*40)
    print("Configuring SMS...")
    resp = send_cmd(ser, "AT+CMGF=1")
    print(f"Text mode: {'OK' in resp}")
    
    # Send SMS
    phone = "+306976518415"
    message = "Test SMS from Raspberry Pi with SIM7070G"
    
    print(f"\nSending SMS to {phone}...")
    
    # Clear buffer
    ser.reset_input_buffer()
    
    # Send CMGS command
    ser.write(f'AT+CMGS="{phone}"\r'.encode())
    
    # Wait for prompt
    time.sleep(3)
    prompt_resp = ser.read(ser.in_waiting or 100)
    print(f"After CMGS: {repr(prompt_resp)}")
    
    # Send message
    print("Sending message text...")
    ser.write(message.encode())
    time.sleep(0.5)
    ser.write(b'\x1A')  # Ctrl+Z
    
    # Wait for confirmation
    print("Waiting for confirmation (30 seconds)...")
    time.sleep(30)
    
    final_resp = ser.read(ser.in_waiting or 1000).decode('utf-8', errors='ignore')
    print(f"Response: {final_resp}")
    
    if "+CMGS" in final_resp or "OK" in final_resp:
        print("\n" + "="*40)
        print("✓✓✓ SMS SENT SUCCESSFULLY! ✓✓✓")
        print("="*40)
    else:
        print("\n✗ SMS send failed")
    
    ser.close()
    GPIO.cleanup()
    print("\nTest complete!")

if __name__ == "__main__":
    main()
