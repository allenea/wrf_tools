#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 28 12:26:45 2018

Last Modified:  1/31/2019 4:50PM
Eric Allen, University of Delaware 
@author: allenea

This is an alternative to MET: Model Evaluation Toolkit - supported by NCAR/DTC

Still a work in progress....

TO_DO:
    Save I,J pairs and make sure one grid box isn't being checked multiple times.
    Add an option to take a mean of the 4 neighboring gridboxes to use as the mean for a particular gridbox.
    Add More Statistics including on the entire dataset (like ... Willmott's Index of Agreement or the Nash-Sutcliffe)
    
    
"""
    
## IMPORTS
import calendar
import datetime
import sys
import os


import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from netCDF4 import Dataset
import wrf

import func_4_stat_analysis as stats


#%% SET ANALYSIS WINDOW, CASE STUDY TIMES, INDEPENDENT VARIABLES (ASSIMILATION TYPE, PHYSICS TYPE, ETC.), VARIABLES,STATISTICS, etc.

#!! SELECT RUN OPTION (1. By Case Study    2. By Independent Variable)
#option = 1 #!! ANALYZE BY CASE STUDY
option = 2 #!!  ANALYZE BY INDEPENDENT VARIABLE

#!!! WARNING DOES NOT WORK WHEN CHANGING MULTIPLE MONTHS OR MULTIPLE YEARS (Long Term Analysis)
analysis_start_hour_UTC = 10 
analysis_length_hrs = 18

wrf_interval_min = 15                        ### CHANGE BASED ON MODEL TIMESTEP
analysis_interval_min = 30                   ### CHANGE BASED ON DATA TIMESTEP


#ENTER CASE STUDY TIMES IN THIS FORMAT: '2015-08-14_06:00'
casestudy_time = ['2014-06-04_06:00','2014-06-08_06:00','2015-08-14_06:00']
independent_var = ["NDA", "BOTH","DEOS","FERRY"]    # Data Assimilation, Physics, sensitivity test, etc.
ind_var_str = "DA_TYPE"                             # Describes the independent Variable... KEEP LESS THAN 8 CHAR
plt_str = "DA_Avgs"

variables = ['Wind_Speed (m/s)','Wind_Direction (deg)','Air_Temperature (K)','Dewpoint_Temperature (K)']#,'Relative Humidity (%)','Pressure (Pa)']  
                                                                                                    ## Pressure and RH lack sufficient Observed Data
domain = "03" #"01","02          
stats_list = ["MAE", "MAPE", "RMSE", "BIAS"]

dtype_usage = '10m' #,'original'    ### ALWAYS USE 10m winds data in model evaluation including winds since that is the output level. The other data isn't changed


#%% Administrative OS- Set Paths
mydir = os.getcwd()
outdir = mydir+"/STATS/stat_graphs/"
if not os.path.exists(outdir): os.makedirs(outdir)
csvdir = mydir+"/STATS/csv_new/"
if not os.path.exists(csvdir):os.makedirs(csvdir)

model_data_dir = os.path.abspath('../Model_Outputs/')
ver_data_dir = os.path.abspath('../Verification_Data/')

"""                        
### GATHER VALIDATION DATA - Around lines 290-300 - Each directory holds csv files trimmed to the window of the WRF RUN.

if dtype_usage == "10m":
    if isRaw == True:
        data_file = ver_data_dir+"/verify_case_study_data/"+dtype_usage+"/"+case_time[0:10]+'/' 
    else:
        data_file = ver_data_dir+"/hr_avg_trim/"+dtype_usage+"/"+case_time[0:10]+'/'
            
elif dtype_usage == "original":
    if isRaw == True:
        data_file = ver_data_dir+"/verify_case_study_data/"+dtype_usage+"/"+case_time[0:10]+'/'
    else:
        data_file = ver_data_dir+"/hr_avg_trim/"+dtype_usage+"/"+case_time[0:10]+'/'
"""



def fmt_run_path(case, iv):
    """
    SETS FILE FORMAT FOR CASES AND THEIR VARIATIONS
    Files should be arranged and named so you can simply look through.
    
    
    # DIRECTORY MAKER: Build Your Own Naming Mechanism
    # - For Example: 
        'CaseStudy_6-4-2014/BOTH_6_4_2014'
        'CaseStudy_6-4-2014/DEOS_6_4_2014'
        'CaseStudy_6-4-2014/NDA_6_4_2014'
        'CaseStudy_6-4-2014/FERRY_6_4_2014'
        'CaseStudy_6-8-2014/BOTH_6_8_2014'
        'CaseStudy_6-8-2014/DEOS_6_8_2014'
        'CaseStudy_6-8-2014/FERRY_6_8_2014'
        'CaseStudy_6-8-2014/NDA_6_8_2014'
    """
    filename = "wrfout_d"+domain+"_*"

    prefix_casestudy = "CaseStudy_"
    dtuple = datetime.datetime.strptime(case, "%Y-%m-%d_%H:%M")
    short_time = dtuple.strftime('%-m-%-d-%Y')
    simulation = "/"+prefix_casestudy+short_time+"/"+iv_type+"_"+short_time.replace("-","_")+"/"

    model_path = model_data_dir+simulation+filename

    return model_path, short_time




##########################DO NOT EDIT BELOW#####################################################
    


## FILL WITH TIME STEPS DURING ANALYSIS FOR PLOTTING
header= ["NAME", "AVERAGE"]
header_Var= ["VARIABLE", "AVERAGE"]
header_iv= [ind_var_str, "AVERAGE"]
header_case= ["CASE", "AVERAGE"]         

#Quick Out
if len(stats_list) == 0  or len(casestudy_time) == 0 or domain == 0:
    print("Missing Important Info In Setup")
    sys.exit(0)

#Constants
sec = 60.0  
original_len = len(header)
isRaw = False                       ### ALWAYS LEAVE FALSE TO USE 30 min averaged data on consistant time step
fillHeaders = False                 ### ALWAYS LEAVE FALSE. It'll be set to true once the headers above are filled

def get_substeps(wrf_interval_min,analysis_interval_min):
    """
    Calculates the analysis window. Doesn't go multiple months or years.
    
    (int) wrf_interval_min:  15
    (int) analysis_interval_min: i.e. 30
    """
    
    if analysis_interval_min % wrf_interval_min == 0:
        #opposite
        wrf_substeps = analysis_interval_min//wrf_interval_min
        analysis_substeps = 1
    elif wrf_interval_min % analysis_interval_min == 0:
        #opposite
        analysis_substeps = wrf_interval_min//analysis_interval_min
        wrf_substeps = 1
    else:
        print("NOT AN EVEN TIME STEP BETWEEN THE DATA AND THE MODEL")
        sys.exit(0)
        
    return wrf_substeps, analysis_substeps 

   
# Get analysis window
def get_analysis_window(case_time, analysis_start_hour_UTC, analysis_length_hrs):
    """
    Calculates the analysis window. Doesn't go multiple months or years.
    
    (str) Case_Time: i.e. '2014-06-04_06:00'
    (int) analysis_start_hour_UTC:  12
    (int) analysis_length_hrs: i.e. 18
    """
    
    dtuple = datetime.datetime.strptime(case_time, "%Y-%m-%d_%H:%M")
    yrCH = dtuple.year
    monCH = dtuple.month
    dayCH = dtuple.day
    
    
    analysis_start = datetime.datetime(dtuple.year, dtuple.month, dtuple.day,analysis_start_hour_UTC)
    # CHANGES DAY
    if analysis_start_hour_UTC + analysis_length_hrs > 23:
        # END HOUR
        analysis_end_hour_UTC = (analysis_start_hour_UTC + analysis_length_hrs)%24
        
        ## NUMBER OF ADDITIONAL DAYS
        analysis_end_day_UTC = (analysis_start_hour_UTC + analysis_length_hrs)//24  

        if dtuple.month == 1 or dtuple.month == 3 or  dtuple.month == 5 or  dtuple.month == 7 or  dtuple.month == 8 or  dtuple.month == 10:
            
            if dtuple.day + analysis_end_day_UTC > 32 and (dtuple.day + analysis_end_day_UTC) <= 60:
                monCH = dtuple.month +1
                dayCH =  (dtuple.day + analysis_end_day_UTC) - 32
                
            elif dtuple.day + analysis_end_day_UTC <= 32:
                dayCH =  dtuple.day + analysis_end_day_UTC 
            else:
                print("ANALYSIS WINDOW PROBLEM")
                sys.exit(0)
                
        elif dtuple.month == 2 and calendar.isleap(dtuple.year) == False:
            #and dtuple.day == 28
            if dtuple.day + analysis_end_day_UTC > 28 and (dtuple.day + analysis_end_day_UTC) <= 60:
                monCH = dtuple.month +1
                dayCH =  (dtuple.day + analysis_end_day_UTC) - 28
                
            elif dtuple.day + analysis_end_day_UTC <= 28:
                dayCH =  dtuple.day + analysis_end_day_UTC 
            else:
                print("ANALYSIS WINDOW PROBLEM")
                sys.exit(0)

        elif dtuple.month == 2 and calendar.isleap(dtuple.year) == True:
            # and dtuple.day == 29
            if dtuple.day + analysis_end_day_UTC > 29 and (dtuple.day + analysis_end_day_UTC) <= 61:
                monCH = dtuple.month +1
                dayCH =  (dtuple.day + analysis_end_day_UTC) - 29
                
            elif dtuple.day + analysis_end_day_UTC <= 29:
                dayCH =  dtuple.day + analysis_end_day_UTC 
            else:
                print("ANALYSIS WINDOW PROBLEM")
                sys.exit(0)
                
        elif dtuple.month == 4 or dtuple.month == 6 or dtuple.month == 9 or dtuple.month ==11:
            if dtuple.day + analysis_end_day_UTC > 30 and (dtuple.day + analysis_end_day_UTC) <= 60:
                monCH = dtuple.month +1
                dayCH =  (dtuple.day + analysis_end_day_UTC) - 30
                
            elif dtuple.day + analysis_end_day_UTC <= 30:
                dayCH =  dtuple.day + analysis_end_day_UTC 
            else:
                print("ANALYSIS WINDOW PROBLEM")
                sys.exit(0)
                
        elif dtuple.month == 12:
            if dtuple.day + analysis_end_day_UTC > 30 and (dtuple.day + analysis_end_day_UTC) <= 62:
                yrCH = dtuple.year + 1
                monCH = 1
                dayCH =  (dtuple.day + analysis_end_day_UTC) - 30
            elif dtuple.day + analysis_end_day_UTC <= 30:
                dayCH =  dtuple.day + analysis_end_day_UTC 
            else:
                print("ANALYSIS WINDOW PROBLEM")
                sys.exit(0)
                
                
        analysis_end = datetime.datetime(yrCH, monCH, dayCH, analysis_end_hour_UTC)

    else:
        analysis_end_hour_UTC = analysis_start_hour_UTC + analysis_length_hrs
        analysis_end = datetime.datetime(dtuple.year, dtuple.month, dtuple.day, analysis_end_hour_UTC)  

    return analysis_start, analysis_end  



#!!! OPTION 1
if option == 1:
    outdir = outdir+"/Option1/"
    csvdir = csvdir+"/Option1/"
    if not os.path.exists(csvdir): os.makedirs(csvdir)
    if not os.path.exists(outdir): os.makedirs(outdir)
    """
    For each variable being analyzed perform the aforementioned statistics on each case study and independent variable for the run.
    
    """

    ## START ANALYSIS
    analysis_start, analysis_end  = get_analysis_window(casestudy_time[0],analysis_start_hour_UTC, analysis_length_hrs)
    wrf_substeps, analysis_substeps = get_substeps(wrf_interval_min,analysis_interval_min)  
    #\ DO ONE VARIABLE AT A TIME
    for var_step in variables:
        
        variables_short = [var_step] 
        print(var_step)    #Puts it in a "short list"
        
        # Do each statistical analysis
        for stat_type in stats_list:
            
            case_analysis = np.zeros((len(casestudy_time),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)
            # For each case study
            for m in range(len(casestudy_time)):
                
                case_time = casestudy_time[m]
                
                cumulative_error = 0; cumulative_checks = 0;
                analysis_start, analysis_end  = get_analysis_window(case_time,analysis_start_hour_UTC, analysis_length_hrs)
                iv_analysis = np.zeros((len(independent_var),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)

                # For each WRF configuration
                for z in range(len(independent_var)):
                    
                    iv_type = independent_var[z]
                    iv_error = 0; iv_checks = 0;
                    simulation, short_time = fmt_run_path(case_time, iv_type)
                                    
                    # For each WRF domain in analysis get that data file and read it. If Empty->EXIT
                    listing = glob.glob(simulation)
                    if len(listing) == 0: print("INVALID PATH"); sys.exit(0)
                    print(case_time,"\t",iv_type)

                    #WRF OUTPUT FILE
                    ncfile = Dataset(listing[0])
                    var_analysis = np.zeros((len(independent_var),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)

                    ###  Get's a single variable from top loop.... left here to keep everything else working. 
                    for p in range(len(variables_short)):
                        
                        variable = variables_short[p]
                        variable_error = 0; variable_checks = 0;
                        
                        ### GATHER VALIDATION DATA DIRECTORY FOR CASE
                        if dtype_usage == "10m":
                            if isRaw == True:   data_file = ver_data_dir+"/verify_case_study_data/"+dtype_usage+"/"+case_time[0:10]+'/' 
                            else:               data_file = ver_data_dir+"/hr_avg_trim/"+dtype_usage+"/"+case_time[0:10]+'/'
                        elif dtype_usage == "original":
                            if isRaw == True:   data_file = ver_data_dir+"/verify_case_study_data/"+dtype_usage+"/"+case_time[0:10]+'/'
                            else:               data_file = ver_data_dir+"/hr_avg_trim/"+dtype_usage+"/"+case_time[0:10]+'/'
                     
                        # PER VARIABLE - EXTRACT FOR ANALYSIS  (WRF-DATA)
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_uvmet.get_uvmet10_wspd_wdir.html?highlight=wrf%20wind%20direction%2010m   #10m wind speed    #UNIT m/s    
                        if variable == 'Wind_Speed (m/s)': WRF_VAR = wrf.g_uvmet.get_uvmet10_wspd_wdir(ncfile, timeidx=wrf.ALL_TIMES, method='cat',squeeze=True, cache=None, meta=False, _key=None, units='m s-1')[0]                    
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_uvmet.get_uvmet10_wspd_wdir.html?highlight=wrf%20wind%20direction%2010m       #10m wind direction
                        elif variable == 'Wind_Direction (deg)':  WRF_VAR = wrf.g_uvmet.get_uvmet10_wspd_wdir(ncfile, timeidx=wrf.ALL_TIMES, method='cat', squeeze=True, cache=None, meta=False, _key=None, units='m s-1')[1] #UNIT m/s                        
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_temp.get_tk.html?highlight=Air%20temperature      ## 2m air temperature KELVIN
                        elif variable == 'Air_Temperature (K)': WRF_VAR = wrf.getvar(ncfile,"T2",timeidx=wrf.ALL_TIMES,method='cat',squeeze=True,cache=None,meta=False) 
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_dewpoint.get_dp_2m.html?highlight=wrf.g_dewpoint.get_dp_2m        #2m dewpoint temperature KELVIN
                        elif variable == 'Dewpoint_Temperature (K)': WRF_VAR = wrf.g_dewpoint.get_dp_2m(ncfile,timeidx=wrf.ALL_TIMES, method='cat',squeeze=True,cache=None,meta=False,_key=None,units='K')
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_rh.get_rh_2m.html?highlight=relative%20humidity           #2m relative humidity   UNIT: %    
                        elif variable == "Relative Humidity (%)": WRF_VAR = wrf.g_rh.get_rh_2m(ncfile,timeidx=wrf.ALL_TIMES,method='cat',squeeze=True, cache=None, meta=False, _key=None)                 
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_pressure.get_pressure.html?highlight=pressure #SLP pressure
                        elif variable == "Pressure (Pa)": WRF_VAR = wrf.g_slp.get_slp(ncfile,timeidx=wrf.ALL_TIMES, method='cat',squeeze=True,cache=None,meta=False,_key=None,units='Pa')
                        else: print ("INVALID VARIABLE OPTION"); sys.exit(0)
                        
                        # GET WRF TIME STEP AHD REFORMAT
                        WRF_TIMES = wrf.extract_times(ncfile,timeidx=wrf.ALL_TIMES, method='cat',squeeze=True,cache = None, meta=False,do_xtime=False).astype(str)
                        #WRF_TIMES = wrf.g_times.get_times(ncfile,timeidx=wrf.ALL_TIMES,method='cat',squeeze=True,cache=None,meta=False,_key=None).astype(str)
                        WRF_DT = [""] * len(WRF_TIMES)
                        for ijk in range(len(WRF_TIMES)):
                            # FOR SOME REASON THERE ARE 9 miliseconds orecision when there should be 6
                            WRF_DT[ijk] = datetime.datetime.strptime(WRF_TIMES[ijk][:-3],'%Y-%m-%dT%H:%M:%S.%f')   
                            #dt= utc_dt.strftime('%Y-%m-%d %H:%M:%S')
                            
                        diff_wrf = WRF_DT[-1] - WRF_DT[0]
                        wrf_timestep = (WRF_DT[1] - WRF_DT[0]).total_seconds()
                        tot_sec_wrf = diff_wrf.total_seconds()
                        
                        if len(WRF_DT) != (tot_sec_wrf / wrf_timestep) + 1: print("WRF TIME NOT THE RIGHT LENGTH"); sys.exit(0)
                        
                        # Get verification data
                        verdat = glob.glob(data_file+"*")    
                        half_hourly_analysis = np.zeros((len(verdat),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)

                        # Loop through verification data
                        for verdex in range(len(verdat)):
                            hha_idx = 0; station_error = 0; stationCHECKS = 0;
        
                            #%% Read In Data   - Verification
                            data = pd.read_csv(verdat[verdex], low_memory=False)
                            data.columns.tolist()
                            # Mask missing data
                            data = data.mask(data == " ",other = np.nan)
                            data = data.mask(data == "",other = np.nan)
                            data = data.mask(data == -888888.0, other = np.nan)
                            data['Wind_Speed (m/s)'] = data['Wind_Speed (m/s)'].mask(data['Wind_Speed (m/s)'] < 0, other = np.nan)
                            
                            
                            ID_String = str(data['ID_String'][0])

                            half_hourly_analysis[verdex,0] = ID_String  # STORE IN ANALYSIS ARRAY
                            
                            
                            ## EXTRACT VERIFICATION DATA TIME
                            time = []
                            #SAMPLE: '2014-06-04T06:00:00.000000000'
                            if isRaw == True:
                                    Date = np.array(data['DATE'],dtype=str)
                                    for dte in Date:
                                        utc_dt= datetime.datetime(int(dte[0:4]),int(dte[4:6]),int(dte[6:8]),int(dte[8:10]),int(dte[10:12]),int(dte[12:14]))
                                        #dt= utc_dt.strftime('%Y-%m-%d %H:%M:%S')
                                        time.append(utc_dt)#utc_dt.strftime('%Y-%m-$dT%H:%M:%S'))
                            elif isRaw == False:
                                year =np.array(data['YEAR'],dtype=int) 
                                month =np.array(data['MONTH'],dtype=int) 
                                day = np.array(data['DAY'],dtype=int) 
                                hour =np.array(data['HOUR'],dtype=int) 
                                minute = np.array(data['MINUTE'],dtype=int) 
                                for idx in range(len(year)):
                                    utc_dt= datetime.datetime(year[idx],month[idx],day[idx],hour[idx],minute[idx])
                                    time.append(utc_dt)#utc_dt.strftime('%Y-%m-%dT%H:%M:%S.%f'))
                            
                            #The second half of this if (or) statement could be an issue... haven't tested it.
                            if len(time) != tot_sec_wrf / (wrf_interval_min * sec * wrf_substeps)+1:
                                if len(time) != tot_sec_wrf / (analysis_interval_min * sec * analysis_substeps)+1:
                                    print("VALIDATION DATA TIME NOT THE RIGHT LENGTH")
                                    continue
                                else:
                                    print("POTENTIALLY BIG PROBLEM BUT ERIC'S BEING TO LAZY TO TEST")
                                    print("This means (I HOPE) that the time is the length of the analysis time * subseps\n\t\t which means multiple analysis timesteps between wrf time steps")

                            ## LATITUDE AND LONGITUDE IN OBSERVATION TO LOC IN MODEL OUTPUT
                            obs_lat = np.array(data['Latitude'][0]) 
                            obs_long = np.array(data['Longitude'][0]) 
        
                            # PER VARIABLE - VERIFICATION
                            if variable == 'Wind_Speed (m/s)':  variable_data= np.array(data['Wind_Speed (m/s)'])
                            elif variable == 'Wind_Direction (deg)':  variable_data = np.array(data['Wind_Direction (deg)'])
                            elif variable == 'Air_Temperature (K)':  variable_data = np.array(data['Air_Temperature (K)'])
                            elif variable == 'Dewpoint_Temperature (K)':  variable_data = np.array(data['Dewpoint_Temperature (K)']) 
                            elif variable == "Relative Humidity (%)":  variable_data = np.array(data['Relative Humidity (%)'])
                            elif variable == "Pressure (Pa)":  variable_data = np.array(data['Pressure (Pa)'])
                            else: sys.exit(0)

                            # WRF VARIABLE FULL TIME SLICE AT ONE LOCATION
                            try:
                                x_y = wrf.ll_to_xy(ncfile,  obs_lat, obs_long)
                                #latlon = wrf.xy_to_ll(ncfile,  float(x_y[0]),float(x_y[1]))
                                TRIM_WRF_VAR = WRF_VAR[:,int(x_y[0]),int(x_y[1])]
                            except:
                                continue

            
                            ## FOCUS ON 8am to 8pm so 12UTC to 0UTC
                            ## CHANGED TO 6am to midnight that way it captures sunrise and sunset and after SB.
                            for i in range(0,len(time),analysis_substeps):
                                #Checks every half hour and 30 minutes
                                for j in range(0,len(WRF_DT),wrf_substeps):
                                    #Verification Data outside analysis window
                                    if time[i] < analysis_start or time[i] > analysis_end:
                                        continue
                                    #WRF Data outside analysis window
                                    elif WRF_DT[j]  < analysis_start or WRF_DT[j] > analysis_end:
                                        continue
                                    ## Correct time - MATCH!
                                    elif time[i] == WRF_DT[j]:
                                        if fillHeaders == False:
                                            header.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE
                                            header_Var.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE
                                            header_iv.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE
                                            header_case.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE

                                        # Verification Data is Missing Value
                                        if np.isnan(variable_data[i]) == True:
                                            half_hourly_analysis[verdex,hha_idx+1] = np.nan
                                            hha_idx +=1
                                            continue
                                        # WRF Data is Missing Value
                                        elif np.isnan(TRIM_WRF_VAR[j]) == True:
                                            half_hourly_analysis[verdex,hha_idx+1] = np.nan
                                            hha_idx +=1
                                            continue
                                        else:
                                            #GOOD DATA - ANALYZE BASED ON THE STATISTIC BEING PERFORMED (based on iteration of the stat array)
                                            if stat_type == "MAE":
                                                #∑|(Xf - Xo)| / n
                                                ylabel_str = "Mean Absolute Error"
                                                abs_error = stats.absolute_error(TRIM_WRF_VAR[j], variable_data[i])
                                                half_hourly_analysis[verdex,hha_idx+1] = abs_error
            
                                                station_error += abs_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            
                                            elif stat_type == "MAPE":
                                                ylabel_str = "Mean Absolute Percent Error"

                                                # ( ∑|Xf - Xo| / Xo ) / n or relative error:|Xf - Xo| / Xo then multiply by 100 for %
                                                # then ∑x/n for mean Absolute percent error

                                                rel_error = stats.relative_error(TRIM_WRF_VAR[j], variable_data[i])
                                                half_hourly_analysis[verdex,hha_idx+1] = rel_error * 100.0
                                                    
                                                station_error += rel_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            
                                            elif stat_type == "BIAS":
                                                #∑(Xf - Xo) / n
                                                ylabel_str = "Bias"
                                                fcst_error = stats.forecast_error(TRIM_WRF_VAR[j], variable_data[i])
                                                half_hourly_analysis[verdex,hha_idx+1] = fcst_error
                                                station_error += fcst_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            
                                            
                                            elif stat_type == "RMSE":
                                                ylabel_str = "Root Mean Square Error"

                                                rel_error = stats.forecast_error(TRIM_WRF_VAR[j], variable_data[i])  ** 2
                                                half_hourly_analysis[verdex,hha_idx+1] = rel_error
                                                    
                                                station_error += rel_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            # append error by hour any non checks filled with np.nan
                                            else:
                                                print("INVALID STATISTICAL OPTION.... ADD NEAR LINE 500")
                                                sys.exit(0)

                                            # DO MORE STUFF HERE

                                    # This will always happen even if there is no wrf match to the time.
                                    elif time[i] != WRF_DT[j] and WRF_DT[j] == WRF_DT[-1]:
                                        continue
        
                                    # THIS WILL ALWAYS HAPPEN AT THE END OF THE ITERATION IF NO MATCH
                                    elif time[i] == time[-1]:
                                        continue
                                    
                            # MAKE TRUE TO PREVENT HEADERS FROM BEING REFILLED EACH TIME        
                            fillHeaders=True

                            # IF NO DATA (STAT) ANALYSIS ELSE CALCULATE THE MEAN OF THE STAT AND PRINT       
                            if stationCHECKS == 0:
                                print ("No Checks Performed At ", ID_String)
                                continue
                            else:
                                # ADD STATION ERROR TO VARIABLE ERROR
                                variable_error += station_error
                                variable_checks += stationCHECKS
                                station_calc_err = station_error/stationCHECKS
                                #print(ID_String,"Error: \t\t" , station_calc_err)
                            
                        ## CALCULATE VARIANCE HERE
                    
                    
                        ### AVERAGE BY LOCATION
                        
                        ## TAKE THE MEAN OF ALL CHECKS (OR SQ MEAN FOR RMSE) FOR EACH HOUR.... THEN FOR EACH STATION AND APPEND    
                        # MASK ZEROS FROM INITIALIZED ARRAY. NO CHECKS WERE PERFORMED AT THOSE LOCATIONS.
                        hr_stations_stat = pd.DataFrame(half_hourly_analysis,index=None)
                        hr_stations_stat = hr_stations_stat.mask(hr_stations_stat == 0, other=np.nan)
                        if stat_type == "RMSE":
                            vertAvg = (np.nanmean((np.array(hr_stations_stat)[:,1:]).astype(float), axis=0)) ** 0.5
                        else:
                            vertAvg = np.nanmean((np.array(hr_stations_stat)[:,1:]).astype(float), axis=0) #vertically (DEFAULT: axis=0),

                        tmp1 = np.zeros(len(vertAvg)+1).astype(object)
                        tmp1[0] = "Hr_Avgs"
                        tmp1[1:] = vertAvg
                        half_hourly_analysis2 = pd.concat((pd.DataFrame(half_hourly_analysis),pd.DataFrame(tmp1).T))
                        half_hourly_analysis2 = half_hourly_analysis2.mask(half_hourly_analysis2 == 0, other=np.nan)

                        per_station_stats = np.array(half_hourly_analysis2)
                        #horizontally (axis=1)
                        
                        if stat_type == "RMSE":
                            horAvg = (np.nanmean(per_station_stats[:,1:].astype(float), axis=1)) ** 0.5
                        else:
                            horAvg = np.nanmean(per_station_stats[:,1:].astype(float), axis=1)
                            
                        complete_station_stats = pd.concat((pd.DataFrame(per_station_stats),pd.DataFrame(horAvg)),axis=1)
                        complete_station_stats.columns =header
                        
                        # WRITE TO CSV - 4 files per case subdir (so about 16 files per variable)
                        #complete_station_stats.to_csv(csvdir+stat_type+"_"+case_subdir+"_"+domain+"_"+variable[:-5].strip()+".csv", index=False,float_format='%.3f')
                        var_check =np.array(complete_station_stats)[len(complete_station_stats)-1][:-1]
                        var_check[0] = variable
                        var_analysis[p] = var_check # AVERAGE OVER ALL STATIONS (NOT TIME)
                        
                        if variable_checks == 0:
                            print("No checks performed for ", variable)
                            continue
                        else:
                            iv_error += variable_error
                            iv_checks += variable_checks
                            var_err = variable_error/variable_checks
                            #print(variable, "Error: \t\t",var_err )

                    iv_check222 =var_analysis[p]
                    iv_check222[0] = iv_type
                    iv_analysis[z] = iv_check222  
                    if iv_checks == 0:
                        print("No checks performed for ", case_time,"\t",iv_type,"\t", domain, '\t',variable)
                        continue
                    else:
                        iv_err =iv_error/iv_checks
                        cumulative_error +=iv_error
                        cumulative_checks +=iv_checks
                        print(case_time,"\t",variable," "+stat_type+": \t\t", iv_err)

                
                # AVERAGE BY HOUR AND ASSIMILATION TYPE  - PUT IN THE SPREADSHEET
                
                ## TAKE THE MEAN OF ALL CHECKS (OR SQ MEAN FOR RMSE) FOR EACH HOUR OF EACH DATA ASSIMILATION TYPE ( NOW ONLY ONE VARIABLE AT A TIME) AND FOR EACH TYPE... AND APPEND
                ## VERTICAL APPEND IS WHAT GOES IN THE VERIFICATION_TABLE SPREAD SHEET BY USER
                vertAvgIV = np.nanmean((iv_analysis[:,1:]).astype(float), axis=0)   
                tmp4 = np.zeros(len(vertAvgIV)+1).astype(object)
                tmp4[0] = plt_str
                tmp4[1:] = vertAvgIV
                ivAnaly2 = pd.concat((pd.DataFrame(iv_analysis),pd.DataFrame(tmp4).T))
                ivAnaly2 = ivAnaly2.mask(ivAnaly2 == 0, other=np.nan)
                ivAnaly2 = np.array(ivAnaly2)
                horAvgIV = np.nanmean(ivAnaly2[:,1:].astype(float), axis=1)                #horizontally (axis=1)
                IV = pd.concat((pd.DataFrame(ivAnaly2),pd.DataFrame(horAvgIV)),axis=1)
                IV.columns =header_iv 
                IV.to_csv(csvdir+"Assimilation_Analysis_"+stat_type+"_"+short_time.replace("-","_").strip()+"_"+variable[:-6]+".csv", index=False,float_format='%.3f')

                case_type_check =np.array(IV)[len(IV)-1][:-1]
                case_type_check[0] = case_time
                case_analysis[m] = case_type_check      
                
                ## PLOT ERROR BY CASE BY ASSIMILATION TYPE
                fig,ax = plt.subplots(figsize=(14,6)) 
                colors = ['red','green','blue','purple','black']
                colorcount = 0
                for row in np.array(IV):
                    ax.plot(header[1:-1], row[1:-1], color = colors[colorcount],label = row[0])
                    colorcount +=1
                ax.set_title(ylabel_str+" on "+short_time+"\n"+variable.replace("_"," "), fontsize=16)
                ax.set_xlabel("Time (UTC)", fontsize=14)
                ax.set_ylabel(ylabel_str +" ("+stat_type+")", fontsize=14)
                ax.legend(loc='best', fontsize=14)
                ax.minorticks_on()
                plt.gcf().autofmt_xdate()
                plt.savefig(outdir+stat_type+"_"+variable[:-6]+"_"+short_time.replace("-","_").strip()+".png")
                #plt.show()
                plt.close()     
                
                if cumulative_checks == 0:
                    print("No checks performed for ", case_time,"\t",iv_type,"\t", domain, '\t',variable)
                else:
                    cu_err =cumulative_error/cumulative_checks
                    #print(case_time,"\t",variable," "+stat_type+": \t\t", cu_err)
            
            # AVERAGE BY CASE - NOT A FOCUS BECAUSE IT MIXES DA TYPES
            
            ## TAKE THE MEAN OF ALL CHECKS (OR SQ MEAN FOR RMSE) FOR EACH HOUR OF ALL CASES ( NOW ONLY ONE VARIABLE AT A TIME) AND FOR EACH CASE... AND APPEND            
            vertAvgCase = np.nanmean((case_analysis[:,1:]).astype(float), axis=0)
            tmp5 = np.zeros(len(vertAvgCase)+1).astype(object)
            tmp5[0] = "Case_Avgs"
            tmp5[1:] = vertAvgCase
            caseAnaly2 = pd.concat((pd.DataFrame(case_analysis),pd.DataFrame(tmp5).T))
            caseAnaly2 = caseAnaly2.mask(caseAnaly2 == 0, other=np.nan)
            caseAnaly2 = np.array(caseAnaly2)
            horAvgCase = np.nanmean(caseAnaly2[:,1:].astype(float), axis=1)
            case3 = pd.concat((pd.DataFrame(caseAnaly2),pd.DataFrame(horAvgCase)),axis=1)
            case3.columns =header_case 
            case3.to_csv(csvdir+"Case_Analysis_All_"+stat_type+"_"+variable[:-6]+".csv", index=False,float_format='%.3f')
               
            
            ## PLOT ERROR BY CASE BY HOUR
            fig2, ax1 = plt.subplots(figsize=(14,6)) 
            colors = ['red','green','blue','purple','black']
            colorcount = 0
            for row in np.array(case3):
                ax1.plot(header[1:-1], row[1:-1], color = colors[colorcount],label=row[0])
                colorcount +=1
            ax1.set_title(ylabel_str+" for All Cases\n"+variable.replace("_"," "), fontsize=16)
            ax1.set_xlabel("Time (UTC)", fontsize=14)
            ax1.set_ylabel(ylabel_str +" ("+stat_type+")", fontsize=14)
            ax1.legend(loc='best', fontsize=14)
            ax1.minorticks_on()
            plt.gcf().autofmt_xdate()
            plt.savefig(outdir+stat_type+"_"+variable[:-6]+"_All_Cases.png")
            #plt.show()
            plt.close()
            

#!!! OPTION 2
if option == 2:
    outdir = outdir+"/Option2/"
    csvdir = csvdir+"/Option2/"
    if not os.path.exists(csvdir):os.makedirs(csvdir)
    if not os.path.exists(outdir): os.makedirs(outdir)
    
    """
    For each Independent Variable being analyzed perform the aforementioned statistics on each case study and independent variable for the run.
    
    """

    ## START ANALYSIS
    analysis_start, analysis_end  = get_analysis_window(casestudy_time[0],analysis_start_hour_UTC, analysis_length_hrs)
    wrf_substeps, analysis_substeps = get_substeps(wrf_interval_min,analysis_interval_min)  
    #\ DO ONE VARIABLE AT A TIME
    for var_step in variables:
        
        variables_short = [var_step] 
        print(var_step)    #Puts it in a "short list"
        
        # Do each statistical analysis
        for stat_type in stats_list:
            iv_analysis = np.zeros((len(independent_var),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)

            # For each WRF configuration
            for z in range(len(independent_var)):
                iv_type = independent_var[z]
                iv_error = 0; iv_checks = 0;

                case_analysis = np.zeros((len(casestudy_time),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)
               
                # For each case study
                for m in range(len(casestudy_time)):
                    
                    case_time = casestudy_time[m]
                    
                    analysis_start, analysis_end  = get_analysis_window(case_time,analysis_start_hour_UTC, analysis_length_hrs)

                    cumulative_error = 0; cumulative_checks = 0;
                    simulation, short_time = fmt_run_path(case_time, iv_type)
                                    
                    # For each WRF domain in analysis get that data file and read it. If Empty->EXIT
                    listing = glob.glob(simulation)
                    if len(listing) == 0: print("INVALID PATH"); sys.exit(0)
                    print(case_time,"\t",iv_type)

                    #WRF OUTPUT FILE
                    ncfile = Dataset(listing[0])
                    
                    var_analysis = np.zeros((len(variables_short),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)
                    ###  Get's a single variable from top loop.... left here to keep everything else working. 
                    for p in range(len(variables_short)):
                        
                        variable = variables_short[p]
                        variable_error = 0; variable_checks = 0;
                        
                        ### GATHER VALIDATION DATA DIRECTORY FOR CASE
                        if dtype_usage == "10m":
                            if isRaw == True:   data_file = ver_data_dir+"/verify_case_study_data/"+dtype_usage+"/"+case_time[0:10]+'/' 
                            else:               data_file = ver_data_dir+"/hr_avg_trim/"+dtype_usage+"/"+case_time[0:10]+'/'
                        elif dtype_usage == "original":
                            if isRaw == True:   data_file = ver_data_dir+"/verify_case_study_data/"+dtype_usage+"/"+case_time[0:10]+'/'
                            else:               data_file = ver_data_dir+"/hr_avg_trim/"+dtype_usage+"/"+case_time[0:10]+'/'
                     
                        # PER VARIABLE - EXTRACT FOR ANALYSIS  (WRF-DATA)
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_uvmet.get_uvmet10_wspd_wdir.html?highlight=wrf%20wind%20direction%2010m   #10m wind speed    #UNIT m/s    
                        if variable == 'Wind_Speed (m/s)': WRF_VAR = wrf.g_uvmet.get_uvmet10_wspd_wdir(ncfile, timeidx=wrf.ALL_TIMES, method='cat',squeeze=True, cache=None, meta=False, _key=None, units='m s-1')[0]                    
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_uvmet.get_uvmet10_wspd_wdir.html?highlight=wrf%20wind%20direction%2010m       #10m wind direction
                        elif variable == 'Wind_Direction (deg)':  WRF_VAR = wrf.g_uvmet.get_uvmet10_wspd_wdir(ncfile, timeidx=wrf.ALL_TIMES, method='cat', squeeze=True, cache=None, meta=False, _key=None, units='m s-1')[1] #UNIT m/s                        
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_temp.get_tk.html?highlight=Air%20temperature      ## 2m air temperature KELVIN
                        elif variable == 'Air_Temperature (K)': WRF_VAR = wrf.getvar(ncfile,"T2",timeidx=wrf.ALL_TIMES,method='cat',squeeze=True,cache=None,meta=False) 
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_dewpoint.get_dp_2m.html?highlight=wrf.g_dewpoint.get_dp_2m        #2m dewpoint temperature KELVIN
                        elif variable == 'Dewpoint_Temperature (K)': WRF_VAR = wrf.g_dewpoint.get_dp_2m(ncfile,timeidx=wrf.ALL_TIMES, method='cat',squeeze=True,cache=None,meta=False,_key=None,units='K')
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_rh.get_rh_2m.html?highlight=relative%20humidity           #2m relative humidity   UNIT: %    
                        elif variable == "Relative Humidity (%)": WRF_VAR = wrf.g_rh.get_rh_2m(ncfile,timeidx=wrf.ALL_TIMES,method='cat',squeeze=True, cache=None, meta=False, _key=None)                 
                        #https://wrf-python.readthedocs.io/en/latest/internal_api/generated/wrf.g_pressure.get_pressure.html?highlight=pressure #SLP pressure
                        elif variable == "Pressure (Pa)": WRF_VAR = wrf.g_slp.get_slp(ncfile,timeidx=wrf.ALL_TIMES, method='cat',squeeze=True,cache=None,meta=False,_key=None,units='Pa')
                        else: print ("INVALID VARIABLE OPTION"); sys.exit(0)
                        
                        # GET WRF TIME STEP AHD REFORMAT
                        WRF_TIMES = wrf.extract_times(ncfile,timeidx=wrf.ALL_TIMES, method='cat',squeeze=True,cache = None, meta=False,do_xtime=False).astype(str)
                        #WRF_TIMES = wrf.g_times.get_times(ncfile,timeidx=wrf.ALL_TIMES,method='cat',squeeze=True,cache=None,meta=False,_key=None).astype(str)
                        WRF_DT = [""] * len(WRF_TIMES)
                        for ijk in range(len(WRF_TIMES)):
                            # FOR SOME REASON THERE ARE 9 miliseconds orecision when there should be 6
                            WRF_DT[ijk] = datetime.datetime.strptime(WRF_TIMES[ijk][:-3],'%Y-%m-%dT%H:%M:%S.%f')   
                            #dt= utc_dt.strftime('%Y-%m-%d %H:%M:%S')
                            
                        diff_wrf = WRF_DT[-1] - WRF_DT[0]
                        wrf_timestep = (WRF_DT[1] - WRF_DT[0]).total_seconds()
                        tot_sec_wrf = diff_wrf.total_seconds()
                        
                        if len(WRF_DT) != (tot_sec_wrf / wrf_timestep) + 1: print("WRF TIME NOT THE RIGHT LENGTH"); sys.exit(0)
                        
                        # Get verification data
                        verdat = glob.glob(data_file+"*")    
                        half_hourly_analysis = np.zeros((len(verdat),int(((analysis_end - analysis_start).total_seconds()/(analysis_interval_min * sec))+original_len))).astype(object)

                        # Loop through verification data
                        for verdex in range(len(verdat)):
                            hha_idx = 0; station_error = 0; stationCHECKS = 0;
        
                            #%% Read In Data   - Verification
                            data = pd.read_csv(verdat[verdex], low_memory=False)
                            data.columns.tolist()
                            # Mask missing data
                            data = data.mask(data == " ",other = np.nan)
                            data = data.mask(data == "",other = np.nan)
                            data = data.mask(data == -888888.0, other = np.nan)
                            data['Wind_Speed (m/s)'] = data['Wind_Speed (m/s)'].mask(data['Wind_Speed (m/s)'] < 0, other = np.nan)
                            
                            
                            ID_String = str(data['ID_String'][0])

                            half_hourly_analysis[verdex,0] = ID_String  # STORE IN ANALYSIS ARRAY
                            
                            
                            ## EXTRACT VERIFICATION DATA TIME
                            time = []
                            #SAMPLE: '2014-06-04T06:00:00.000000000'
                            if isRaw == True:
                                    Date = np.array(data['DATE'],dtype=str)
                                    for dte in Date:
                                        utc_dt= datetime.datetime(int(dte[0:4]),int(dte[4:6]),int(dte[6:8]),int(dte[8:10]),int(dte[10:12]),int(dte[12:14]))
                                        #dt= utc_dt.strftime('%Y-%m-%d %H:%M:%S')
                                        time.append(utc_dt)#utc_dt.strftime('%Y-%m-$dT%H:%M:%S'))
                            elif isRaw == False:
                                year =np.array(data['YEAR'],dtype=int) 
                                month =np.array(data['MONTH'],dtype=int) 
                                day = np.array(data['DAY'],dtype=int) 
                                hour =np.array(data['HOUR'],dtype=int) 
                                minute = np.array(data['MINUTE'],dtype=int) 
                                for idx in range(len(year)):
                                    utc_dt= datetime.datetime(year[idx],month[idx],day[idx],hour[idx],minute[idx])
                                    time.append(utc_dt)#utc_dt.strftime('%Y-%m-%dT%H:%M:%S.%f'))
                            
                            #The second half of this if (or) statement could be an issue... haven't tested it.
                            if len(time) != tot_sec_wrf / (wrf_interval_min * sec * wrf_substeps)+1:
                                if len(time) != tot_sec_wrf / (analysis_interval_min * sec * analysis_substeps)+1:
                                    print("VALIDATION DATA TIME NOT THE RIGHT LENGTH")
                                    continue
                                else:
                                    print("POTENTIALLY BIG PROBLEM BUT ERIC'S BEING TO LAZY TO TEST")
                                    print("This means (I HOPE) that the time is the length of the analysis time * subseps\n\t\t which means multiple analysis timesteps between wrf time steps")

                            ## LATITUDE AND LONGITUDE IN OBSERVATION TO LOC IN MODEL OUTPUT
                            obs_lat = np.array(data['Latitude'][0]) 
                            obs_long = np.array(data['Longitude'][0]) 
        
                            # PER VARIABLE - VERIFICATION
                            if variable == 'Wind_Speed (m/s)':  variable_data= np.array(data['Wind_Speed (m/s)'])
                            elif variable == 'Wind_Direction (deg)':  variable_data = np.array(data['Wind_Direction (deg)'])
                            elif variable == 'Air_Temperature (K)':  variable_data = np.array(data['Air_Temperature (K)'])
                            elif variable == 'Dewpoint_Temperature (K)':  variable_data = np.array(data['Dewpoint_Temperature (K)']) 
                            elif variable == "Relative Humidity (%)":  variable_data = np.array(data['Relative Humidity (%)'])
                            elif variable == "Pressure (Pa)":  variable_data = np.array(data['Pressure (Pa)'])
                            else: sys.exit(0)

                            # WRF VARIABLE FULL TIME SLICE AT ONE LOCATION
                            try:
                                x_y = wrf.ll_to_xy(ncfile,  obs_lat, obs_long)
                                #latlon = wrf.xy_to_ll(ncfile,  float(x_y[0]),float(x_y[1]))
                                TRIM_WRF_VAR = WRF_VAR[:,int(x_y[0]),int(x_y[1])]
                            except:
                                continue

            
                            ## FOCUS ON 8am to 8pm so 12UTC to 0UTC
                            ## CHANGED TO 6am to midnight that way it captures sunrise and sunset and after SB.
                            for i in range(0,len(time),analysis_substeps):
                                #Checks every half hour and 30 minutes
                                for j in range(0,len(WRF_DT),wrf_substeps):
                                    #Verification Data outside analysis window
                                    if time[i] < analysis_start or time[i] > analysis_end:
                                        continue
                                    #WRF Data outside analysis window
                                    elif WRF_DT[j]  < analysis_start or WRF_DT[j] > analysis_end:
                                        continue
                                    ## Correct time - MATCH!
                                    elif time[i] == WRF_DT[j]:
                                        if fillHeaders == False:
                                            header.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE
                                            header_Var.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE
                                            header_iv.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE
                                            header_case.insert(hha_idx+1, time[i].strftime("%H:%M")) # NAME ..... # AVERAGE

                                        # Verification Data is Missing Value
                                        if np.isnan(variable_data[i]) == True:
                                            half_hourly_analysis[verdex,hha_idx+1] = np.nan
                                            hha_idx +=1
                                            continue
                                        # WRF Data is Missing Value
                                        elif np.isnan(TRIM_WRF_VAR[j]) == True:
                                            half_hourly_analysis[verdex,hha_idx+1] = np.nan
                                            hha_idx +=1
                                            continue
                                        else:
                                            #GOOD DATA - ANALYZE BASED ON THE STATISTIC BEING PERFORMED (based on iteration of the stat array)
                                            if stat_type == "MAE":
                                                #∑|(Xf - Xo)| / n
                                                ylabel_str = "Mean Absolute Error"
                                                abs_error = stats.absolute_error(TRIM_WRF_VAR[j], variable_data[i])
                                                half_hourly_analysis[verdex,hha_idx+1] = abs_error
            
                                                station_error += abs_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            
                                            elif stat_type == "MAPE":
                                                ylabel_str = "Mean Absolute Percent Error"

                                                # ( ∑|Xf - Xo| / Xo ) / n or relative error:|Xf - Xo| / Xo then multiply by 100 for %
                                                # then ∑x/n for mean Absolute percent error

                                                rel_error = stats.relative_error(TRIM_WRF_VAR[j], variable_data[i])
                                                half_hourly_analysis[verdex,hha_idx+1] = rel_error * 100.0
                                                    
                                                station_error += rel_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            
                                            elif stat_type == "BIAS":
                                                #∑(Xf - Xo) / n
                                                ylabel_str = "Bias"
                                                fcst_error = stats.forecast_error(TRIM_WRF_VAR[j], variable_data[i])
                                                half_hourly_analysis[verdex,hha_idx+1] = fcst_error
                                                station_error += fcst_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            
                                            
                                            elif stat_type == "RMSE":
                                                ylabel_str = "Root Mean Square Error"

                                                rel_error = stats.forecast_error(TRIM_WRF_VAR[j], variable_data[i])  ** 2
                                                half_hourly_analysis[verdex,hha_idx+1] = rel_error
                                                    
                                                station_error += rel_error
                                                stationCHECKS +=1
                                                hha_idx +=1
                                                continue
                                            # append error by hour any non checks filled with np.nan
                                            else:
                                                print("INVALID STATISTICAL OPTION.... ADD NEAR LINE 500")
                                                sys.exit(0)

                                            # DO MORE STUFF HERE

                                    # This will always happen even if there is no wrf match to the time.
                                    elif time[i] != WRF_DT[j] and WRF_DT[j] == WRF_DT[-1]:
                                        continue
        
                                    # THIS WILL ALWAYS HAPPEN AT THE END OF THE ITERATION IF NO MATCH
                                    elif time[i] == time[-1]:
                                        continue
                                    
                            # MAKE TRUE TO PREVENT HEADERS FROM BEING REFILLED EACH TIME        
                            fillHeaders=True

                            # IF NO DATA (STAT) ANALYSIS ELSE CALCULATE THE MEAN OF THE STAT AND PRINT       
                            if stationCHECKS == 0:
                                print ("No Checks Performed At ", ID_String)
                                continue
                            else:
                                # ADD STATION ERROR TO VARIABLE ERROR
                                variable_error += station_error
                                variable_checks += stationCHECKS
                                station_calc_err = station_error/stationCHECKS
                                #print(ID_String,"Error: \t\t" , station_calc_err)
                            
                        ## CALCULATE VARIANCE HERE
                    
                    
                        ### AVERAGE BY LOCATION       

                        ## TAKE THE MEAN OF ALL CHECKS (OR SQ MEAN FOR RMSE) FOR EACH HOUR.... THEN FOR EACH STATION AND APPEND    
                        # MASK ZEROS FROM INITIALIZED ARRAY. NO CHECKS WERE PERFORMED AT THOSE LOCATIONS.
                        hr_stations_stat = pd.DataFrame(half_hourly_analysis,index=None)
                        hr_stations_stat = hr_stations_stat.mask(hr_stations_stat == 0, other=np.nan)
                        if stat_type == "RMSE":
                            vertAvg = (np.nanmean((np.array(hr_stations_stat)[:,1:]).astype(float), axis=0)) ** 0.5
                        else:
                            vertAvg = np.nanmean((np.array(hr_stations_stat)[:,1:]).astype(float), axis=0) #vertically (DEFAULT: axis=0),

                        tmp1 = np.zeros(len(vertAvg)+1).astype(object)
                        tmp1[0] = "Hr_Avgs"
                        tmp1[1:] = vertAvg
                        half_hourly_analysis2 = pd.concat((pd.DataFrame(half_hourly_analysis),pd.DataFrame(tmp1).T))
                        half_hourly_analysis2 = half_hourly_analysis2.mask(half_hourly_analysis2 == 0, other=np.nan)

                        per_station_stats = np.array(half_hourly_analysis2)
                        #horizontally (axis=1)
                        
                        if stat_type == "RMSE":
                            horAvg = (np.nanmean(per_station_stats[:,1:].astype(float), axis=1)) ** 0.5
                        else:
                            horAvg = np.nanmean(per_station_stats[:,1:].astype(float), axis=1)
                            
                        complete_station_stats = pd.concat((pd.DataFrame(per_station_stats),pd.DataFrame(horAvg)),axis=1)
                        complete_station_stats.columns =header
                        
                        # WRITE TO CSV - 4 files per case subdir (so about 16 files per variable)
                        #complete_station_stats.to_csv(csvdir+"Case_"+short_time.replace("-","_").strip()+"_"+stat_type+"_"+domain+"_"+variable[:-5].strip()+".csv", index=False,float_format='%.3f')
                        
                        
                        var_check =np.array(complete_station_stats)[len(complete_station_stats)-1][:-1]
                        var_check[0] = case_time
                        var_analysis[p] = var_check # AVERAGE OVER ALL STATIONS (NOT TIME)  ## SHOULD BE length 0

                        if variable_checks == 0:
                            print("No checks performed for ", variable)
                            continue
                        else:
                            cumulative_error += variable_error
                            cumulative_checks += variable_checks
                            var_err = variable_error/variable_checks
                            #print(variable, "Error: \t\t",var_err )
                            
                            
                    case_type_check = var_analysis[p]
                    case_type_check[0] = case_time
                    case_analysis[m] = case_type_check  
                    if cumulative_checks == 0:
                        print("No checks performed for ", case_time,"\t",iv_type,"\t", domain, '\t',variable)
                        continue
                    else:
                        cu_err =cumulative_error/cumulative_checks
                        iv_error +=cumulative_error
                        iv_checks +=cumulative_checks
                        #print(case_time,"\t",variable," "+stat_type+": \t\t", cu_err)

                ### AVERAGE BY CASE       

                ## TAKE THE MEAN OF ALL CHECKS (OR SQ MEAN FOR RMSE) FOR EACH HOUR OF EACH DATA ASSIMILATION TYPE ( NOW ONLY ONE VARIABLE AT A TIME) AND FOR EACH TYPE... AND APPEND
                ## VERTICAL APPEND IS WHAT GOES IN THE VERIFICATION_TABLE SPREAD SHEET BY USER
                vertAvgCase = np.nanmean((case_analysis[:,1:]).astype(float), axis=0)   
                tmp4 = np.zeros(len(vertAvgCase)+1).astype(object)
                tmp4[0] = "Case_Avg"
                tmp4[1:] = vertAvgCase
                caseAnaly2 = pd.concat((pd.DataFrame(case_analysis),pd.DataFrame(tmp4).T))
                ivAnaly2 = caseAnaly2.mask(caseAnaly2 == 0, other=np.nan)
                caseAnaly2 = np.array(caseAnaly2)
                horAvgCase = np.nanmean(caseAnaly2[:,1:].astype(float), axis=1)                #horizontally (axis=1)
                case22 = pd.concat((pd.DataFrame(caseAnaly2),pd.DataFrame(horAvgCase)),axis=1)
                case22.columns =header_case
                #case22.to_csv(csvdir+iv_type+"_"+stat_type+"_"+variable[:-6]+".csv", index=False,float_format='%.3f')

                iv_check222 =np.array(case22)[len(case22)-1][:-1]
                iv_check222[0] = iv_type
                iv_analysis[z] = iv_check222      
                
                ## PLOT ERROR BY CASE BY ASSIMILATION TYPE
                #fig,ax = plt.subplots(figsize=(14,6)) 
                #colors = ['red','green','blue','purple','black']
                #colorcount = 0
                #for row in np.array(case22):
                #    ax.plot(header[1:-1], row[1:-1], color = colors[colorcount],label = row[0])
                #    colorcount +=1
                #ax.set_title(ylabel_str+" for "+iv_type+"\n"+variable.replace("_"," "), fontsize=16)
                #ax.set_xlabel("Time (UTC)", fontsize=14)
                #ax.set_ylabel(ylabel_str +" ("+stat_type+")", fontsize=14)
                #ax.legend(loc='best', fontsize=14)
                #ax.minorticks_on()
                #plt.gcf().autofmt_xdate()
                #plt.savefig(outdir+iv_type+"_"+stat_type+"_"+variable[:-6]+".png")
                ##plt.show()
                #plt.close()     
                
                if iv_checks == 0:
                    print("No checks performed for ", case_time,"\t",iv_type,"\t", domain, '\t',variable)
                else:
                    iv_err =iv_error/iv_checks
                    #print(case_time,"\t",variable," "+stat_type+": \t\t", iv_err)
            ### AVERAGE BY HOUR       
            ## TAKE THE MEAN OF ALL CHECKS (OR SQ MEAN FOR RMSE) FOR EACH HOUR OF ALL CASES ( NOW ONLY ONE VARIABLE AT A TIME) AND FOR EACH CASE... AND APPEND            
            vertAvgIV = np.nanmean((iv_analysis[:,1:]).astype(float), axis=0)
            tmp5 = np.zeros(len(vertAvgIV)+1).astype(object)
            tmp5[0] = plt_str
            tmp5[1:] = vertAvgIV
            ivAnaly2 = pd.concat((pd.DataFrame(iv_analysis),pd.DataFrame(tmp5).T))
            ivAnaly2 = ivAnaly2.mask(ivAnaly2 == 0, other=np.nan)
            ivAnaly2 = np.array(ivAnaly2)
            horAvgIV = np.nanmean(ivAnaly2[:,1:].astype(float), axis=1)
            iv3 = pd.concat((pd.DataFrame(ivAnaly2),pd.DataFrame(horAvgIV)),axis=1)
            iv3.columns =header_iv
            iv3.to_csv(csvdir+"All_Assimilation_Types_"+stat_type+"_"+variable[:-6]+".csv", index=False,float_format='%.3f')
               
            
            ## PLOT ERROR BY CASE BY HOUR
            fig2, ax1 = plt.subplots(figsize=(14,6)) 
            colors = ['red','green','blue','purple','black']
            colorcount = 0
            for row in np.array(iv3):
                ax1.plot(header[1:-1], row[1:-1], color = colors[colorcount],label=row[0])
                colorcount +=1
            ax1.set_title(ylabel_str+" for All Assimilation Configurations\n"+variable.replace("_"," "), fontsize=16)
            ax1.set_xlabel("Time (UTC)", fontsize=14)
            ax1.set_ylabel(ylabel_str +" ("+stat_type+")", fontsize=14)
            ax1.legend(loc='best', fontsize=14)
            ax1.minorticks_on()
            plt.gcf().autofmt_xdate()
            #plt.savefig(outdir+stat_type+"_"+variable[:-6]+"_All_Cases.png")
            #plt.show()
            plt.close()
            