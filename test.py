from serial import Serial

stationPort = Serial(port = "/dev/ttyS5", baudrate = 4800)
    

while True:
    stationPort.write(b"emergency\n\0")