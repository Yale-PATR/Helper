#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  3 15:58:29 2018

@author: aditya
"""

import pickle
import os
import pandas as pd
import numpy as np
import time
from tqdm import tqdm


flatten = lambda original: [item for sublist in original for item in sublist]


def timer(func, *args, iters = 100):
    elapsed = 0
    for i in tqdm(range(iters)):
        start = time.time()
        func(*args)
        end = time.time()
        elapsed += end - start
    print("Avg time:", round(1000*elapsed/iters, 3), "ms")

## Wrappers for pickling.  Just makes saving/loading objects a little less verbose

def save(obj, folder, name):
    name += '.pickle'
    with open(os.path.join(folder, name), 'wb') as output:
        pickle.dump(obj, output, -1)
def load(folder, name):
    name += '.pickle'
    with open(os.path.join(folder, name), 'rb') as input:
        obj = pickle.load(input)
        return obj
    
# converts time from float in hours to str
# in form '6 hrs 12 mins'
def getHrsMins(time):
    hours = int(np.floor(time))
    minutes = np.round(60*(time-hours), decimals = 1)
    text = str(hours) + ' hrs ' + str(minutes) + ' mins'
    return text

## search for substring query within names array
def searchColumns(names, query):
    match = np.array([query.lower() in name.lower() for name in list(names)])
    return names[match]
    

## Used for linear models
## takes a list of predictors and associated coefficients
## and prints them together in a nice way
def showCoef(coef, predictors):
    predictors = list(predictors)
    
    # make sure coef is 1-d and rounded
    if len(np.shape(coef)) > 1:   # convert (n,1) or (1,n) -> (n) 
        coef = coef[:,0] if np.shape(coef)[1] == 1 else coef[0,:]
    coef = np.around(coef, decimals = 3)
    
    # add right amount of spacing to predictor names to make eveyrthing aligned
    lengths = [len(x) for x in predictors]
    k = max(lengths)
    spaces = [k - len(x) for x in predictors]
    predictors = [predictors[i] + ' '*spaces[i] for i in range(len(predictors))]
    
    # pair and sort pairs by coef size
    toPrint = list((zip(predictors, coef)))
    sortIndex = np.argsort(coef)[::-1]
    toPrint = np.array(toPrint)[sortIndex]
    
    # print to console
    print('\n')
    for i in range(len(toPrint)):
        print(toPrint[i])
    print('\n')



# saves a file of the unique values for the columns given in a dataset
def saveUnique(data, names, folder, fileName, maxRecord = 1000, verbose = True):
    df_unique = pd.DataFrame(np.empty((maxRecord, len(names)), dtype = np.dtype('O')),
                             columns = names, index = np.arange(maxRecord))
    
    df_counts = pd.DataFrame(np.zeros((maxRecord, len(names)), dtype = np.int64),
                             columns = names, index = np.arange(maxRecord))
    
    for var in names:
        select = ~(data[var].astype(np.str).values == 'nan')
        dataRecorded = data[var].values[select]
        try:
            vals, counts = np.unique(dataRecorded, return_counts = True)
        except TypeError:
            dataRecorded = dataRecorded.astype(np.str)
            vals, counts = np.unique(dataRecorded, return_counts = True)
        maxLen = min(len(vals), maxRecord)
        sorter = np.argsort(counts)[::-1][:maxLen]
        vals, counts = vals[sorter], counts[sorter]
        loc = df_unique.columns.get_loc(var)
        df_unique.iloc[:maxLen, loc] = vals
        df_counts.iloc[:maxLen, loc] = counts
        if verbose:
            print(var)
    df_unique.to_csv(os.path.join(folder, fileName + '_unique.csv'))
    df_counts.to_csv(os.path.join(folder, fileName + '_counts.csv'))

 
def classVariableTransform(Y, T, soft = False, margin = None, side = 'both'):
    """
    Performs the standard class variable transormation, but with the option for soft targets (e.g. 0.05 or 0.95)
    Margin is how far to deviate from the hard targets 0/1
    Side is for when you only want to make a single class soft (such as minority class in imbalanced dataset) 
    """      
    ## expects numpy arrays, returns numpy array of same type
    # make sure a margin is provided if we want soft targets
    if soft:
        assert margin
        # configure shit for one sided margins if necessary
        if side == 'both':
            left = 1
            right = 1
        else:
            assert side == 'left' or side == 'right'
            left, right = 0, 0
            left = 1 if side == 'left' else 0
            right = 1 if side == 'right' else 0
    
    m = len(Y)
    f = lambda y,t: 1 if (y+t)%2 == 0 else 0
    Z = [f(Y[i],T[i]) for i in range(m)]
    if sum(Y) > m/2:
        Z = [not z for z in Z]
    
    if soft:
        g = lambda z: z+margin*left if margin < 0.5 else z-margin*right
        Z = [g(z) for z in Z]
        
    return np.array(Z, dtype = np.float32)

def getPatientIndices(data):
    """
    Input: 1-d numpy array of patient encounter IDs that is total length of data (repeats necessary)
    Output: (k x 3) matrix, X, where 1st and 2nd columns are start and stop indices, 
            third column is number of timestamps, and k is num encounters
    Usage for jth patient: data.iloc[ X[j,0]:X[j,1] , : ]
    """
    m = len(data)
    X = np.zeros((len(np.unique(data)), 3), dtype = np.int64)
    
    #fix boundaries
    X[0,0] = 0
    X[-1,1] = m

    # do loop to record indices
    counter = 0
    current = data[0]
    for i in range(1,m):
        if data[i] != current:
            current = data[i]
            X[counter,1] = i
            X[counter+1,0] = i
            counter += 1

    X[:,2] = X[:,1] - X[:,0]
    return X


"""
I don't remember how these work exactly
Needs refactoring and better comments
"""


def description_update(description, file):
    # remove first '\n' and grab model name
    description = description[1:]
    model_name = description[:description.index(':')]
    
    # read file
    f = open(file, 'r')
    contents = f.read()
    f.close()
    
    # collect all recorded model names
    splits = recursive_split(contents,[])
    if splits != []:
        splits = [splits[i][:splits[i].index(':')] for i in range(len(splits))]
        
    # append model description if name not taken
    if model_name in splits:
        raise ValueError('Model name is already used! Try another name.')
    f = open(file, 'a')
    f.write(description)
    f.close()

def recursive_split(contents, splits):
    index = contents.find('\n\n')
    if index == -1:
        return splits
    else:
        splits.append(contents[:index])
        contents = contents[index+2:]
        splits = recursive_split(contents, splits)
        return splits
    
