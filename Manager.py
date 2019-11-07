# Bibliotecas de Interface com Usuário
from yaspin import yaspin
from pyfiglet import Figlet
from termcolor import colored
from yaspin.spinners import Spinners

# Bibliotecas para Paralelismo, Processamento e Comunicação
import json
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

eventRoutine : bool = False     # Flag para input de comandos.

isRunning : bool = False    # Indica o estado de execução do parâmetro para os laços das Threads.
isControlActive : bool = False   # Indica o estado da Thread de Controle.

stationPort : Serial = None     # Entrada de Comunicação Serial da Estação.
supervisorPort : Serial = None  # Entrada de Comunicação Serial do Supervisor.

#   Limit = Average + STD * Threshold   ->  Limite para Suspeitar Anomalia.
threshold : float = 1   # Threshold - Parâmetro que multiplica o corte de desvio médio.
avg : float = 4        # Average   - Média dos valores de tempo do Dataset.
std : float = 0.5       # STD       - Desvio Padrão dos valores de tempo do Dataset.

eps : float = 0.3   # Parâmetro Epsilon para o DBSCAN.
samples : int = 10  # Parametro min_samples para o DBSCAN.

lambdaAcc : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Acidentes".
lambdaLck : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Falta de Materiais".
lambdaMal : float = 0.5     # Parâmetro Lambda da Distribuição de Poisson para Anomalias do tipo "Equipamentos com Defeituosos".

happenedAcc : int = 0       # Número de eventos do tipo "Acidentes" no dia.
happenedLck : int = 0       # Número de eventos do tipo "Falta de Materiais" no dia.
happenedMal : int = 0       # Número de eventos do tipo "Equipamentos Defeituosos" no dia.

acc : float = 0     # Accuracy da Decision Tree Model.

sessionNumber : int = 1     # Número de dias passados.

def isOutlier(elapsedTime : float) -> bool:
    """
        Executa o algoritmo DBSCAN para verificar se um ponto é uma anomalia (outlier)
        dado um conjunto de pontos já obtidos pela coleta sucessiva de dados na fábrica.
    """
    raw_data = open(DATASET_FILE_PATH, 'rt')
    dataset = numpy.loadtxt(raw_data, delimiter=",")

    insertion = numpy.append(dataset, [[elapsedTime, 0]], axis = 0)

    dbscan = DBSCAN(eps = eps, min_samples = samples).fit(insertion)
    labels = dbscan.labels_

    return labels[insertion.size//2 - 1] == -1

def plot():
    """
        Faz uma exibição gráfica dos pontos coletados para o DBSCAN usando a biblioteca
        Matplotlib através do comando plot.
    """
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
    plotter.title("Gráfico - Resultados DBSCAN") 
    plotter.show()

def trainTree():
    """
        Treina o modelo de Decision Tree.
    """
    global acc

    errorset = pandas.read_csv("errorset.csv", header = None, names = ['time', 'presence', 'label'])
    X = errorset[['time', 'presence']]
    Y = errorset.label

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size = 0.3, random_state = 1)

    clf = DecisionTreeClassifier()
    clf = clf.fit(X_train, Y_train)
    Y_pred = clf.predict(X_test)
    acc = metrics.accuracy_score(Y_test, Y_pred)

def probability(parameter : float, k : int) -> float:
    """
        Calcula a probabilidade de Poisson para k eventos ocorrem num intervalo de 1 session
        dado o parâmetro lambda registrado (frequência de ocorrências já obtida).
    """
    return (exp(-parameter) * (parameter ** k)) / factorial(k)

def loadParameters():
    """
        Carrega os parâmetros de utilização salvos em um arquivo JSON.
    """
    global lambdaAcc
    global lambdaLck
    global lambdaMal

    global eps
    global samples
    global threshold
    global std
    global avg 

    global sessionNumber

    with open('cfg.json') as file:
        data = json.load(file)
        
        lambdaAcc = data['lambdas'][0]['acc']
        lambdaLck = data['lambdas'][0]['lck']
        lambdaMal = data['lambdas'][0]['mal']

        eps = data['dbscan'][0]['eps']
        samples = data['dbscan'][0]['samples']
        threshold = data['dbscan'][0]['threshold']
        avg = data['dbscan'][0]['avg']
        std = data['dbscan'][0]['std']
        
        sessionNumber = data['happens'][0]['ses']


def saveParameters():
    """
        Salva os parâmetros calculados em um arquivo JSON.
    """
    global sessionNumber   

    sessionNumber = sessionNumber + 1

    raw_data = open(DATASET_FILE_PATH, 'rt')
    dataset = numpy.ma.masked_equal(numpy.loadtxt(raw_data, delimiter=","), 0)

    average = numpy.mean(dataset)
    stDeviation = numpy.std(dataset)

    savedData = {}
    savedData['lambdas'] = []
    savedData['lambdas'].append({
        'acc': lambdaAcc,
        'lck': lambdaLck,
        'mal': lambdaMal,
    })

    savedData['dbscan'] = []
    savedData['dbscan'].append({
        'eps': eps,
        'samples': samples,
        'threshold': threshold,
        'avg': average,
        'std': stDeviation
    })   

    savedData['happens'] = []
    savedData['happens'].append({
        'ses': sessionNumber
    })

    with open('cfg.json', 'w') as file:
        json.dump(savedData, file)

