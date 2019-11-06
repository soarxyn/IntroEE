# Bibliotecas de Interface com Usuário
from yaspin import yaspin
from pyfiglet import Figlet
from termcolor import colored
from yaspin.spinners import Spinners

import sys

# Bibliotecas para Paralelismo, Processamento e Comunicação
import codecs
from time import sleep
from serial import Serial
from threading import Lock
from threading import Thread
from chronometer import Chronometer

# Bibliotecas para AI e Tratamento / Exibição de Dados
from math import exp
import numpy as numpy
import pandas as pandas
from math import factorial
from sklearn import metrics 
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plotter
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

DEFAULT_STATION_BAUDRATE : int = 9600           # Baudrate Padrão para Comunicação Serial ou Bluetooth com os Slaves das Estações.
DEFAULT_SUPERVISOR_BAUDRATE : int = 4800        # Baudrate Padrão para Comunicação Serial ou Bluetooth com o Slave Supervisor.

DEFAULT_STATION_PORT : str = "COM13"       # Porta Padrão para Comunicação Serial ou Bluetooth com os Slaves das Estações.
DEFAULT_SUPERVISOR_PORT : str = "/dev/ttyS4"    # Porta Padrão para Comunicação Serial ou Bluetooth com o Slave Supervisor.

DATASET_FILE_PATH : str = "dataset.txt"     # Arquivo nos quais estão contidos os dados para feed no Algoritmo DBSCAN.
ERRORSET_FILE_PATH : str = "errorset.csv"   # Arquivo de armazenamento dos erros encontrados para feed no modelo de classificação Decision Tree.

timerStation : Chronometer = Chronometer()  # Cronômetro para o Tempo gasto em cada Estação.

stationThread : Thread = None     # Thread que executa a Await-For-Response do Arduino das Estações.
controlThread : Thread = None     # Thread que controla a Await-For-Response para parada, enquanto a `stationThread` está ocupada com o DBSCAN.

chronometerLock : Lock = None
stopLock : Lock = None

isRunning : bool = False    # Indica o estado de execução do parâmetro para os laços das Threads.
isControlActive : bool = False   # ioandio

stationPort : Serial = None

#   Limit = Average + STD * Threshold   ->  Limite para Suspeitar Anomalia.
threshold : float = 1   # Threshold - Parâmetro que multiplica o corte de desvio médio.
avg : float = 4        # Average   - Média dos valores de tempo do Dataset.
std : float = 0.5       # STD       - Desvio Padrão dos valores de tempo do Dataset.

eps : float = 0.3   # Parâmetro Epsilon para o DBSCAN.
samples : int = 10  # Parametro min_samples para o DBSCAN.

lambdaAcc : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Acidentes".
lambdaLck : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Falta de Materiais".
lambdaMal : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Equipamentos com Mau Funcionamento".

happenedAcc : int = 0
happenedLck : int = 0
happenedMal : int = 0

sessionNumber : int = 1

def isOutlier(elapsedTime : float) -> bool:
    raw_data = open(DATASET_FILE_PATH, 'rt')
    dataset = numpy.loadtxt(raw_data, delimiter=",")

    insertion = numpy.append(dataset, [[elapsedTime, 0]], axis = 0)

    dbscan = DBSCAN(eps = eps, min_samples = samples).fit(insertion)
    labels = dbscan.labels_

    return labels[insertion.size//2 - 1] == -1

def plot():
    raw_data = open(DATASET_FILE_PATH, 'rt')
    dataset = numpy.loadtxt(raw_data, delimiter=",")

    dbscan = DBSCAN(eps = eps, min_samples = samples).fit(dataset)
    core_samples = numpy.zeros_like(dbscan.labels_, dtype=bool)
    core_samples[dbscan.core_sample_indices_] = True
    labels = dbscan.labels_

    unique_labels = set(labels)
    colors = ['y', 'b', 'g', 'r']

    for k, col in zip(unique_labels, colors):
        if k == -1:
            col = 'k'   

        class_member = (labels == k)

        xy = dataset[class_member & core_samples] 
        plotter.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col, 
                                        markeredgecolor='k',  
                                        markersize=6) 
    
        xy = dataset[class_member & ~core_samples] 
        plotter.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=col, 
                                        markeredgecolor='k', 
                                        markersize=6) 
    plotter.title("Grafico") 
    plotter.show()

def probability(parameter : float, k : int) -> float:
    return (exp(-parameter) * (parameter ** k)) / factorial(k)

def loadParameters():
    return NotImplemented

def saveParameters():
    return NotImplemented

