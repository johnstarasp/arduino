#!/bin/bash

# Simple SMS sending script for SIM7070G
PORT="/dev/serial0"
BAUD="115200"
PHONE="+306976518415"
MESSAGE="Test SMS from Pi"

echo "Testing SIM7070G module..."

# Function to send AT command
send_at() {
    echo -e "$1\r" > $PORT
    sleep 2
}

# Configure serial port
stty -F $PORT $BAUD cs8 -cstopb -parenb raw -echo

# Test AT
echo "Testing AT command..."
send_at "AT"
sleep 1

# Disable echo
send_at "ATE0"

# Check SIM
echo "Checking SIM..."
send_at "AT+CPIN?"
sleep 2

# Set text mode
echo "Setting SMS text mode..."
send_at "AT+CMGF=1"

# Send SMS
echo "Sending SMS to $PHONE..."
echo -e "AT+CMGS=\"$PHONE\"\r" > $PORT
sleep 2

# Send message text and Ctrl+Z
echo -n "$MESSAGE" > $PORT
echo -e "\x1A" > $PORT

echo "Waiting for response..."
sleep 10

echo "Done!"
