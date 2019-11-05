from chronometer import Chronometer
from threading import Thread
from time import sleep
from pyfiglet import Figlet
from yaspin import yaspin
from yaspin.spinners import Spinners
from serial import Serial

import numpy as numpy
from sklearn.cluster import DBSCAN
from sklearn import metrics 

DEFAULT_STATION_BAUDRATE : int = 9600
DEFAULT_SUPERVISOR_BAUDRATE : int = 4800

DEFAULT_STATION_PORT : int = 3
DEFAULT_SUPERVISOR_PORT : int = 4

isRunning : bool = False    # Flag de Execucao

lambdaAcc : float = 0.5     # Lambda distribuicao Poisson para Acidentes
lambdaLck : float = 0.5     # Lambda distribuicao Poisson para Falta de Materiais
lambdaMal : float = 0.5     # Lambda distribuicao Poisson para Equipamentos Defeituosos

timerStation : Chronometer = Chronometer()  # Timer para cronometrar o tempo nas estacoes

stationThread : Thread = NotImplemented
controlThread : Thread = NotImplemented

threshold : float = 2
average : float = 6.7
std : float = 0.7
eps : float = 0.3

def t_StationThread(stationID : int, stationPort : int, stationBaudrate : int): 
    stationPort : Serial = Serial(port = "/dev/ttyS" + str(stationPort), baudrate = stationBaudrate)

    while isRunning:
        if timerStation.started:
            if timerStation.elapsed > (average + threshold * std):   
                dataset = numpy.genfromtxt("dbscan_dataset.csv", delimiter = ',')
                dbscan = DBSCAN(eps = eps, min_samples = 10).fit(dataset)

                core_samples = numpy.zeros_like(dbscan.labels_, dtype = bool)
                core_samples[dbscan.core_sample_indices] = True 
                labels = dbscan.labels_

                if labels[dataset.size//2 - 1] == -1:
                    pass
                else:
                    sleep(0.2)
                
        else:
            stationMessage = stationPort.readline()
            
            if stationMessage:
                try:
                    decodedMessage = codecs.decode(stationMessage, "ascii")

                    if (decodedMessage == "start"):
                        controlThread = Thread(target = t_ControlThread, daemon = True, args=(0, DEFAULT_SUPERVISOR_PORT, DEFAULT_SUPERVISOR_BAUDRATE))
                        controlThread.start()
                        timerStation.start()
                except:
                    print("A message was received but could not be interpreted by Codecs decoder. Please send again.")
                    sleep(0.1)
                    pass        


def t_ControlThread(stationID : int, stationPort : int, stationBaudrate : int):
    return NotImplemented

if __name__ == "__main__":
    figlet = Figlet(font = "slant")
    print(figlet.renderText('Manager'))
    print("Welcome to the custom management system for Fabrica do Futuro - Escola Politecnica da Universidade de Sao Paulo")

    with yaspin(Spinners.bouncingBall, text = "Carregando comunicacao com estacao", color = "blue") as loader:
        stationThread = Thread(target = t_StationThread, daemon = True, args = (0, DEFAULT_STATION_PORT, DEFAULT_STATION_BAUDRATE))
        sleep(1)
        loader.ok("> OK ")

    isRunning = True

    