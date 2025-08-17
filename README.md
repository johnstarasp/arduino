# SIM7070G SMS Speedometer for Raspberry Pi

This project implements a bike speedometer using a Waveshare SIM7070G HAT on Raspberry Pi that sends speed updates via SMS every 30 seconds.

## 🚀 Quick Start

```bash
# Run the production speedometer
sudo python3 production/bike_speedometer.py

# Test SMS functionality
python3 diagnostics/verify_sms_fix.py
```

## 📋 Project Overview

- **Hall sensor speed measurement** on GPIO 17
- **SMS updates every 30 seconds** with speed data
- **Automatic SIM7070G power control** via GPIO 4
- **Robust error handling** and SMS retry logic
- **Support for new SIM cards** with automatic SMS center configuration

## 🔧 Hardware Setup

### Required Components
- Raspberry Pi (tested on Pi 4)
- Waveshare SIM7070G Cat-M/NB-IoT/GPRS HAT
- Hall sensor for speed detection
- Magnet attached to bike wheel
- Active SIM card with SMS capability

### Connections
```
GPIO 4  -> SIM7070G PWRKEY (Power control)
GPIO 17 -> Hall sensor signal
GND     -> Hall sensor ground
3.3V    -> Hall sensor power (if needed)
```

### SIM7070G HAT Configuration
- **Serial Port**: `/dev/serial0`
- **Baud Rate**: `57600`
- **Power Control**: GPIO 4 (BCM)

## ⚙️ Software Requirements

```bash
# Install required packages
sudo apt-get update
sudo apt-get install python3-serial python3-rpi.gpio

# Enable UART in raspi-config
sudo raspi-config
# -> Interface Options -> Serial -> No to login shell, Yes to hardware
```

## 🚨 Critical Configuration: SMS Service Center

**IMPORTANT**: New SIM cards often don't have the SMS Service Center (SMSC) configured, causing `CMS ERROR 500`.

### Fix for Greek SIM Cards:
```python
# Set correct SMS center (example for specific carrier)
AT+CSCA="+3097100000"

# Alternative centers to try:
# COSMOTE: +306942000000
# WIND: +306977000000  
# VODAFONE: +306945000000
```

This is automatically handled by the production scripts.

## 📁 Project Structure

```
├── production/          # Ready-to-use scripts
│   ├── bike_speedometer.py       # Main speedometer application
│   └── sms_sender.py             # Standalone SMS functionality
├── diagnostics/         # Debugging and testing tools
│   ├── verify_sms_fix.py         # Verify SMS is working
│   ├── sim_diagnosis.py          # Comprehensive SIM testing
│   ├── fix_sms_center.py         # Set correct SMS center
│   └── minimal_sms_test.py       # Basic SMS test
├── development/          # Development and experimental scripts
│   └── [various test scripts]
├── archive/             # Archived experimental files
└── README.md            # This file
```

## 🔧 Configuration

### Phone Number
Edit the phone number in the speedometer script:
```python
self.phone_number = "+306980531698"  # Your phone number
```

### Wheel Circumference
Adjust for your bike wheel size:
```python
self.wheel_circumference = 2.1  # meters (700c wheel ≈ 2.1m)
```

### SMS Update Interval
Change the monitoring interval:
```python
avg_speed, pulses = self.monitor_speed(30)  # 30 seconds
```

## 🚀 Usage

### 1. Test SMS Functionality First
```bash
cd diagnostics/
python3 verify_sms_fix.py
```

Expected output:
```
✅ Module connected
✅ SMS center correctly set to +3097100000
✅ SMS prompt received
🎉 SMS SENT SUCCESSFULLY!
✅ CMS ERROR 500 FIXED!
```

### 2. Run the Speedometer
```bash
cd production/
sudo python3 bike_speedometer.py
```

### 3. Expected SMS Messages
```
Speedometer started at 14:30:15 - All systems working!
Speed: 25.3 km/h (12 pulses) at 14:30:45
Stationary at 14:31:15 (pin: 1)
Speed: 18.7 km/h (8 pulses) at 14:31:45
```

## 🔍 Troubleshooting

### CMS ERROR 500 (Unknown Error)
**Cause**: SMS Service Center not configured on new SIM
**Solution**: 
```bash
python3 diagnostics/fix_sms_center.py
```

### Module Not Responding
**Cause**: Power control or serial communication issue
**Solution**: 
1. Check GPIO 4 connection to PWRKEY
2. Verify `/dev/serial0` at `57600` baud
3. Run: `python3 diagnostics/sim_diagnosis.py`

### No Hall Sensor Pulses
**Cause**: Sensor wiring or magnet positioning
**Solution**: 
1. Check GPIO 17 connection
2. Test by shorting GPIO 17 to ground
3. Adjust magnet position on wheel

### SMS Not Sending
**Common causes**:
- Wrong SMS service center number
- SIM not activated (wait 24-48 hours)
- No SMS service on SIM plan
- Network registration issues

**Debug steps**:
```bash
python3 diagnostics/sim_diagnosis.py
```

## 📊 Speed Calculation

The system calculates speed using:
```
Speed (km/h) = (Wheel Circumference × 3.6) / Time Between Pulses
```

Where:
- **Wheel Circumference**: Distance traveled per revolution (meters)
- **Time Between Pulses**: Time between hall sensor triggers (seconds)
- **3.6**: Conversion factor from m/s to km/h

## 🔒 Security Notes

- SMS messages are sent in plain text
- Phone numbers are stored in code (consider external config)
- No authentication on SMS commands
- SIM PIN should be disabled for automatic startup

## 🛠️ Development

### Adding New Features
1. Create new scripts in `development/`
2. Test thoroughly with diagnostics
3. Move stable code to `production/`

### Testing Changes
```bash
# Test SMS functionality
python3 diagnostics/minimal_sms_test.py

# Test hall sensor
python3 development/hall_sensor_test.py

# Full system test
python3 diagnostics/verify_sms_fix.py
```

## 📝 Known Issues

1. **Initial SMS may fail** - SIM modules need warm-up time
2. **GPIO edge detection conflicts** - Use polling instead of interrupts
3. **Serial timeouts** - Increase timeout for slow networks
4. **New SIM activation** - May take 24-48 hours for full SMS service

## 🆘 Support

For issues:
1. Run full diagnostics: `python3 diagnostics/sim_diagnosis.py`
2. Check hardware connections
3. Verify SIM card SMS capability
4. Test with different SMS service center numbers

## 📜 License

This project is for educational and personal use. Ensure compliance with local regulations regarding SMS and cellular communications.

---

**Last Updated**: August 2025  
**Tested On**: Raspberry Pi 4, Waveshare SIM7070G HAT  
**SIM Compatibility**: Greek carriers (COSMOTE, WIND, VODAFONE)