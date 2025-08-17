#!/usr/bin/env python3
"""
Test Firebase Data Transmission via SIM7070G
Quick test to send sample data to Firebase Firestore
"""

import serial
import time
import json
from datetime import datetime, timezone

def test_firebase_data_send():
    """Test sending data to Firebase via SIM7070G"""
    print("🔥 Firebase Data Transmission Test")
    print("=" * 50)
    
    # Sample speedometer data
    test_data = {
        "device_id": "test_speedometer_001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 25.3,
        "pulse_count": 12,
        "battery_level": 85,
        "signal_strength": -75,
        "test": True
    }
    
    try:
        # Initialize serial connection
        print("[1/6] Connecting to SIM7070G...")
        ser = serial.Serial('/dev/serial0', 57600, timeout=10)
        time.sleep(2)
        print("✅ Connected to SIM7070G")
        
        # Test communication
        print("[2/6] Testing communication...")
        ser.write(b'AT\r\n')
        time.sleep(2)
        response = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in response:
            print("❌ SIM module not responding")
            return False
        print("✅ SIM module responding")
        
        # Setup data connection
        print("[3/6] Setting up data connection...")
        ser.write(b'AT+CGDCONT=1,"IP","internet"\r\n')
        time.sleep(2)
        ser.read(100)
        
        ser.write(b'AT+CGATT=1\r\n')
        time.sleep(5)
        ser.read(100)
        print("✅ Data connection ready")
        
        # Prepare Firebase API request
        print("[4/6] Preparing Firebase request...")
        
        # Replace with your Firebase project ID
        firebase_project_id = "your-project-id"
        firebase_url = f"https://firestore.googleapis.com/v1/projects/{firebase_project_id}/databases/(default)/documents/speed_data"
        
        # Convert to Firestore format
        firestore_doc = {
            "fields": {
                "device_id": {"stringValue": test_data["device_id"]},
                "timestamp": {"timestampValue": test_data["timestamp"]},
                "speed": {"doubleValue": test_data["speed"]},
                "pulse_count": {"integerValue": str(test_data["pulse_count"])},
                "battery_level": {"doubleValue": test_data["battery_level"]},
                "signal_strength": {"integerValue": str(test_data["signal_strength"])},
                "test": {"booleanValue": test_data["test"]},
                "created_at": {"timestampValue": datetime.now(timezone.utc).isoformat()}
            }
        }
        
        json_data = json.dumps(firestore_doc)
        content_length = len(json_data.encode('utf-8'))
        
        print(f"✅ Prepared {content_length} bytes of data")
        
        # Initialize HTTP
        print("[5/6] Sending data to Firebase...")
        ser.write(b'AT+HTTPINIT\r\n')
        time.sleep(2)
        ser.read(100)
        
        # Set parameters
        ser.write(b'AT+HTTPPARA="CID",1\r\n')
        time.sleep(1)
        ser.read(100)
        
        ser.write(f'AT+HTTPPARA="URL","{firebase_url}"\r\n'.encode())
        time.sleep(1)
        ser.read(100)
        
        # Set headers
        ser.write(b'AT+HTTPPARA="USERDATA","Content-Type: application/json"\r\n')
        time.sleep(1)
        ser.read(100)
        
        # Send POST data
        ser.write(f'AT+HTTPDATA={content_length},10000\r\n'.encode())
        time.sleep(2)
        response = ser.read(100)
        
        if b'DOWNLOAD' in response:
            # Send the JSON data
            ser.write(json_data.encode('utf-8'))
            time.sleep(3)
            
            # Execute POST
            ser.write(b'AT+HTTPACTION=1\r\n')
            time.sleep(15)
            
            response = ser.read(500).decode('utf-8', errors='ignore')
            print(f"[RESPONSE] {response}")
            
            if '+HTTPACTION: 1,200' in response:
                print("✅ Data sent to Firebase successfully!")
                success = True
            elif '+HTTPACTION: 1,201' in response:
                print("✅ Data created in Firebase successfully!")
                success = True
            else:
                print("❌ Firebase request failed")
                print(f"Response: {response}")
                success = False
        else:
            print("❌ Failed to send data")
            success = False
        
        # Cleanup
        print("[6/6] Cleaning up...")
        ser.write(b'AT+HTTPTERM\r\n')
        time.sleep(2)
        ser.close()
        
        if success:
            print("\n🎉 SUCCESS: Test data sent to Firebase!")
            print(f"📊 Data sent: Speed {test_data['speed']} km/h, Battery {test_data['battery_level']}%")
            print("🔍 Check your Firebase Console to verify the data")
        else:
            print("\n❌ FAILED: Could not send data to Firebase")
            print("🔧 Check Firebase configuration and API permissions")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_with_config():
    """Test using firebase-config.json"""
    try:
        with open('firebase-config.json', 'r') as f:
            config = json.load(f)
        
        project_id = config.get('firebase_project_id')
        api_key = config.get('api_key')
        
        if not project_id or not api_key:
            print("❌ Missing Firebase configuration")
            print("📝 Please update firebase-config.json with your project details")
            return False
        
        print(f"🔥 Using Firebase project: {project_id}")
        return test_firebase_data_send()
        
    except FileNotFoundError:
        print("❌ firebase-config.json not found")
        print("📝 Please create configuration file first")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Firebase Data Transmission Test")
    print("This test will send sample speedometer data to Firebase")
    print()
    
    try:
        choice = input("Use firebase-config.json? (y/n): ").lower().strip()
        if choice == 'y':
            success = test_with_config()
        else:
            success = test_firebase_data_send()
        
        if success:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")