#!/usr/bin/env python3
import subprocess
import os

print("Deploying files to Raspberry Pi...")

# Files to copy
files = ["test_modem.py", "firstTry_fixed.py"]

# First, let's create the files locally from fix_sms.sh
os.system("bash fix_sms.sh")

# Try to copy using scp with password
pi_host = "jstaras@192.168.1.48"
pi_path = "/repos/arduino/"

for file in files:
    if os.path.exists(file):
        print(f"Copying {file} to Pi...")
        # This will prompt for password
        cmd = f"scp {file} {pi_host}:{pi_path}"
        print(f"Running: {cmd}")
        print("Enter password when prompted: Saskatouraw1!")
        subprocess.run(cmd, shell=True)
    else:
        print(f"File {file} not found")

print("\nFiles copied! Now SSH to your Pi with:")
print("ssh jstaras@192.168.1.48")
print("Password: Saskatouraw1!")
print("\nThen run:")
print("cd /repos/arduino")
print("sudo python3 test_modem.py")
print("sudo python3 firstTry_fixed.py")