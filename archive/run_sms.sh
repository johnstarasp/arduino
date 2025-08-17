#!/bin/bash
echo "Running SMS test on Raspberry Pi..."
ssh jstaras@192.168.1.48 << 'ENDSSH'
Saskatouraw1!
cd repos/arduinoP/arduino
echo "Current directory: $(pwd)"
echo "Running script with sudo..."
sudo python3 working_sms.py 2>&1
echo "Script completed with exit code: $?"
ENDSSH
