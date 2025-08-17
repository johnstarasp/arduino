#!/usr/bin/env python3
"""
Firebase Firestore Direct Client for SIM7070G
Sends sensor data directly to Firebase Firestore via cellular data
Includes local buffering and automatic retry logic
"""

import serial
import time
import json
import sqlite3
import os
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional
import threading
import queue
import hashlib
import hmac

class FirebaseClient:
    def __init__(self, config_file="firebase-config.json"):
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Hardware configuration
        self.ser = None
        self.GPIO = None
        self.hall_pin = self.config.get("hall_pin", 17)
        self.wheel_circumference = self.config.get("wheel_circumference", 2.1)
        
        # Firebase configuration
        self.firebase_url = self.config.get("firebase_url")
        self.device_id = self.config.get("device_id", "speedometer_001")
        self.api_key = self.config.get("api_key")
        
        # Data buffering
        self.db_path = "sensor_data_firebase.db"
        self.data_queue = queue.Queue()
        self.running = True
        
        # Speed tracking
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.current_speed = 0.0
        self.last_pin_state = 1
        
        # Initialize database
        self.init_database()
    
    def load_config(self, config_file: str) -> Dict:
        """Load Firebase configuration from JSON file"""
        default_config = {
            "hall_pin": 17,
            "wheel_circumference": 2.1,
            "firebase_url": "https://your-project.firebaseio.com",
            "device_id": "speedometer_001",
            "api_key": "your-firebase-web-api-key",
            "data_interval": 30,
            "retry_attempts": 3,
            "apn": "internet"
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    default_config.update(config)
            else:
                # Create default config file
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                print(f"[CONFIG] Created default config: {config_file}")
        except Exception as e:
            print(f"[ERROR] Config error: {e}")
        
        return default_config
    
    def init_database(self):
        """Initialize SQLite database for local data buffering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firebase_doc_id TEXT,
                    timestamp TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    speed REAL NOT NULL,
                    pulse_count INTEGER NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    battery_level REAL,
                    signal_strength INTEGER,
                    sent BOOLEAN DEFAULT FALSE,
                    retry_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sent ON sensor_data(sent)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_retry ON sensor_data(retry_count)
            ''')
            
            conn.commit()
            conn.close()
            print("[OK] Database initialized")
        except Exception as e:
            print(f"[ERROR] Database init failed: {e}")
    
    def init_gpio(self):
        """Initialize GPIO for hall sensor"""
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
            
            # Setup hall sensor pin
            GPIO.setup(self.hall_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(4, GPIO.OUT)  # SIM power control
            
            print(f"[OK] GPIO initialized - Hall sensor on pin {self.hall_pin}")
            return True
        except Exception as e:
            print(f"[ERROR] GPIO init failed: {e}")
            return False
    
    def init_sim_module(self):
        """Initialize SIM7070G module for data connection"""
        try:
            print("[POWER] Powering SIM7070G module...")
            
            # Power cycle sequence
            self.GPIO.output(4, self.GPIO.LOW)
            time.sleep(3)
            self.GPIO.output(4, self.GPIO.HIGH)
            time.sleep(3)
            self.GPIO.output(4, self.GPIO.LOW)
            
            print("[WAIT] Waiting 20 seconds for module boot...")
            time.sleep(20)
            
            # Connect to module
            self.ser = serial.Serial('/dev/serial0', 57600, timeout=10)
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
            
            # Configure for data connection
            commands = [
                (b"ATE0\r\n", "Disable echo"),
                (b'AT+CMEE=2\r\n', "Enable verbose errors"),
                (b'AT+CGDCONT=1,"IP","internet"\r\n', "Set APN"),
                (b'AT+CGATT=1\r\n', "Attach to GPRS"),
            ]
            
            for cmd, desc in commands:
                print(f"[CONFIG] {desc}...")
                self.ser.write(cmd)
                time.sleep(2)
                response = self.ser.read(200)
                if b'OK' not in response and b'ERROR' in response:
                    print(f"[WARNING] {desc} warning: {response}")
            
            # Wait for network registration
            print("[NETWORK] Waiting for network registration...")
            for attempt in range(30):
                self.ser.write(b'AT+CREG?\r\n')
                time.sleep(2)
                response = self.ser.read(200).decode('utf-8', errors='ignore')
                if '+CREG: 0,1' in response or '+CREG: 0,5' in response:
                    print("[OK] Network registered")
                    break
                time.sleep(2)
            else:
                print("[WARNING] Network registration timeout")
            
            print("[OK] SIM module ready for data")
            return True
            
        except Exception as e:
            print(f"[ERROR] SIM init failed: {e}")
            return False
    
    def check_hall_sensor(self):
        """Poll hall sensor for state changes"""
        try:
            current_state = self.GPIO.input(self.hall_pin)
            
            # Detect falling edge (magnet passing sensor)
            if self.last_pin_state == 1 and current_state == 0:
                current_time = time.time()
                
                if self.last_pulse_time > 0:
                    time_diff = current_time - self.last_pulse_time
                    if time_diff > 0.1:  # Debounce
                        # Calculate instantaneous speed
                        speed_ms = self.wheel_circumference / time_diff
                        self.current_speed = speed_ms * 3.6  # km/h
                        print(f"[PULSE] Speed: {self.current_speed:.1f} km/h")
                
                self.last_pulse_time = current_time
                self.pulse_count += 1
            
            self.last_pin_state = current_state
        except Exception as e:
            print(f"[ERROR] Hall sensor error: {e}")
    
    def get_battery_level(self):
        """Get battery level from SIM module (if available)"""
        try:
            if not self.ser or not self.ser.is_open:
                return None
            
            self.ser.write(b'AT+CBC\r\n')
            time.sleep(2)
            response = self.ser.read(200).decode('utf-8', errors='ignore')
            
            # Parse response: +CBC: <bcs>,<bcl>,<voltage>
            if '+CBC:' in response:
                parts = response.split('+CBC:')[1].strip().split(',')
                if len(parts) >= 2:
                    return int(parts[1])  # Battery level percentage
        except Exception as e:
            print(f"[WARNING] Battery level read failed: {e}")
        
        return None
    
    def get_signal_strength(self):
        """Get signal strength from SIM module"""
        try:
            if not self.ser or not self.ser.is_open:
                return None
            
            self.ser.write(b'AT+CSQ\r\n')
            time.sleep(2)
            response = self.ser.read(200).decode('utf-8', errors='ignore')
            
            # Parse response: +CSQ: <rssi>,<ber>
            if '+CSQ:' in response:
                parts = response.split('+CSQ:')[1].strip().split(',')
                if len(parts) >= 1:
                    rssi = int(parts[0])
                    if rssi != 99:  # 99 = unknown
                        # Convert to dBm: -113 + 2*rssi
                        return -113 + (2 * rssi)
        except Exception as e:
            print(f"[WARNING] Signal strength read failed: {e}")
        
        return None
    
    def store_data_locally(self, data: Dict):
        """Store sensor data locally in SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sensor_data 
                (timestamp, device_id, speed, pulse_count, latitude, longitude, battery_level, signal_strength)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['timestamp'],
                data['device_id'],
                data['speed'],
                data['pulse_count'],
                data.get('latitude'),
                data.get('longitude'),
                data.get('battery_level'),
                data.get('signal_strength')
            ))
            
            conn.commit()
            conn.close()
            print(f"[DB] Data stored locally: {data['speed']:.1f} km/h")
        except Exception as e:
            print(f"[ERROR] Local storage failed: {e}")
    
    def send_to_firebase(self, data: Dict) -> bool:
        """Send data directly to Firebase REST API via cellular"""
        try:
            if not self.ser or not self.ser.is_open:
                print("[ERROR] SIM module not connected")
                return False
            
            # Prepare Firebase REST API URL
            collection_url = f"{self.firebase_url}/v1/projects/{self.config.get('firebase_project_id')}/databases/(default)/documents/speed_data"
            
            # Prepare Firestore document
            firestore_doc = {
                "fields": {
                    "device_id": {"stringValue": data['device_id']},
                    "timestamp": {"timestampValue": data['timestamp']},
                    "speed": {"doubleValue": data['speed']},
                    "pulse_count": {"integerValue": str(data['pulse_count'])},
                    "created_at": {"timestampValue": datetime.now(timezone.utc).isoformat()}
                }
            }
            
            # Add optional fields
            if data.get('latitude'):
                firestore_doc["fields"]["latitude"] = {"doubleValue": data['latitude']}
            if data.get('longitude'):
                firestore_doc["fields"]["longitude"] = {"doubleValue": data['longitude']}
            if data.get('battery_level'):
                firestore_doc["fields"]["battery_level"] = {"doubleValue": data['battery_level']}
            if data.get('signal_strength'):
                firestore_doc["fields"]["signal_strength"] = {"integerValue": str(data['signal_strength'])}
            
            json_data = json.dumps(firestore_doc)
            
            print(f"[FIREBASE] Sending to Firestore via cellular...")
            
            # Use SIM7070G HTTP client to send to Firebase
            success = self.send_http_via_sim(collection_url, json_data, {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            
            if success:
                print("[OK] Data sent to Firebase successfully")
                return True
            else:
                print("[ERROR] Failed to send data to Firebase")
                return False
                
        except Exception as e:
            print(f"[ERROR] Firebase send failed: {e}")
            return False
    
    def send_http_via_sim(self, url: str, data: str, headers: Dict) -> bool:
        """Send HTTP POST request via SIM7070G"""
        try:
            # Parse URL
            if url.startswith('https://'):
                host = url.replace('https://', '').split('/')[0]
                path = '/' + '/'.join(url.split('/')[3:])
                use_ssl = True
            else:
                host = url.replace('http://', '').split('/')[0]
                path = '/' + '/'.join(url.split('/')[3:])
                use_ssl = False
            
            # Initialize HTTP
            self.ser.write(b'AT+HTTPINIT\r\n')
            time.sleep(2)
            self.ser.read(100)
            
            # Set SSL if needed
            if use_ssl:
                self.ser.write(b'AT+HTTPSSL=1\r\n')
                time.sleep(2)
                self.ser.read(100)
            
            # Set parameters
            self.ser.write(f'AT+HTTPPARA="CID",1\r\n'.encode())
            time.sleep(1)
            self.ser.read(100)
            
            self.ser.write(f'AT+HTTPPARA="URL","{url}"\r\n'.encode())
            time.sleep(1)
            self.ser.read(100)
            
            # Set headers
            for header_name, header_value in headers.items():
                self.ser.write(f'AT+HTTPPARA="USERDATA","{header_name}: {header_value}"\r\n'.encode())
                time.sleep(1)
                self.ser.read(100)
            
            # Send POST data
            content_length = len(data.encode('utf-8'))
            self.ser.write(f'AT+HTTPDATA={content_length},10000\r\n'.encode())
            time.sleep(2)
            response = self.ser.read(100)
            
            if b'DOWNLOAD' in response:
                # Send the data
                self.ser.write(data.encode('utf-8'))
                time.sleep(2)
                
                # Execute POST
                self.ser.write(b'AT+HTTPACTION=1\r\n')
                time.sleep(15)  # Wait longer for Firebase response
                
                # Read response
                response = self.ser.read(500).decode('utf-8', errors='ignore')
                
                # Terminate HTTP
                self.ser.write(b'AT+HTTPTERM\r\n')
                time.sleep(1)
                self.ser.read(100)
                
                # Check for success (200 or 201 for Firebase)
                if '+HTTPACTION: 1,200' in response or '+HTTPACTION: 1,201' in response:
                    return True
                else:
                    print(f"[ERROR] HTTP request failed: {response}")
                    return False
            else:
                print("[ERROR] Failed to start HTTP data transfer")
                self.ser.write(b'AT+HTTPTERM\r\n')
                return False
                
        except Exception as e:
            print(f"[ERROR] HTTP via SIM failed: {e}")
            try:
                self.ser.write(b'AT+HTTPTERM\r\n')
            except:
                pass
            return False
    
    def sync_buffered_data(self):
        """Send any unsent data from local database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get unsent data (limit retry attempts)
            cursor.execute('''
                SELECT * FROM sensor_data 
                WHERE sent = FALSE AND retry_count < 5 
                ORDER BY created_at 
                LIMIT 10
            ''')
            unsent_data = cursor.fetchall()
            
            for row in unsent_data:
                data = {
                    'timestamp': row[2],
                    'device_id': row[3],
                    'speed': row[4],
                    'pulse_count': row[5],
                    'latitude': row[6],
                    'longitude': row[7],
                    'battery_level': row[8],
                    'signal_strength': row[9]
                }
                
                if self.send_to_firebase(data):
                    # Mark as sent
                    cursor.execute('UPDATE sensor_data SET sent = TRUE WHERE id = ?', (row[0],))
                    conn.commit()
                    print(f"[SYNC] Sent buffered data: {data['speed']:.1f} km/h")
                else:
                    # Increment retry count
                    cursor.execute(
                        'UPDATE sensor_data SET retry_count = retry_count + 1 WHERE id = ?', 
                        (row[0],)
                    )
                    conn.commit()
                    print(f"[SYNC] Failed to send buffered data (retry {row[10] + 1})")
                    break  # Stop trying if network is down
                
                time.sleep(2)  # Rate limiting
            
            conn.close()
        except Exception as e:
            print(f"[ERROR] Data sync failed: {e}")
    
    def monitor_speed(self, duration: int) -> Dict:
        """Monitor speed for specified duration"""
        start_count = self.pulse_count
        start_time = time.time()
        end_time = start_time + duration
        
        print(f"[MONITOR] Monitoring speed for {duration} seconds...")
        
        while time.time() < end_time and self.running:
            self.check_hall_sensor()
            time.sleep(0.01)  # Poll every 10ms
        
        pulses = self.pulse_count - start_count
        time_elapsed = time.time() - start_time
        
        # Calculate average speed
        if pulses > 0:
            distance = pulses * self.wheel_circumference
            avg_speed = (distance / time_elapsed) * 3.6  # km/h
        else:
            avg_speed = 0.0
        
        # Get additional sensor data
        battery_level = self.get_battery_level()
        signal_strength = self.get_signal_strength()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'device_id': self.device_id,
            'speed': avg_speed,
            'pulse_count': pulses,
            'latitude': None,  # TODO: Add GPS if available
            'longitude': None,
            'battery_level': battery_level,
            'signal_strength': signal_strength
        }
    
    def data_collection_loop(self):
        """Main data collection and transmission loop"""
        while self.running:
            try:
                # Collect speed data
                data = self.monitor_speed(self.config.get("data_interval", 30))
                
                # Store locally first (backup)
                self.store_data_locally(data)
                
                # Try to send to Firebase
                if self.send_to_firebase(data):
                    print(f"[FIREBASE] Data sent successfully: {data['speed']:.1f} km/h")
                    
                    # Try to sync any buffered data
                    self.sync_buffered_data()
                else:
                    print("[WARNING] Firebase send failed - data stored locally")
                
            except Exception as e:
                print(f"[ERROR] Data collection error: {e}")
                time.sleep(5)
    
    def run(self):
        """Main application entry point"""
        print("====== FIREBASE CELLULAR SPEEDOMETER ======")
        print("=" * 50)
        print(f"Device ID: {self.device_id}")
        print(f"Firebase URL: {self.firebase_url}")
        print(f"Wheel circumference: {self.wheel_circumference}m")
        print(f"Hall sensor: GPIO {self.hall_pin}")
        print(f"Data interval: {self.config.get('data_interval', 30)}s")
        print("=" * 50)
        
        # Initialize hardware
        if not self.init_gpio():
            print("[ERROR] Failed to initialize GPIO")
            return
        
        if not self.init_sim_module():
            print("[ERROR] Failed to initialize SIM module")
            return
        
        print("\n[SUCCESS] ALL SYSTEMS READY!")
        print("[INFO] Starting data collection and Firebase sync...")
        print("[STOP] Press Ctrl+C to stop")
        print()
        
        try:
            self.data_collection_loop()
        except KeyboardInterrupt:
            print("\n[STOP] Stopping Firebase client...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.running = False
            
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            if self.GPIO:
                self.GPIO.cleanup()
            
            print("[OK] Cleanup complete")
        except:
            pass

def main():
    """Application entry point"""
    client = FirebaseClient()
    client.run()

if __name__ == "__main__":
    main()