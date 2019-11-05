# Bibliotecas de Interface com Usuário
from yaspin import yaspin
from pyfiglet import Figlet
from termcolor import colored
from yaspin.spinners import Spinners

# Bibliotecas para Paralelismo, Processamento e Comunicação
from time import sleep
from serial import Serial
from threading import Thread
from chronometer import Chronometer

# Bibliotecas para AI e Tratamento / Exibição de Dados
import numpy as numpy
from sklearn import metrics 
from sklearn.cluster import DBSCAN

DEFAULT_STATION_BAUDRATE : int = 9600           # Baudrate Padrão para Comunicação Serial ou Bluetooth com os Slaves das Estações.
DEFAULT_SUPERVISOR_BAUDRATE : int = 4800        # Baudrate Padrão para Comunicação Serial ou Bluetooth com o Slave Supervisor.

DEFAULT_STATION_PORT : str = "/dev/ttyS3"       # Porta Padrão para Comunicação Serial ou Bluetooth com os Slaves das Estações.
DEFAULT_SUPERVISOR_PORT : str = "/dev/ttyS4"    # Porta Padrão para Comunicação Serial ou Bluetooth com o Slave Supervisor.

DATASET_FILE_PATH : str = "dataset.txt"     # Arquivo nos quais estão contidos os dados para feed no Algoritmo DBSCAN.

timerStation : Chronometer = Chronometer()  # Cronômetro para o Tempo gasto em cada Estação.

stationThread : Thread = NotImplemented     # Thread que executa a Await-For-Response do Arduino das Estações.
controlThread : Thread = NotImplemented     # Thread que controla a Await-For-Response para parada, enquanto a `stationThread` está ocupada com o DBSCAN.

isRunning : bool = False    # Indica o estado de execução do parâmetro para os laços das Threads.

#   Limit = Average + STD * Threshold   ->  Limite para Suspeitar Anomalia.
threshold : float = 1   # Threshold - Parâmetro que multiplica o corte de desvio médio.
avg : float = 1         # Average   - Média dos valores de tempo do Dataset.
std : float = 0.5       # STD       - Desvio Padrão dos valores de tempo do Dataset.

eps : float = 0.3   # Parâmetro Epsilon para o DBSCAN.

lambdaAcc : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Acidentes".
lambdaLck : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Falta de Materiais".
lambdaMal : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Equipamentos com Mau Funcionamento".

def isOutlier(elapsedTime : float) -> bool:
    raw_data = open(DATASET_FILE_PATH, 'rt')
    dataset = numpy.loadtxt(raw_data, delimiter=",")

    insertion = numpy.append(dataset, [[elapsedTime, 0]], axis = 0)

    dbscan = DBSCAN(eps = 0.3, min_samples = 10).fit(insertion)
    labels = dbscan.labels_

    return labels[insertion.size//2 - 1] == -1

def loadParameters():
    return NotImplemented

def saveParameters():
    return NotImplemented

def t_StationThread(stationID : int, stationPort : str, stationBaudrate : int): 
    stationPort : Serial = Serial(port = stationPort, baudrate = stationBaudrate)

    while isRunning:
        if timerStation.started:
            if timerStation.elapsed > (average + threshold * std):   
                if isOutlier(timerStation.elapsed):
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


def t_ControlThread(stationID : int, stationPort : str, stationBaudrate : int):
    return NotImplemented

if __name__ == "__main__":
    figlet = Figlet(font = "slant")
    print(figlet.renderText('Labrador'))
    print("Bem-vindo ao ", colored("Sistema de Gerenciamento e Aquisição de Dados", "cyan"), "Customizado para a", colored("Fábrica do Futuro - Escola Politécnica da Universidade de São Paulo", "yellow"))
    print('')

    with yaspin(Spinners.bouncingBall, text = "Carregando Comunicação com as Estações...", color = "blue") as loader:
        stationThread = Thread(target = t_StationThread, daemon = True, args = (0, DEFAULT_STATION_PORT, DEFAULT_STATION_BAUDRATE))
        sleep(3)
        loader.ok("> OK ")

    with yaspin(Spinners.bouncingBall, text = "Carregando os Arquivos de Configuração...", color = "yellow") as loader:
        sleep(3)
        loader.ok("> OK ")

    print("\nEntre com", colored("help", "cyan", attrs = ["underline"]), "para ver comandos e outros funcionalidades.")

    isRunning = True
    stationThread.start()

    print('')

    while isRunning:
        print("Entre com um comando:", end = " ")
        command = input()
        
        if command == "quit":
            isRunning = False
        elif command == "help":
            print("\nLista de comandos disponíveis:")
            print("\t-", colored("help", "cyan"), ": Exibe esta informação, com os comandos disponíveis.")
            print("\t-", colored("quit", "red"), ": Finaliza a execução do sistema.\n")
        else:
            print(colored("Este comando não foi reconhecido!\n", "white", "on_red"))
    