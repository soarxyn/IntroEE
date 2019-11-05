import serial
import codecs
from time import sleep
import threading

isRunning = False

def reader():
    port = serial.Serial(port = "/dev/ttyS3", baudrate = 9600)

    while isRunning:
        msg = port.readline()
        if msg: 
            try:
                print("Received a message: 3", codecs.decode(msg, "ascii"))
            except:
                pass
        sleep (0.5)

def reader2():
    port = serial.Serial(port = "/dev/ttyS4", baudrate = 4800)

    while isRunning:
        msg = port.readline()
        if msg: 
            try:
                print("Received a message: 4", codecs.decode(msg, "ascii"))
            except:
                pass
        sleep (0.5)

if __name__ == "__main__":
    read = threading.Thread(target = reader, daemon = True)
    rr = threading.Thread(target=reader2, daemon=True)

    isRunning = True

    read.start()
    rr.start()

    while isRunning:
        print("Type a command: ")
        cmd = input()

        if cmd == "quit":
            isRunning = False
        elif cmd == "help":
            print("Type quit for exiting the program.")