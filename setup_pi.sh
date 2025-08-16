#!/usr/bin/expect -f

set timeout 30
spawn ssh jstaras@192.168.1.48

expect {
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    "password:" {
        send "Saskatouraw1!\r"
    }
}

expect "$ "
send "cd /repos/arduino\r"
expect "$ "
send "ls -la\r"
expect "$ "

# Create test_modem.py
send "cat > test_modem.py << 'EOF'\r"
send {import serial
import time
import sys

def test_modem():
    ports = ["/dev/serial0", "/dev/ttyS0", "/dev/ttyAMA0", "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]
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
}
send "\rEOF\r"
expect "$ "

# Now run the test
send "sudo python3 test_modem.py\r"
expect {
    "password for jstaras:" {
        send "Saskatouraw1!\r"
        exp_continue
    }
    "$ " {
        # Command completed
    }
    timeout {
        puts "Test modem script timeout"
    }
}

interact