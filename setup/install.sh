#!/bin/bash
# Installation script for bike speedometer auto-start

echo "=== Bike Speedometer Auto-Start Installation ==="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the absolute path to the project
PROJECT_DIR="/home/jstaras/repos/arduinoP/arduino"

# Option 1: Create systemd service (RECOMMENDED)
echo "Installing systemd service..."

cat > /etc/systemd/system/bike-speedometer.service << EOF
[Unit]
Description=Bike Speedometer with SMS Updates
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/production
ExecStart=/usr/bin/python3 $PROJECT_DIR/production/bike_speedometer.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable bike-speedometer.service

echo "✓ Systemd service installed"
echo
echo "Service commands:"
echo "  Start:   sudo systemctl start bike-speedometer"
echo "  Stop:    sudo systemctl stop bike-speedometer"
echo "  Status:  sudo systemctl status bike-speedometer"
echo "  Logs:    sudo journalctl -u bike-speedometer -f"
echo "  Disable: sudo systemctl disable bike-speedometer"
echo

# Option 2: Add to crontab as backup
echo "Adding crontab entry as backup option..."

# Add to root crontab
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && /usr/bin/python3 $PROJECT_DIR/production/bike_speedometer.py >> $PROJECT_DIR/speedometer.log 2>&1") | crontab -

echo "✓ Crontab entry added"
echo

echo "=== Installation Complete ==="
echo
echo "The speedometer will start automatically on boot."
echo "To start it now, run:"
echo "  sudo systemctl start bike-speedometer"
echo