import numpy as numpy
import pandas as pandas
from sklearn import metrics 
from sklearn.cluster import DBSCAN
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

errorset = pandas.read_csv("errorset.csv", header = None, names = ['time', 'presence', 'label'])
X = errorset[['time', 'presence']]
Y = errorset.label

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size = 0.3, random_state = 1)

clf = DecisionTreeClassifier()
clf = clf.fit(X_train, Y_train)
Y_pred = clf.predict(X_test)

print("Acc: ", metrics.accuracy_score(Y_test, Y_pred))