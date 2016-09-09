"""
Created on Tue Feb 23 12:01:21 2016

"""


import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from lasagne.layers import InputLayer, DropoutLayer, DenseLayer
from lasagne.updates import nesterov_momentum
from lasagne.objectives import binary_crossentropy
from lasagne.init import Uniform
from nolearn.lasagne import NeuralNet, BatchIterator
import theano
from theano import tensor as T
from theano.tensor.nnet import sigmoid


from sklearn.cross_validation import train_test_split 


from sklearn.metrics import roc_auc_score 
from sklearn.metrics import accuracy_score 
from sklearn.metrics import mean_squared_error
from sklearn.cross_validation import cross_val_score 

from sklearn.feature_selection import VarianceThreshold


class AdjustVariable(object):
    def __init__(self, name, start=0.03, stop=0.001):
        self.name = name
        self.start, self.stop = start, stop
        self.ls = None

    def __call__(self, nn, train_history):
        if self.ls is None:
            self.ls = np.linspace(self.start, self.stop, nn.max_epochs)

        epoch = train_history[-1]['epoch']
        new_value = np.float32(self.ls[epoch - 1])
        getattr(nn, self.name).set_value(new_value)


def preprocess_data(X, scaler=None):
    if not scaler:
        scaler = StandardScaler()       
        scaler.fit(X)
    X = scaler.transform(X)
    return X, scaler


        
def getDummiesInplace(columnList, train, test = None):
    #Takes in a list of column names and one or two pandas dataframes
    #One-hot encodes all indicated columns inplace
    columns = []
    
    if test is not None:
        df = pd.concat([train,test], axis= 0)
    else:
        df = train
        
    for columnName in df.columns:
        index = df.columns.get_loc(columnName)
        if columnName in columnList:
            dummies = pd.get_dummies(df.ix[:,index], prefix = columnName, prefix_sep = ".")
            columns.append(dummies)
        else:
            columns.append(df.ix[:,index])
    df = pd.concat(columns, axis = 1)
    
    if test is not None:
        train = df[:train.shape[0]]
        test = df[train.shape[0]:]
        return train, test
    else:
        train = df
        return train
        
def pdFillNAN(df, strategy = "mean"):
    #Fills empty values with either the mean value of each feature, or an indicated number
    if strategy == "mean":
        return df.fillna(df.mean())
    elif type(strategy) == int:
        return df.fillna(strategy)



train = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')

np.random.seed(3210)
train = train.iloc[np.random.permutation(len(train))]

#Drop target, ID, and v22(due to too many levels), and high correlated columns
labels = train["target"]
trainId = train["ID"]
testId = test["ID"]

#train.drop(labels = ["ID","target","v22","v107","v71","v31","v100","v63","v64"], axis = 1, inplace = True)
train.drop(['ID','target',"v22",'v8','v23','v25','v31','v36','v37','v46','v51','v53','v54','v63','v73','v75','v79','v81','v82','v89','v92','v95','v105','v107','v108','v109','v110','v116','v117','v118','v119','v123','v124','v128'],axis=1, inplace = True)

#train.drop(['ID','target',"v22"],axis=1, inplace = True)

#test.drop(labels = ["ID","v22","v107","v71","v31","v100","v63","v64"], axis = 1, inplace = True)
test.drop(labels = ["ID","v22",'v8','v23','v25','v31','v36','v37','v46','v51','v53','v54','v63','v73','v75','v79','v81','v82','v89','v92','v95','v105','v107','v108','v109','v110','v116','v117','v118','v119','v123','v124','v128'],axis=1, inplace = True)

#test.drop(labels = ["ID","v22"], axis =1 , inplace = True)

#find categorical variables
categoricalVariables = []
for var in train.columns:
    vector=pd.concat([train[var],test[var]], axis=0)
    typ=str(train[var].dtype)
    if (typ=='object'):
        categoricalVariables.append(var)


print ("Generating dummies...")
train, test = getDummiesInplace(categoricalVariables, train, test)

#Remove sparse columns
cls = train.sum(axis=0)
train = train.drop(train.columns[cls<10], axis=1)
test = test.drop(test.columns[cls<10], axis=1)

print ("Filling in missing values...")
fillNANStrategy = -1
#fillNANStrategy = "mean"
train = pdFillNAN(train, fillNANStrategy)
test = pdFillNAN(test, fillNANStrategy)


print ("Scaling...")
train, scaler = preprocess_data(train)
test, scaler = preprocess_data(test, scaler)


train = np.asarray(train, dtype=np.float32)        
labels = np.asarray(labels, dtype=np.int32).reshape(-1,1)




# Convert the data frame column into a single dim array 
print("Creating training set and validation set : 90 / 10 ")
X_train , X_valid , y_train , y_valid  = train_test_split(train , labels , test_size = 0.50 , random_state = 0 )

print("Opening model")
import cPickle as pickle

net = NeuralNet(
    layers=[  
        ('input', InputLayer),
        ('dropout0', DropoutLayer),
        ('hidden1', DenseLayer),
        ('dropout1', DropoutLayer),
        ('hidden2', DenseLayer),
        ('dropout2', DropoutLayer),
        ('hidden3', DenseLayer),
        ('dropout3', DropoutLayer),
        ('hidden4', DenseLayer),
        ('dropout4', DropoutLayer),

        ('hidden5', DenseLayer),
        ('output', DenseLayer),
        ],

    input_shape=(None, len(train[1])),
    dropout0_p=0.1,
    hidden1_num_units=250,
    dropout1_p=0.4,
    hidden2_num_units=180,
    dropout2_p=0.5,
    hidden3_num_units=100,
    dropout3_p=0.3,
    hidden4_num_units=40,
    dropout4_p=0.1,

    hidden5_num_units=25,

    output_nonlinearity=sigmoid,
    output_num_units=1, 
    update=nesterov_momentum,
    update_learning_rate=theano.shared(np.float32(0.01)),
    update_momentum=theano.shared(np.float32(0.9)),    
    # Decay the learning rate
    on_epoch_finished=[AdjustVariable('update_learning_rate', start=0.01, stop=0.0001),
                       AdjustVariable('update_momentum', start=0.9, stop=0.99),
                       ],
    regression=True,
    y_tensor_type = T.imatrix,                   
    objective_loss_function = binary_crossentropy,
    #batch_iterator_train = BatchIterator(batch_size = 256),
    max_epochs=50, 
    eval_size=0.1,
    #train_split =0.0,
    verbose=2,
    )

with open('./model/neural_net__fea_ext_250_150_80_25_drop__100_epoch.pkl' , 'rb') as pickle_file:
    est_model = pickle.load(pickle_file)

net.load_weights_from(est_model)
net.initialize()


print(" Validate Model ")
pred_valid_y = net.predict_proba(X_valid)[:,0]

mse = mean_squared_error(y_valid,pred_valid_y)
print("MSE : %.4f" % mse)

roc = roc_auc_score(y_valid,pred_valid_y)
print("ROC : %.4f" % roc)

print("Saving the response from train set")
y_pred = net.predict(train)
pd.DataFrame({"ID": trainId, "PredictedProb": y_pred[:,0] }).to_csv('./ver4/train_net_ds_2_250_150_80_25__100.csv' , index = False)

print("Saving the response from test set")
y_pred = net.predict(test)
pd.DataFrame({"ID": testId, "PredictedProb": y_pred[:,0] }).to_csv('./ver4/test_net_ds_2_250_150_80_25__100.csv', index=False)


