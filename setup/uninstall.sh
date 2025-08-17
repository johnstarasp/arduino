#!/bin/bash
# Uninstallation script for speedometer auto-start

echo "=== Speedometer Auto-Start Uninstallation ==="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Stop and disable systemd service
echo "Removing systemd service..."

# Stop the service if running
systemctl stop speedometer.service 2>/dev/null

# Disable the service
systemctl disable speedometer.service 2>/dev/null

# Remove service file
rm -f /etc/systemd/system/speedometer.service

# Reload systemd
systemctl daemon-reload

echo "✓ Systemd service removed"

# Remove from crontab
echo "Removing crontab entry..."

# Remove the specific line from crontab
crontab -l 2>/dev/null | grep -v "speedometer.py" | crontab -

echo "✓ Crontab entry removed"

echo
echo "=== Uninstallation Complete ==="
echo "The speedometer will no longer start automatically."
echo