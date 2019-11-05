import serial
import codecs
from time import sleep
import threading

isRunning = False

def reader():
    port = serial.Serial(port = "/dev/ttyS3")

    while isRunning:
        msg = port.readline()
        if msg: 
            try:
                print("Received a message: ", codecs.decode(msg, "ascii"))
            except:
                pass
        sleep (0.5)

if __name__ == "__main__":
    read = threading.Thread(target = reader, daemon = True)

    isRunning = True

    read.start()

    while isRunning:
        print("Type a command: ")
        cmd = input()

        if cmd == "quit":
            isRunning = False
        elif cmd == "help":
            print("Type quit for exiting the program.")