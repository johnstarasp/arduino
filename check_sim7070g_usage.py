#!/usr/bin/env python3
"""
Check if SIM7070G module is being used by other processes
"""
import subprocess
import time
import serial
import os
import psutil

def check_serial_port_usage():
    """Check what processes are using the serial port"""
    print("=== Checking Serial Port Usage ===")
    
    # Check with lsof (list open files)
    try:
        result = subprocess.run(['lsof', '/dev/serial0'], 
                              capture_output=True, text=True)
        if result.stdout:
            print("Processes using /dev/serial0:")
            print(result.stdout)
        else:
            print("No processes currently using /dev/serial0")
    except FileNotFoundError:
        print("lsof command not found")
    
    # Check with fuser
    try:
        result = subprocess.run(['fuser', '/dev/serial0'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print(f"PIDs using /dev/serial0: {result.stdout.strip()}")
        else:
            print("No PIDs found using /dev/serial0")
    except FileNotFoundError:
        print("fuser command not found")

def check_running_processes():
    """Check for processes that might be using SIM7070G"""
    print("\n=== Checking Running Processes ===")
    
    # Keywords to search for
    keywords = ['sim7070', 'modem', 'ppp', 'wvdial', 'minicom', 'screen', 'socat', 'serial']
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            process_info = proc.info
            cmdline = ' '.join(process_info['cmdline']) if process_info['cmdline'] else ''
            
            for keyword in keywords:
                if (keyword in process_info['name'].lower() or 
                    keyword in cmdline.lower() or
                    '/dev/serial0' in cmdline or
                    '/dev/ttyS0' in cmdline):
                    print(f"PID {process_info['pid']}: {process_info['name']} - {cmdline}")
                    break
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def check_systemd_services():
    """Check for systemd services that might use the modem"""
    print("\n=== Checking Systemd Services ===")
    
    services_to_check = [
        'ModemManager',
        'networkmanager', 
        'pppd',
        'wvdial',
        'gpsd'
    ]
    
    for service in services_to_check:
        try:
            result = subprocess.run(['systemctl', 'is-active', service], 
                                  capture_output=True, text=True)
            status = result.stdout.strip()
            if status == 'active':
                print(f"⚠️  {service}: {status}")
                # Get more info about active service
                result = subprocess.run(['systemctl', 'status', service, '--no-pager', '-l'], 
                                      capture_output=True, text=True)
                print(f"   Details: {result.stdout.split('Active:')[1].split('\\n')[0] if 'Active:' in result.stdout else 'N/A'}")
            else:
                print(f"✓ {service}: {status}")
        except Exception as e:
            print(f"Could not check {service}: {e}")

def test_serial_access():
    """Test if we can access the serial port"""
    print("\n=== Testing Serial Port Access ===")
    
    try:
        ser = serial.Serial('/dev/serial0', 57600, timeout=1)
        print("✓ Successfully opened /dev/serial0")
        
        # Try a simple AT command
        ser.write(b'AT\r\n')
        time.sleep(1)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(f"✓ SIM7070G responded: {response.strip()}")
        else:
            print("⚠️  No response from SIM7070G")
            
        ser.close()
        
    except serial.SerialException as e:
        print(f"❌ Cannot access /dev/serial0: {e}")
        print("This suggests another process is using the port")
    except Exception as e:
        print(f"❌ Error testing serial port: {e}")

def monitor_serial_activity(duration=10):
    """Monitor serial port for unexpected activity"""
    print(f"\n=== Monitoring Serial Activity for {duration} seconds ===")
    
    try:
        ser = serial.Serial('/dev/serial0', 57600, timeout=0.1)
        print("Monitoring for unexpected data...")
        
        start_time = time.time()
        activity_detected = False
        
        while time.time() - start_time < duration:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting()).decode('utf-8', errors='ignore')
                print(f"Unexpected data: {data.strip()}")
                activity_detected = True
            time.sleep(0.1)
            
        if not activity_detected:
            print("✓ No unexpected serial activity detected")
        else:
            print("⚠️  Unexpected serial activity detected - another process may be using the module")
            
        ser.close()
        
    except serial.SerialException as e:
        print(f"❌ Cannot monitor serial port: {e}")

def check_cron_jobs():
    """Check for cron jobs that might use the modem"""
    print("\n=== Checking Cron Jobs ===")
    
    try:
        # Check system crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.stdout and 'serial' in result.stdout.lower():
            print("Found serial-related cron jobs:")
            print(result.stdout)
        else:
            print("No obvious serial-related cron jobs found")
            
        # Check system-wide crontabs
        cron_dirs = ['/etc/cron.d/', '/etc/cron.hourly/', '/etc/cron.daily/']
        for cron_dir in cron_dirs:
            if os.path.exists(cron_dir):
                files = os.listdir(cron_dir)
                if files:
                    print(f"Files in {cron_dir}: {', '.join(files)}")
                    
    except Exception as e:
        print(f"Could not check cron jobs: {e}")

def main():
    print("SIM7070G Usage Conflict Detector")
    print("=" * 40)
    
    check_serial_port_usage()
    check_running_processes()
    check_systemd_services()
    check_cron_jobs()
    test_serial_access()
    monitor_serial_activity(10)
    
    print("\n" + "=" * 40)
    print("Recommendations:")
    print("1. If ModemManager is active, disable it: sudo systemctl disable ModemManager")
    print("2. If other processes are using /dev/serial0, stop them first")
    print("3. Check for custom scripts in /etc/cron.* that might be using the modem")
    print("4. Reboot if needed to clear any stuck processes")

if __name__ == "__main__":
    main()