def t_StationThread(): 
    """
        Thread que opera a comunicação e inteligência do Arduino na estação.
    """
    global isControlActive
    global happenedAcc
    global happenedLck
    global happenedMal
    global lambdaAcc
    global lambdaLck
    global lambdaMal
    global eventRoutine

    while isRunning:
        if timerStation.started:
            if timerStation.elapsed > (avg + threshold * std):
                if isOutlier(timerStation.elapsed):
                    isControlActive = False

                    probAcc : float = probability(parameter = lambdaAcc, k = happenedAcc + 1)
                    probLck : float = probability(parameter = lambdaLck, k = happenedLck + 1)
                    probMal : float = probability(parameter = lambdaMal, k = happenedMal + 1)

                    classification : str = ""
                    label : str = ""

                    if probAcc < probLck < probMal or probLck < probAcc < probMal:
                        classification = "Equipamento Defeituoso"
                        label = "mal"
                    elif probMal < probLck < probAcc or probLck < probMal < probAcc:
                        classification = "Acidente"
                        label = "acc"
                    else:
                        classification = "Falta de Peças"
                        label = "lack"
                    
                    print("\n", colored("ATENÇÃO", 'red'), " um problema foi encontrado na linha produtiva na estação 0. A classificação aponta a ocorrência de ",
                            classification, ". Recomenda-se a verificação.\n")

                    timerStation.stop()
                    stationPort.write(b"stop\n\0")

                    sleep (1)

                    print(colored("Classificador:", 'yellow'), "Qual o problema obtido? (0 - Falso Positivo, 1 -", colored("Acidente", 'red'), ", 2 - ", colored("Falta de Peças", 'cyan'), ", 3 - ", colored("Ferramentas com Problemas", 'yellow'), ") ?")
                    print("\nEntre com", colored('event', 'cyan'), " (ENTER) ", colored('X', 'cyan'), "para responder: ", end = '')
                    
                    eventRoutine = True
                    event = input()

                    print('')   

                    with yaspin(Spinners.bouncingBall, text = "Processando...", color = "blue") as loader:
                        sleep(2)
                        if event == '1':
                            happenedAcc = happenedAcc + 1
                            lambdaAcc = (lambdaAcc * sessionNumber + happenedAcc) / (sessionNumber) 
                        elif event == '2':
                            happenedLck = happenedLck + 1
                            lambdaLck = (lambdaAcc * sessionNumber + happenedLck) / (sessionNumber + 1) 
                        elif event == '3':
                            happenedMal = happenedMal + 1
                            lambdaMal = (lambdaAcc * sessionNumber + happenedMal) / (sessionNumber + 1) 
                        elif event == '0':
                            dataset = open(DATASET_FILE_PATH, 'a+')
                            dataset.write(str(round(timerStation.elapsed, 5)) + ",0\n")
                            dataset.close()
                            loader.write("A ocorrência de falsos positivos é normal quando o modelo está pouco treinado.")
                        loader.ok("> OK")
                        
                        if event != "0":
                            errorset = open(ERRORSET_FILE_PATH, 'a+')

                            supervisorPort.write("#r")
                            answer = supervisorPort.readline()

                            presence = float(answer)

                            errorset.write('"' + str(timerStation.elapsed) + '","' + str(presence)+'","' + label + '"')
                            errorset.close()
                    
                    print('')
                    timerStation.reset()
                    eventRoutine = False
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
    """
        Thread que substitui a Station Thread enquanto o comando Stop não for recebido.
    """
    global isControlActive

    stationPort.timeout = 1
    while isControlActive:
        stationMessage = stationPort.readline()   
        if stationMessage:
            try:
                decodedMessage = codecs.decode(stationMessage, "ascii")

                if decodedMessage == "stop\r\n":
                    print("\nA", colored("Estação 0", "cyan"), "teve sua conexão encerrada.")
                    timerStation.stop()
                    
                    dataset = open(DATASET_FILE_PATH, 'a+')
                    dataset.write(str(round(timerStation.elapsed, 5)) + ",0\n")
                    dataset.close()

                    timerStation.reset()

                    isControlActive = False
            except NameError as e:
                print(e)
    stationPort.timeout = None


if __name__ == "__main__":
    """
        Main Thread
    """
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
            supervisorPort : Serial = Serial(port = DEFAULT_SUPERVISOR_PORT, baudrate = DEFAULT_SUPERVISOR_BAUDRATE)
        except Exception as exp:
            loader.fail("ERRO")
            loader.write("Uma exceção foi lançada ao tentar inicializar as portas seriais: \n\t" + str(exp))
            quit()
        sleep(1)
        loader.ok("> OK ")

    with yaspin(Spinners.bouncingBall, text = "Carregando os Arquivos de Configuração...", color = "yellow") as loader:
        loadParameters()
        sleep(2)
        loader.ok("> OK ")

    print("\nEntre com", colored("help", "cyan", attrs = ["underline"]), "para ver comandos e outros funcionalidades.")

    chronometerLock = Lock()
    stopLock = Lock()

    stationThread.start()

    print('')

    while isRunning:
        if not eventRoutine:
            print("Entre com um comando:", end = " ")
            command = input()
            
            if command == "quit":
                saveParameters()
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
                print("\n\tAccuracy: ", acc)
                print('')
            elif command == "help":
                print("\nLista de comandos disponíveis:")
                print("\t-", colored("help", "cyan"), ": Exibe esta informação, com os comandos disponíveis.")
                print("\t-", colored("train", "red"), ": ?")
                print("\t-", colored("plot", "yellow"), ": Exibe o gráfico produzido pelo DBSCAN.")
                print("\t-", colored("models", "magenta"), ": Exibe os parâmetros dos modelos de AI.")
                print("\t-", colored("quit", "red"), ": Finaliza a execução do sistema.\n")
            elif command == "event":
                continue
            else:
                print(colored("Este comando não foi reconhecido!\n", "white", "on_red"))
    stationPort.close()
    supervisorPort.close()