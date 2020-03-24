#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  5 09:55:09 2018
Last Modified:  1/28/2019 6:30PM
Python 3
@author: allenea
Eric Allen, University of Delaware, allenea@udel.edu

Create functions for formulas that can be called in other programs

Function List:

    Absolute Error
    Relative Error
    Percent Error
    Forecast Error
    Mean Square Error
    Mean Absolute Error
    Root Mean Square Error
    Bias
    Median Absolute Deviation
    Mean
    Median
    Mode
    Variance
    Standard Deviation


Sources for formulas and help:
https://dtcenter.org/met/users/docs/presentations/WRF_Users_2012.pdf
https://www.hindawi.com/journals/amete/2015/758250/
http://www.australianweathernews.com/verify/intro.htm
https://pdfs.semanticscholar.org/af71/3d815a7caba8dff7248ecea05a5956b2a487.pdf
http://dkmathstats.com/mean-median-mode-variance-in-python/
https://www.dummies.com/education/math/statistics/how-to-calculate-standard-deviation-in-a-statistical-data-set/
https://machinelearningmastery.com/time-series-forecasting-performance-measures-with-python/
Found this after the fact:
    http://www.statsmodels.org/devel/_modules/statsmodels/tools/eval_measures.html#mse


Future Ideas or Comments:
No skill score because we know that a sea breeze is going to happen. Might want to add
for Dan's verification to see if it forecasted precipitation.

Is MAE Skill Score 1 - MAE/MAE(no data assimilation?)

Scatter Plot of Observations vs Forecast values

