# Auto-Start Setup for Bike Speedometer

This directory contains scripts to automatically start the bike speedometer when your Raspberry Pi boots.

## 🚀 Quick Installation

```bash
cd setup/
sudo bash install.sh
```

## 📋 What Gets Installed

### Method 1: Systemd Service (Primary)
- **Service name**: `bike-speedometer`
- **Auto-starts** on boot
- **Auto-restarts** if it crashes
- **Logs** to system journal

### Method 2: Crontab (Backup)
- **@reboot** entry in root crontab
- **30-second delay** to ensure system is ready
- **Logs** to `speedometer.log`

## 🎛️ Service Management

### Start/Stop Service
```bash
# Start the speedometer
sudo systemctl start bike-speedometer

# Stop the speedometer  
sudo systemctl stop bike-speedometer

# Restart the speedometer
sudo systemctl restart bike-speedometer
```

### Check Status
```bash
# Service status
sudo systemctl status bike-speedometer

# View live logs
sudo journalctl -u bike-speedometer -f

# View recent logs
sudo journalctl -u bike-speedometer --since "10 minutes ago"
```

### Enable/Disable Auto-Start
```bash
# Enable auto-start on boot
sudo systemctl enable bike-speedometer

# Disable auto-start on boot
sudo systemctl disable bike-speedometer
```

## 📊 Monitoring

### Real-time Logs
```bash
# System journal (recommended)
sudo journalctl -u bike-speedometer -f

# Log file (if using crontab method)
tail -f speedometer.log
```

### Check if Running
```bash
# Check service status
sudo systemctl is-active bike-speedometer

# Check process
ps aux | grep bike_speedometer
```

## 🔧 Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status bike-speedometer

# Check for errors
sudo journalctl -u bike-speedometer --since "5 minutes ago"

# Test script manually
cd production/
sudo python3 bike_speedometer.py
```

### Permissions Issues
```bash
# Ensure proper ownership
sudo chown -R jstaras:jstaras /home/jstaras/repos/arduinoP/arduino

# Check GPIO permissions
ls -la /dev/gpiomem
groups jstaras  # Should include 'gpio'
```

### SIM Module Issues
```bash
# Test SIM module
cd diagnostics/
python3 verify_sms_fix.py

# Check serial permissions
ls -la /dev/serial0
groups jstaras  # Should include 'dialout'
```

## ⚠️ Important Notes

1. **Service runs as root** - Required for GPIO access
2. **30-second delay** on boot - Allows system to stabilize
3. **Auto-restart** - Service restarts if it crashes
4. **SMS on startup** - Sends notification when started

## 🗑️ Uninstallation

```bash
cd setup/
sudo bash uninstall.sh
```

This will:
- Stop and disable the systemd service
- Remove the service file
- Remove crontab entries
- Clean up all auto-start configurations

## 🔄 Service Configuration

The systemd service is configured with:
- **Restart policy**: Always restart on failure
- **Restart delay**: 30 seconds between restarts
- **Working directory**: `production/`
- **User**: root (required for GPIO)
- **Logging**: System journal

## 📱 SMS Notifications

The speedometer will send SMS notifications for:
- **Startup**: "Speedometer started at HH:MM:SS - Ready to track!"
- **Speed updates**: Every 30 seconds while running
- **Shutdown**: "Speedometer stopped at HH:MM:SS" (on clean shutdown)

## 🔐 Security

- Service runs as root for hardware access
- No network services exposed
- SMS messages are plain text
- Consider firewall rules if needed