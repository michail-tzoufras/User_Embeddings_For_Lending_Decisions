import os
import csv
import argparse

import pandas as pd
import numpy as np
import copy
#------------------------------------------------------------------

import matplotlib.pyplot as plt
plt.rc("font", size=14)
import matplotlib as mpl
mpl.rcParams['legend.frameon'] = 'True'

import seaborn as sns
sns.set(style="white")
#------------------------------------------------------------------

from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
#------------------------------------------------------------------

import visualization as Vis
#------------------------------------------------------------------

def new_csv_writer( path, name, filenumber, headers, delimiter):
    """Returns a csv writer with the proper headers"""
    writer =  csv.writer( 
        open(
            os.path.join( path, name % filenumber ),'w'
            ), delimiter=delimiter
        )
    writer.writerow(headers)
    return writer

def split(filehandler, output_path, output_name_template, row_limit=100000, delimiter=','):
    """Break up the file provided by the filehandler to several csv files
    of manageable size of row_limit rows. """

    file_reader = csv.reader(filehandler, delimiter=delimiter)
    file_headers = next(file_reader)

    current_chunk = 1
    i = row_limit   # this initialization allows us to start a 
                    # new output_writer when entering the loop below 

    for row in file_reader:
        if ( (i+1) > row_limit ):
            output_writer = new_csv_writer(output_path, 
                                           output_name_template, 
                                           current_chunk, file_headers, delimiter)
            current_chunk += 1
            i = 0

        output_writer.writerow(row)
        i += 1

#----------------------#----------------------#----------------------

def normalize_column(df_column, center_at_zero = False):
    """Converts an unnormalized dataframe column to a normalized 
    1D numpy array
    Default: normalizes between [0,1]
    (center_at_zero == True): normalizes between [-1,1] """

    normalized_array = np.array(df_column,dtype = 'float64')
    amax, amin = np.max(normalized_array), np.min(normalized_array)
    normalized_array -= amin
    if center_at_zero:
        normalized_array *= 2.0/(amax-amin)
        normalized_array -= 1.0
    else:
        normalized_array *= 1.0/(amax-amin)
    return normalized_array


def dataframe_to_numpy(df,categorical_columns,ordinal_columns):
    """Converts data in dataframe to numpy array that includes:
    1) one-hot encoded categorical columnhs
    2) normalized ordinal columns"""

    le = preprocessing.LabelEncoder()
    Xtmp = (df[categorical_columns].copy()).apply(lambda col: le.fit_transform(col))

    ohe = preprocessing.OneHotEncoder(handle_unknown='ignore',sparse=False )
    X = np.transpose(ohe.fit_transform(Xtmp))

    for c in ordinal_columns:        
        X = np.vstack([X, normalize_column(df[c])])

    return np.transpose(X)



#-----------------------------------
#------------MAIN-------------------
#-----------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', action='store', 
                        default='/Users/mtzoufras/Desktop/Insight/Insight_Project_Data/BigML_Dataset.csv',
                        help='dataset path')
    parser.add_argument('--solver', action='store', 
                        default='All',
                        help="Select solver from: (1) 'Logistic Regression' \
                                                  (2) 'Random Forest' \
                                                  (3) 'Embeddings' \
                                                  (4) 'All' ")
    args = parser.parse_args()

    #datapath = '/Users/mtzoufras/Desktop/Insight/Insight_Project_Code/d0.0_Make_CSVs/split3/'
    datapath = os.getcwd()+'/../data/preprocessed/'
    dataname = 'BigML_Split_%s.csv'
    #split(open(args.data, 'r'), datapath, dataname)

    df_raw = pd.read_csv(datapath+dataname%1)
    #df_raw = pd.read_csv('/Users/mtzoufras/Desktop/Insight/Insight_Project_Data/BigML_Dataset.csv')

    useful_columns = ['Loan Amount','Country','Sector','Activity','Status']
    valid_status = ['paid','defaulted']

    df_clean = (df_raw[useful_columns][df_raw.Status.isin(valid_status)]).copy()
    df_clean['Funded Time'] = ((df_raw['Funded Date.year']+0.0833*df_raw['Funded Date.month'])
                                [df_raw.Status.isin(valid_status)]).copy()

    Vis.data_exploration(df_clean)
    Vis.country_vs_status(df_clean)
    categorical_columns = ['Country','Sector','Activity']
    ordinal_columns = ['Loan Amount','Funded Time']

    y_pred, y_prob, model_titles = [], [], []
    if ((args.solver == 'Logistic Regression') or \
        (args.solver == 'Random Forest') or \
        (args.solver == 'All')):
        
        X  = dataframe_to_numpy(df_clean,categorical_columns,ordinal_columns)
        y = np.array((pd.get_dummies(df_clean['Status'], columns=['Status'])['defaulted']).tolist())


        # Split data set into training and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
    
        if ((args.solver == 'Logistic Regression') or (args.solver == 'All')):
            # Import module for fitting
            logmodel = LogisticRegression(solver='lbfgs',class_weight= {0:.1, 1:.9},
                              penalty='l2',C=10.0, max_iter=500)

            # Fit the model using the training data
            logmodel.fit(X_train, y_train)

            y_pred.append(logmodel.predict(X_test))
            y_prob.append(logmodel.predict_proba(X_test)[:,1])
            model_titles.append('Logistic Regression')

        if ((args.solver == 'Random Forest') or (args.solver == 'All')):
            # Import module for fitting
            rfmodel = RandomForestClassifier(n_estimators=25,class_weight= {0:.1, 1:.9},max_depth=10)


            # Fit the model using the training data
            rfmodel.fit(X_train,y_train)

            y_pred.append(rfmodel.predict(X_test))
            y_prob.append(rfmodel.predict_proba(X_test)[:,1])
            model_titles.append('Random Forest')


    if ((args.solver == 'Embeddings') or (args.solver == 'All')):
                                      # remove the above comment later, when embeddings are working 
                                      # with the same metrics as the othe models
        import embeddings_DL as Emb
        
        # Find the vocabulary sizes for the categorical features
        vocabulary_sizes = [df_clean[c].nunique() for c in categorical_columns]

        # Maximum sentence length
        max_length=2

        embeddings_model = Emb.model_with_embeddings(vocabulary_sizes, max_length, len(ordinal_columns))
        categorical_data = Emb.data_preprocessing(df_clean, categorical_columns, vocabulary_sizes, max_length)

        # normalize the orindal features
        ordinal_data = [ (normalize_column(df_clean[c])).reshape(-1,1) for c in ordinal_columns] 

        input_data = categorical_data+ordinal_data
        labels = np.array((pd.get_dummies(df_clean['Status'], columns=['Status'])['paid']).tolist())

        acc = embeddings_model(input_data,labels)

        print('Accuracy: %f' % (acc*100))

    Vis.report_model_performance(y_test,y_pred,y_prob,model_titles)