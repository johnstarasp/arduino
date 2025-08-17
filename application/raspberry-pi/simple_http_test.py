#!/usr/bin/env python3
"""
Simple SIM7070G HTTP Test
Quick test to verify cellular data connectivity with minimal setup
"""

import serial
import time
import sys

def simple_http_test():
    """Simple HTTP test with SIM7070G"""
    print("🌐 Simple SIM7070G HTTP Test")
    print("=" * 40)
    
    try:
        # Initialize serial connection
        print("[1/8] Connecting to SIM7070G...")
        ser = serial.Serial('/dev/serial0', 57600, timeout=10)
        time.sleep(2)
        print("✅ Serial connected")
        
        # Test basic communication
        print("[2/8] Testing basic communication...")
        ser.write(b'AT\r\n')
        time.sleep(2)
        response = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in response:
            print("❌ SIM module not responding")
            return False
        print("✅ SIM module responding")
        
        # Check network registration
        print("[3/8] Checking network registration...")
        ser.write(b'AT+CREG?\r\n')
        time.sleep(2)
        response = ser.read(100).decode('utf-8', errors='ignore')
        if '+CREG: 0,1' in response or '+CREG: 0,5' in response:
            print("✅ Network registered")
        else:
            print("❌ Network not registered")
            print(f"Response: {response}")
            return False
        
        # Set APN
        print("[4/8] Setting APN...")
        ser.write(b'AT+CGDCONT=1,"IP","internet"\r\n')
        time.sleep(3)
        response = ser.read(100).decode('utf-8', errors='ignore')
        print("✅ APN configured")
        
        # Attach to GPRS
        print("[5/8] Attaching to GPRS...")
        ser.write(b'AT+CGATT=1\r\n')
        time.sleep(10)
        response = ser.read(100).decode('utf-8', errors='ignore')
        print("✅ GPRS attached")
        
        # Initialize HTTP
        print("[6/8] Initializing HTTP...")
        ser.write(b'AT+HTTPINIT\r\n')
        time.sleep(3)
        response = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in response:
            print("❌ HTTP init failed")
            return False
        print("✅ HTTP initialized")
        
        # Set HTTP parameters
        print("[7/8] Setting HTTP parameters...")
        ser.write(b'AT+HTTPPARA="CID",1\r\n')
        time.sleep(2)
        ser.read(100)
        
        ser.write(b'AT+HTTPPARA="URL","http://httpbin.org/get"\r\n')
        time.sleep(2)
        ser.read(100)
        print("✅ HTTP parameters set")
        
        # Make HTTP request
        print("[8/8] Making HTTP request...")
        ser.write(b'AT+HTTPACTION=0\r\n')
        time.sleep(15)
        response = ser.read(200).decode('utf-8', errors='ignore')
        
        if '+HTTPACTION: 0,200' in response:
            print("✅ HTTP request successful!")
            
            # Read response
            ser.write(b'AT+HTTPREAD\r\n')
            time.sleep(3)
            http_response = ser.read(500).decode('utf-8', errors='ignore')
            
            print("\n📄 HTTP Response (first 200 chars):")
            print("-" * 40)
            
            # Extract content
            if '+HTTPREAD:' in http_response:
                content_start = http_response.find('+HTTPREAD:')
                if content_start != -1:
                    # Skip the +HTTPREAD: line
                    lines = http_response[content_start:].split('\n')
                    content = '\n'.join(lines[1:]).strip()
                    print(content[:200] + "..." if len(content) > 200 else content)
            
            print("-" * 40)
            print("🎉 SUCCESS: Internet connectivity is working!")
            
        else:
            print("❌ HTTP request failed")
            print(f"Response: {response}")
            return False
        
        # Cleanup
        ser.write(b'AT+HTTPTERM\r\n')
        time.sleep(2)
        ser.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def quick_connectivity_check():
    """Ultra-quick connectivity check"""
    print("⚡ Quick Connectivity Check")
    print("=" * 30)
    
    try:
        ser = serial.Serial('/dev/serial0', 57600, timeout=5)
        time.sleep(1)
        
        # Quick AT test
        ser.write(b'AT\r\n')
        time.sleep(1)
        response = ser.read(50).decode('utf-8', errors='ignore')
        if 'OK' in response:
            print("✅ SIM module: OK")
        else:
            print("❌ SIM module: Not responding")
            return False
        
        # Quick network check
        ser.write(b'AT+CREG?\r\n')
        time.sleep(1)
        response = ser.read(100).decode('utf-8', errors='ignore')
        if '+CREG: 0,1' in response or '+CREG: 0,5' in response:
            print("✅ Network: Registered")
        else:
            print("❌ Network: Not registered")
            return False
        
        # Quick signal check
        ser.write(b'AT+CSQ\r\n')
        time.sleep(1)
        response = ser.read(100).decode('utf-8', errors='ignore')
        if '+CSQ:' in response:
            try:
                rssi = int(response.split('+CSQ:')[1].strip().split(',')[0])
                if rssi != 99:
                    dbm = -113 + (2 * rssi)
                    print(f"✅ Signal: {rssi} ({dbm} dBm)")
                else:
                    print("❌ Signal: No signal")
                    return False
            except:
                print("⚠️ Signal: Unable to parse")
        
        ser.close()
        print("🚀 Ready for internet test!")
        return True
        
    except Exception as e:
        print(f"❌ Quick check failed: {e}")
        return False

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Quick connectivity check (30 seconds)")
    print("2. Full HTTP test (2-3 minutes)")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        sys.exit(1)
    
    if choice == "1":
        success = quick_connectivity_check()
    elif choice == "2":
        print("\nRunning quick check first...")
        if quick_connectivity_check():
            print("\n" + "=" * 50)
            success = simple_http_test()
        else:
            print("\n❌ Quick check failed - skipping HTTP test")
            success = False
    else:
        print("Invalid choice. Running quick check...")
        success = quick_connectivity_check()
    
    if success:
        print("\n🎉 Test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test failed!")
        sys.exit(1)