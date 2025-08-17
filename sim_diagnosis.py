#!/usr/bin/env python3
"""
Comprehensive SIM Diagnosis and SMS Center Fix
Sets correct SMS center to +3097100000 and diagnoses SIM issues
"""
import serial
import time

def send_at(ser, cmd, wait=2):
    """Send AT command and return response"""
    ser.reset_input_buffer()
    ser.write(f"{cmd}\r\n".encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting or 300).decode('utf-8', errors='ignore')
    print(f"{cmd}: {response.strip()}")
    return response

def comprehensive_sim_check():
    print("=== COMPREHENSIVE SIM DIAGNOSIS ===")
    print("Setting correct SMS center to +3097100000")
    
    try:
        # Connect to module
        ser = serial.Serial('/dev/serial0', 57600, timeout=5)
        time.sleep(2)
        
        # Test basic connection
        resp = send_at(ser, "AT", 1)
        if "OK" not in resp:
            print("❌ Module not responding")
            return False
        
        print("\n1. BASIC MODULE INFO")
        send_at(ser, "ATI")           # Module info
        send_at(ser, "AT+CGMM")       # Model
        send_at(ser, "AT+CGMR")       # Firmware
        send_at(ser, "AT+CGSN")       # IMEI
        
        print("\n2. SIM CARD DETAILED DIAGNOSIS")
        send_at(ser, "AT+CPIN?")      # SIM PIN status
        send_at(ser, "AT+CCID")       # SIM card ID (ICCID)
        send_at(ser, "AT+CIMI")       # International Mobile Subscriber Identity
        send_at(ser, "AT+CNUM")       # Own phone number (if stored)
        
        # Check if SIM is properly recognized
        cpin_resp = send_at(ser, "AT+CPIN?", 2)
        if "READY" not in cpin_resp:
            print("⚠️  SIM CARD ISSUE: Not ready!")
            if "SIM PIN" in cpin_resp:
                print("   SIM requires PIN")
            elif "SIM PUK" in cpin_resp:
                print("   SIM is PUK locked")
            elif "SIM NOT INSERTED" in cpin_resp:
                print("   SIM not inserted properly")
            return False
        else:
            print("✅ SIM card is ready")
        
        print("\n3. NETWORK REGISTRATION")
        send_at(ser, "AT+CREG?")      # Network registration
        send_at(ser, "AT+COPS?")      # Current operator
        send_at(ser, "AT+CSQ")        # Signal quality
        
        # Check network registration
        creg_resp = send_at(ser, "AT+CREG?", 2)
        if "+CREG: 0,1" in creg_resp or "+CREG: 0,5" in creg_resp:
            print("✅ Registered on network")
        else:
            print("⚠️  NETWORK ISSUE: Not registered!")
            print("   Checking available operators...")
            send_at(ser, "AT+COPS=?", 30)  # Scan for operators (takes time)
            return False
        
        print("\n4. SMS SERVICE CENTER CONFIGURATION")
        
        # Check current SMSC
        current_smsc = send_at(ser, "AT+CSCA?", 2)
        print(f"Current SMS center: {current_smsc}")
        
        # Set correct SMSC to +3097100000
        print("Setting SMS center to +3097100000...")
        smsc_result = send_at(ser, 'AT+CSCA="+3097100000"', 3)
        
        if "OK" in smsc_result:
            print("✅ SMS center set successfully")
        else:
            print(f"❌ Failed to set SMS center: {smsc_result}")
            return False
        
        # Verify it was set
        verify_smsc = send_at(ser, "AT+CSCA?", 2)
        if "+3097100000" in verify_smsc:
            print("✅ SMS center verified: +3097100000")
        else:
            print(f"❌ SMS center verification failed: {verify_smsc}")
        
        print("\n5. SMS CONFIGURATION")
        send_at(ser, "AT+CMGF=1")     # Set text mode
        send_at(ser, "AT+CPMS?")      # Current SMS storage
        send_at(ser, "AT+CPMS=\"SM\",\"SM\",\"SM\"")  # Set SMS storage to SIM
        send_at(ser, "AT+CPMS?")      # Verify SMS storage
        send_at(ser, "AT+CNMI?")      # SMS indication settings
        
        print("\n6. SMS CAPABILITY TEST")
        send_at(ser, "AT+CMEE=2")     # Enable verbose errors
        
        # Test SMS sending capability
        print("Testing SMS prompt...")
        ser.reset_input_buffer()
        ser.write(b'AT+CMGS="+306980531698"\r')
        time.sleep(3)
        prompt_resp = ser.read(200)
        print(f"SMS prompt test: {prompt_resp}")
        
        if b'>' in prompt_resp:
            print("✅ SMS prompt working - sending test message")
            ser.write(b'SIM diagnosis test - SMS center fixed to +3097100000\x1A')
            time.sleep(15)
            sms_result = ser.read(300).decode('utf-8', errors='ignore')
            print(f"SMS result: {sms_result}")
            
            if "+CMGS" in sms_result:
                print("🎉 SMS SENT SUCCESSFULLY!")
                print("✅ SIM and SMS center are working correctly")
                success = True
            elif "CMS ERROR" in sms_result:
                error_code = sms_result.split("CMS ERROR:")[1].strip().split()[0] if "CMS ERROR:" in sms_result else "unknown"
                print(f"❌ CMS ERROR {error_code}")
                if error_code == "500":
                    print("   Still getting 500 - possible SIM activation issue")
                elif error_code == "330":
                    print("   SMSC address unknown - trying alternative")
                success = False
            else:
                print("❌ Unknown SMS response")
                success = False
        else:
            print("❌ No SMS prompt - SIM may have SMS restrictions")
            if b"CMS ERROR" in prompt_resp:
                error = prompt_resp.decode().split("CMS ERROR:")[1].strip() if "CMS ERROR:" in prompt_resp.decode() else "unknown"
                print(f"   CMS ERROR: {error}")
            success = False
        
        print("\n7. SIM TROUBLESHOOTING SUMMARY")
        if success:
            print("✅ SIM diagnosis PASSED")
            print("✅ SMS center correctly set to +3097100000") 
            print("✅ SMS functionality working")
        else:
            print("❌ SIM diagnosis FAILED")
            print("\nPossible issues:")
            print("1. SIM card is new and needs 24-48h activation")
            print("2. SMS service not enabled on this SIM plan")
            print("3. SIM card is faulty or incompatible")
            print("4. Network operator issues")
            print("5. Try different SMS center number")
            print("\nTry these SMS centers:")
            print("   COSMOTE: +306942000000")
            print("   WIND: +306977000000") 
            print("   VODAFONE: +306945000000")
        
        ser.close()
        return success
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        return False

if __name__ == "__main__":
    comprehensive_sim_check()