def t_StationThread(): 
    global isControlActive
    global happenedAcc
    global happenedLck
    global happenedMal

    while isRunning:
        if timerStation.started:
            if timerStation.elapsed > (avg + threshold * std):
                if isOutlier(timerStation.elapsed):
                    isControlActive = False

                    probAcc : float = probability(parameter = lambdaAcc, k = happenedAcc + 1)
                    probLck : float = probability(parameter = lambdaLck, k = happenedLck + 1)
                    probMal : float = probability(parameter = lambdaMal, k = happenedMal + 1)

                    supervisorPort : Serial = Serial(port = DEFAULT_SUPERVISOR_PORT, baudrate = DEFAULT_SUPERVISOR_BAUDRATE)

                    classification : str = ""

                    if probAcc < probLck < probMal or probLck < probAcc < probMal:
                        classification = "Equipamento Defeituoso"
                        happenedMal = happenedMal + 1
                    elif probMal < probLck < probAcc or probLck < probMal < probAcc:
                        classification = "Acidente"
                        happenedAcc = happenedAcc + 1
                    else:
                        classification = "Falta de Peças"
                        happenedLck = happenedLck + 1

                    # Use Decision Tree ( ? )

                    supervisorPort.close()

                    print("\n", colored("ATENÇÃO", 'red'), " um problema foi encontrado na linha produtiva na estação 0. A classificação aponta a ocorrência de ",
                            classification, ". Recomenda-se a verificação.\n")

                    timerStation.stop()
                    timerStation.reset()

                    stationPort.write(b"stop\n\0")
                    sleep(0.1)
                else:
                    sleep(0.2)
        else:
            stationMessage = stationPort.readline()

            if stationMessage:
                try:
                    decodedMessage = codecs.decode(stationMessage, "ascii")
                    
                    if decodedMessage == "start\r\n" or "art" in decodedMessage:
                        print("\n\nUma conexão foi estabelecida com a", colored("Estação 0!", "cyan"))

                        sleep(0.8)

                        controlThread = Thread(target = t_ControlThread, daemon = True)
                        isControlActive = True
                        controlThread.start()
                        timerStation.start() 
                    elif decodedMessage == "emergency\r\n" or "rgen" in decodedMessage:
                        print(colored("\n\nO BOTÃO DE EMERGÊNCIA FOI PRESSIONADO NA ESTAÇÃO 0!", "white", "on_red"))
                        supervisorPort.write(b"emergency\n\0")
                        
                except:
                    print("Uma mensagem foi recebida mas não foi possivel interpretá-la com Codecs decoder. Por favor, envie novamente.")
                    sleep(0.1)


def t_ControlThread():
    global isControlActive

    stationPort.timeout = 1
    while isControlActive:
        stationMessage = stationPort.readline()   
        if stationMessage:
            try:
                decodedMessage = codecs.decode(stationMessage, "ascii")

                if decodedMessage == "stop\r\n":
                    with chronometerLock:
                        print("\nA", colored("Estação 0", "cyan"), "teve sua conexão encerrada.")
                        timerStation.stop()
                        
                        dataset = open("dataset.txt", 'a+')
                        dataset.write(str(round(timerStation.elapsed, 5)) + ",0\n")
                        dataset.close()

                        timerStation.reset()

                        isControlActive = False
            except NameError as e:
                print(e)
    stationPort.timeout = None


if __name__ == "__main__":
    figlet = Figlet(font = "slant")
    print(colored(figlet.renderText('Labrador'), "cyan"))
    print("Bem-vindo ao", colored("Sistema de Gerenciamento e Aquisição de Dados", "cyan"), "Customizado para a", colored("Fábrica do Futuro - Escola Politécnica da Universidade de São Paulo", "yellow"))
    print('')

    isRunning = True
    controlRun = True

    with yaspin(Spinners.bouncingBall, text = "Carregando Comunicação com as Estações...", color = "blue") as loader:
        stationThread = Thread(target = t_StationThread, daemon = True)
        sleep(1)

        try:
            stationPort = Serial(port = DEFAULT_STATION_PORT, baudrate = DEFAULT_STATION_BAUDRATE)
            #supervisorPort : Serial = Serial(port = DEFAULT_SUPERVISOR_PORT, baudrate = DEFAULT_SUPERVISOR_BAUDRATE)
        except Exception as exp:
            loader.fail("ERRO")
            loader.write("Uma exceção foi lançada ao tentar inicializar as portas seriais: \n\t" + str(exp))
            quit()
        sleep(0.1)
        loader.ok("> OK ")

    with yaspin(Spinners.bouncingBall, text = "Carregando os Arquivos de Configuração...", color = "yellow") as loader:
        sleep(0.1)
        loader.ok("> OK ")

    print("\nEntre com", colored("help", "cyan", attrs = ["underline"]), "para ver comandos e outros funcionalidades.")

    chronometerLock = Lock()
    stopLock = Lock()

    stationThread.start()

    print('')

    while isRunning:
        print("Entre com um comando:", end = " ")
        command = input()
        
        if command == "quit":
            isRunning = False
        elif command == 'train':
            print("TRAIN")
        elif command == 'plot':
            plot()
        elif command == 'models':
            print("\nParâmetros de Execução dos Modelos de AI:\n")
            print("\tThreshold:", threshold)
            print("\tAverage: ", avg)
            print("\tStandard Deviation: ", std)
            print("\n\tEpsilon: ", eps)
            print("\tMin. Samples: ", samples)
            print("\n\tLambda Acidentes:", lambdaAcc)
            print("\tLambda Falta de Estoque:", lambdaLck)
            print("\tLambda Equipamento em Mal Funcionamento:", lambdaMal)
            print('\n')
        elif command == "help":
            print("\nLista de comandos disponíveis:")
            print("\t-", colored("help", "cyan"), ": Exibe esta informação, com os comandos disponíveis.")
            print("\t-", colored("train", "red"), ": ?")
            print("\t-", colored("plot", "yellow"), ": Exibe o gráfico produzido pelo DBSCAN.")
            print("\t-", colored("models", "magenta"), ": Exibe os parâmetros dos modelos de AI.")
            print("\t-", colored("quit", "red"), ": Finaliza a execução do sistema.\n")
        else:
            print(colored("Este comando não foi reconhecido!\n", "white", "on_red"))
    stationPort.close()
    supervisorPort.close()