Somehow average errors of the time difference between observed and forecasted.
"""
# IMPORTS
import numpy as np


def getmetrics(obs, pred):
    """Get Metrics"""
    #pred[pred == 0] = np.nan
    #obs[obs == 0] = np.nan
    #obs_nonan = obs[np.logical_not(np.isnan(obs))]
    #pred_nonan = pred[np.logical_not(np.isnan(pred))]

    #nonan_error = pred_nonan - obs_nonan
    error = pred - obs#obs - pred # Error
    #print("HERE")
    #print(error, nonan_error)

    mobs = np.nanmean(obs) # Mean observed
    #print(mobs, np.mean(obs_nonan))

    mpred = np.nanmean(pred) # Mean predicted
    #print(mpred, np.mean(pred_nonan))

    # ******** MAE *********
    mae = np.nanmean(np.abs(error))
    #print(mae, np.mean(np.abs(obs_nonan-pred_nonan)))

    # ******** MSE *********
    mse = np.nanmean(error**2)
    #print(mse, np.mean((obs_nonan-pred_nonan)**2))

    # ******** BIAS *********
    bias1 = np.nanmean(error)
    #print(bias)

    # ******** MAPE *********
    absdiv = np.abs(error / obs)
    mape = np.nanmean(absdiv) * 100.
    #print(mape)

    # ******** RMSE *********
    rmse = np.sqrt(mse)
    #print(rmse, np.sqrt(np.mean((obs_nonan-pred_nonan)**2)))

    # ******** Nash-Sutcliffe *********
    #FASTER
    # Line Continuation after division symbol
    nse = 1 - (np.nansum((obs - pred) ** 2, axis=0, dtype=np.float64)/\
                   np.nansum((obs - np.nanmean(obs)) ** 2, dtype=np.float64))#[0]
    #SAME RESULT. SLOWER
    #nse = 1 - (np.nansum((obs - pred)**2)/np.nansum((obs - np.nanmean(obs))** 2))
        # Nash-Sutcliffe model eficiency coefficient

    # ******** Index of Agreement *********
    part1 = np.nansum(np.abs(pred-obs))
    part2 = 2 * np.nansum(np.abs(obs - mobs))
    if part1 <= part2:
        iagree = 1 - part1/part2
    else:
        iagree = part2/part1 - 1

    # ******** R *********
    ##Line Continuation after division symbol
    pearson = np.nanmean((obs-mobs)*(pred-mpred))/\
        np.sqrt(np.nanmean((obs-mobs)**2))*np.sqrt(np.nanmean((pred-mpred)**2))

    # ******** R2 *********
    # rtwo = 1 - (np.sum(error)/np.sum(obs-mobs))
    rtwo = pearson*pearson

    #print("MAE:",mae)
    #print("MSE: ", mse)
    #print("RMSE: ", rmse)
    #print("BIAS: ", bias)
    #print("MAPE: ", mape)
    #print("R2: ", rtwo)
    #print("NSE1: ", nse)
    #print("Index of Agreement: ", iagree)
    #print("Pearson Correlation Coefficient: ", pearson,\
        # " NP (Corrcoef)=",np.corrcoef(pred_nonan, obs_nonan)[0,1])
    return [mae, mse, rmse, bias1, mape, rtwo, nse, iagree, pearson]



def nash_sutcliffe(pred, obs):
    '''(Forecasted, Observed)'''
    nse = 1 - (np.nansum((obs - pred)**2)/np.nansum((obs - np.nanmean(obs))** 2))
    # Nash-Sutcliffe model eficiency coefficient
    return nse


#Absolute Error
def absolute_error(forecast, actual):
    """
    Absolute Error: measures absolute difference from the forecasted value
                    and the observed value

    Input - A single actual observed value (float)
    Input - A single model forecasted value (float)
    Output - abs_err (absolute error)
    """
    absolute_error_out = abs(float(forecast) - float(actual))
    return absolute_error_out

#Relative Error
def relative_error(forecast, actual):
    """
    Relative Error: measures absolute error divided by the observed value f

    Calls function absolute_error to calculate absolute_error for the numerator

    If actual is 0 then np.nan is returned.

    Input - A single actual observed value (float)
    Input - A single model forecasted value (float)
    Output - RelativeError (relative error)
    """
    if actual == 0:
        actual = np.nan
    abs_err = absolute_error(float(forecast), float(actual))
    relative_error_out = abs_err / float(actual)
    return relative_error_out

#Percent Error
def percent_error(forecast, actual):
    """
    Percent Error: measures relative error as a percentage

    Calls function relative_error to get relative error which calls absolute error.

    If actual is 0 then np.nan is returned.

    Input - A single actual observed value  (float)
    Input - A single model forecasted value (float)
    Output - PercentError
    """
    percent_error_out = (relative_error(float(forecast), float(actual))) * 100
    return percent_error_out

#Forecast Error
def forecast_error(forecast, actual):
    """
    Forecast Error: Difference between forecast and observed

    Input - A single actual observed value  (float)
    Input - A single model forecasted value (float)
    Output - forecast_error
    """
    forecast_error_out = float(forecast) - float(actual)
    return forecast_error_out

#Mean Square Error
def mean_square_error(forecast, actual):
    """
    Mean Square Error: Average of the squares of the difference between the forecast
                        and observed observations.
                        -  Continuous Scores
                        - Does not indicate direction of error
                        - Quadratic rule, therefore large weight on large errors
                        - Good if you wihs to penalize large error BUT SENSITIVE
    Input  - A list actual observed values  (float)
    Input  - A list model forecasted values (float)
    Output - MSE (single value)
    """
    nlength = 0.0
    sfe = 0.0
    if len(actual) == len(forecast):
        nlength = len(forecast)
    else:
        print("MSE - Not Same Size")
    #http://www.australianweathernews.com/verify/intro.htm
    for idx in range(nlength):
        sfe += forecast_error(float(forecast[idx]), float(actual[idx])) ** 2
    mse = (1./nlength) * sfe
    return mse

#Mean Absolute Error
def mean_absolute_error(forecast, actual):
    """
    Mean absolute error: measures the mean amplitude/magnitude of the absolute error
            with respect to the observation.
            - Linear score = each error has the same weight
            - Does not indicate the direction of the error, just the magnitude
    Input  - list of actual observed values (floats)
    Input  - list of model forecasted values (floats)
    Output - MAE
    """
    #MEASURES ACCURACY
    nlength = 0.0
    sae = 0.0
    if len(actual) == len(forecast):
        nlength = len(forecast)
    else:
        print("MSE - Not Same Size")
    #http://www.australianweathernews.com/verify/intro.htm
    for idx in range(nlength):
        #Sum Absolute Error
        sae += absolute_error(float(forecast[idx]), float(actual[idx]))
    mae = (1./nlength) * sae
    return mae

#Root Mean Square Error
def root_mean_square_error(forecast, actual):
    """
    Root mean square error (RMSE): measures the mean square gap between observed
                                   and modelled data.
                        - Does not indicate direction of the error
                        - defined with quadratic rule = sensitive to errors
                        - RMSE IS ALWAYS LARGER OR EQUAL THAN THE MAE

    Calls mean_square_error and takes the square root of MSE

    Input - A list actual observed values  (float)
    Input - A list model forecasted values (float)
    Output - RMSE
    """
    if len(actual) != len(forecast):
        print("ERROR RMSE - Not Same Size")
    #http://www.australianweathernews.com/verify/intro.htm
    rmse = mean_square_error(forecast, actual) ** 0.5
    return rmse

#Bias
def bias(forecast, actual):
    """
    Bias: Measures the mean difference between simulation and observation

    Input - list of actual observed values
    Input - list of model forecasted values
    Output - Single Bias Value
    """
    num_actual = len(actual)
    num_forecast = len(forecast)
    num = 0.0
    sum_diff = 0.0
    if num_actual == num_forecast:
        num = num_actual
    else:
        print("BIAS - Not Same Size")
    for idx in range(num_actual):
        sum_diff += forecast_error(float(forecast[idx]), float(actual[idx]))

    #http://www.australianweathernews.com/verify/intro.htm
    bias_calc = (1./num) * sum_diff
    return bias_calc

#Median Absolute Deviation
def median_absolute_deviation(lst_absolute_error):
    """
    Median Absolute Deviation (MAD): Median of the magnitude of the errors. Very Robust
                                     - Measures accuracy
    Input - list of absolute errors
    Output - Single Median Absolute Error Value
    """
    return median(lst_absolute_error)

# Mean, Variance, STD


#Mean
def mean(lst):
    """
    Mean - Calculates the average or mean value from a list of numbers

    Input - List
    Output - Mean
    """
    return sum(lst)/float(len(lst))

#Median
def median(lst):
    """
    Median - Takes a list, sorts it, and find the median value

    For Python-2.X

    Input - List
    Output - Median Value

    for Python-3.X use below
        from statistics import median
        median([5, 2, 3, 8, 9, -2])
    """
    nlength = len(lst)
    if nlength < 1:
        return None
    if nlength % 2 == 1:
        return sorted(lst)[nlength//2]
    return sum(sorted(lst)[nlength//2-1:nlength//2+1])/2.0

#Mode
def mode(lst):
    """
    Mode - Finds the most common element in a list

    Allows for multiple modes

    Input - List
    Output - Most Common Element if 1; List of Most Common Elements >1
    """
    most = max(list(map(lst.count, lst)))
    return list(set(filter(lambda x: lst.count(x) == most, lst)))

#Variance
def variance(lst):
    """
    Variance - average of the squared differences from the Mean to individal observation.
    Input - List
    Output - Variance
    """
    average = mean(lst)
    variance_out = 0.0
    for item in lst:
        variance_out += (float(average) - float(item)) ** 2.0
    return variance_out/len(lst)

#Standard Deviation
def standard_deviation(lst):
    """
    Standard Deviation - Measures the spread of the numbers.
                       - Square root of variance

    Input - List
    Output - Standard Deviation
    """
    return variance(lst) ** 0.5
