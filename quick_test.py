import serial,time,sys
try:
 s=serial.Serial('/dev/ttyS0',115200,timeout=2)
 s.write(b'AT\r\n');time.sleep(1)
 r=s.read(100);print(f"Response: {r}")
 if b'OK' in r:
  s.write(b'AT+CMGF=1\r\n');time.sleep(1);s.read(100)
  s.write(b'AT+CMGS="+306976518415"\r');time.sleep(2)
  s.write(b'Test SMS\x1A');time.sleep(10)
  print(f"SMS Result: {s.read(200)}")
 s.close()
except Exception as e:print(e)
