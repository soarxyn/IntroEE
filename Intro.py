from serial import Serial

stationPort : Serial = Serial(port = "COM13", baudrate = 9600)

while True:
    stationMessage = stationPort.readline()
    print(stationMessage)