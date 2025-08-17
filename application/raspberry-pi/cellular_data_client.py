#!/usr/bin/env python3
"""
Cellular Data Client for SIM7070G
Sends sensor data via HTTP API calls using cellular data connection
Includes local buffering to prevent data loss during network outages
"""

import serial
import time
import json
import sqlite3
import requests
import os
from datetime import datetime
from typing import Dict, List, Optional
import threading
import queue

class CellularDataClient:
    def __init__(self, config_file="config.json"):
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Hardware configuration
        self.ser = None
        self.GPIO = None
        self.hall_pin = self.config.get("hall_pin", 17)
        self.wheel_circumference = self.config.get("wheel_circumference", 2.1)
        
        # Network configuration
        self.api_endpoint = self.config.get("api_endpoint", "https://your-api.com/api/data")
        self.device_id = self.config.get("device_id", "speedometer_001")
        
        # Data buffering
        self.db_path = "sensor_data.db"
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
        """Load configuration from JSON file"""
        default_config = {
            "hall_pin": 17,
            "wheel_circumference": 2.1,
            "api_endpoint": "http://localhost:3000/api/data",
            "device_id": "speedometer_001",
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
                    timestamp TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    speed REAL NOT NULL,
                    pulse_count INTEGER NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    sent BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sent ON sensor_data(sent)
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
    
    def store_data_locally(self, data: Dict):
        """Store sensor data locally in SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO sensor_data (timestamp, device_id, speed, pulse_count, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['timestamp'],
                data['device_id'],
                data['speed'],
                data['pulse_count'],
                data.get('latitude'),
                data.get('longitude')
            ))
            
            conn.commit()
            conn.close()
            print(f"[DB] Data stored locally: {data['speed']:.1f} km/h")
        except Exception as e:
            print(f"[ERROR] Local storage failed: {e}")
    
    def send_http_request(self, data: Dict) -> bool:
        """Send HTTP POST request via SIM7070G cellular connection"""
        try:
            if not self.ser or not self.ser.is_open:
                print("[ERROR] SIM module not connected")
                return False
            
            # Prepare HTTP request
            json_data = json.dumps(data)
            content_length = len(json_data)
            
            # HTTP request components
            host = self.api_endpoint.replace('https://', '').replace('http://', '').split('/')[0]
            path = '/' + '/'.join(self.api_endpoint.split('/')[3:]) if len(self.api_endpoint.split('/')) > 3 else '/'
            
            http_request = f"POST {path} HTTP/1.1\r\n"
            http_request += f"Host: {host}\r\n"
            http_request += "Content-Type: application/json\r\n"
            http_request += f"Content-Length: {content_length}\r\n"
            http_request += "Connection: close\r\n"
            http_request += "\r\n"
            http_request += json_data
            
            print(f"[HTTP] Sending to {host}{path}")
            
            # Start HTTP connection
            self.ser.write(b'AT+HTTPINIT\r\n')
            time.sleep(2)
            self.ser.read(100)
            
            # Set parameters
            self.ser.write(f'AT+HTTPPARA="CID",1\r\n'.encode())
            time.sleep(1)
            self.ser.read(100)
            
            self.ser.write(f'AT+HTTPPARA="URL","{self.api_endpoint}"\r\n'.encode())
            time.sleep(1)
            self.ser.read(100)
            
            # Send POST request
            self.ser.write(f'AT+HTTPDATA={content_length},10000\r\n'.encode())
            time.sleep(2)
            response = self.ser.read(100)
            
            if b'DOWNLOAD' in response:
                # Send the JSON data
                self.ser.write(json_data.encode())
                time.sleep(2)
                
                # Execute POST
                self.ser.write(b'AT+HTTPACTION=1\r\n')
                time.sleep(10)
                
                # Read response
                response = self.ser.read(500).decode('utf-8', errors='ignore')
                
                # Terminate HTTP
                self.ser.write(b'AT+HTTPTERM\r\n')
                time.sleep(1)
                self.ser.read(100)
                
                if '+HTTPACTION: 1,200' in response:
                    print("[OK] HTTP request successful (200)")
                    return True
                else:
                    print(f"[ERROR] HTTP request failed: {response}")
                    return False
            else:
                print("[ERROR] Failed to start HTTP data transfer")
                return False
                
        except Exception as e:
            print(f"[ERROR] HTTP request failed: {e}")
            return False
    
    def sync_buffered_data(self):
        """Send any unsent data from local database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get unsent data
            cursor.execute('SELECT * FROM sensor_data WHERE sent = FALSE ORDER BY created_at')
            unsent_data = cursor.fetchall()
            
            for row in unsent_data:
                data = {
                    'timestamp': row[1],
                    'device_id': row[2],
                    'speed': row[3],
                    'pulse_count': row[4],
                    'latitude': row[5],
                    'longitude': row[6]
                }
                
                if self.send_http_request(data):
                    # Mark as sent
                    cursor.execute('UPDATE sensor_data SET sent = TRUE WHERE id = ?', (row[0],))
                    conn.commit()
                    print(f"[SYNC] Sent buffered data: {data['speed']:.1f} km/h")
                else:
                    print(f"[SYNC] Failed to send buffered data")
                    break  # Stop trying if network is down
                
                time.sleep(1)  # Rate limiting
            
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
        
        return {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'speed': avg_speed,
            'pulse_count': pulses,
            'latitude': None,  # TODO: Add GPS if available
            'longitude': None
        }
    
    def data_collection_loop(self):
        """Main data collection and transmission loop"""
        while self.running:
            try:
                # Collect speed data
                data = self.monitor_speed(self.config.get("data_interval", 30))
                
                # Store locally first (backup)
                self.store_data_locally(data)
                
                # Try to send via cellular
                if self.send_http_request(data):
                    print(f"[API] Data sent successfully: {data['speed']:.1f} km/h")
                    
                    # Try to sync any buffered data
                    self.sync_buffered_data()
                else:
                    print("[WARNING] API request failed - data stored locally")
                
            except Exception as e:
                print(f"[ERROR] Data collection error: {e}")
                time.sleep(5)
    
    def run(self):
        """Main application entry point"""
        print("====== CELLULAR DATA SPEEDOMETER ======")
        print("=" * 50)
        print(f"Device ID: {self.device_id}")
        print(f"API Endpoint: {self.api_endpoint}")
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
        print("[INFO] Starting data collection and transmission...")
        print("[STOP] Press Ctrl+C to stop")
        print()
        
        try:
            self.data_collection_loop()
        except KeyboardInterrupt:
            print("\n[STOP] Stopping cellular data client...")
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
    client = CellularDataClient()
    client.run()

if __name__ == "__main__":
    main()