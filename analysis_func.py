#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 16:03:18 2019

@author: allenea
"""
#IMPORTS
import os
import sys
import glob
from datetime import datetime, timedelta
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import wrf
if os.environ.get('DISPLAY', '') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')

def fmt_run_path(case, independent_var, domain, path_pwd):
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
    dtuple = datetime.strptime(case, "%Y-%m-%d_%H:%M")
    short_time = dtuple.strftime('%-m-%-d-%Y')
    simulation = "/"+prefix_casestudy+short_time+"/"+independent_var+"_"+\
                    short_time.replace("-", "_")+"/"

    model_path = path_pwd+simulation+filename
    return model_path, short_time


def get_data_file(ver_data_dir, case_time, dtype_usage):
    """Get the file name for the observation data"""
    ### GATHER VALIDATION DATA DIRECTORY FOR CASE
    if dtype_usage == "10m":
        data_file = ver_data_dir+"/"+dtype_usage+"/"+case_time[0:10]+'/'
    elif dtype_usage == "original":
        data_file = ver_data_dir+"/"+dtype_usage+"/"+case_time[0:10]+'/'

    obsdat = glob.glob(data_file+"*")
    if len(obsdat) != 1:
        print("EXITING. TOO MANY FILES.", obsdat)
        sys.exit(0)

    return obsdat[0]


def get_wrf_data(ncfile, variable):
    """Add your data accordingly here.  What variables will you need?"""
    if variable == 'Wind_Speed (m/s)':#10m wind speed    UNIT m/s
        wrf_var = wrf.g_uvmet.get_uvmet10_wspd_wdir(ncfile, timeidx=wrf.ALL_TIMES,\
                                                method='cat', squeeze=True, cache=None,\
                                                meta=False, _key=None, units='m s-1')[0]

    elif variable == 'Wind_Direction (deg)':#10m wind direction UNIT m/s and degrees
        wrf_var = wrf.g_uvmet.get_uvmet10_wspd_wdir(ncfile, timeidx=wrf.ALL_TIMES,\
                                                method='cat', squeeze=True, cache=None,\
                                                meta=False, _key=None, units='m s-1')[1]

    #2m air temperature KELVIN
    elif variable == 'Air_Temperature (K)':
        wrf_var = wrf.getvar(ncfile, "T2", timeidx=wrf.ALL_TIMES, method='cat',\
                                             squeeze=True, cache=None, meta=False)

    #2m dewpoint temperature KELVIN
    elif variable == 'Dewpoint_Temperature (K)':
        wrf_var = wrf.g_dewpoint.get_dp_2m(ncfile, timeidx=wrf.ALL_TIMES,\
                                       method='cat', squeeze=True, cache=None,\
                                       meta=False, _key=None, units='K')

    #2m relative humidity   UNIT: %
    elif variable == "Relative Humidity (%)":
        wrf_var = wrf.g_rh.get_rh_2m(ncfile, timeidx=wrf.ALL_TIMES,\
                                 method='cat', squeeze=True, cache=None,\
                                 meta=False, _key=None)

    #SLP pressure UNITS: Pa
    elif variable == "Pressure (Pa)":
        wrf_var = wrf.g_slp.get_slp(ncfile, timeidx=wrf.ALL_TIMES,\
                                    method='cat', squeeze=True, cache=None,\
                                    meta=False, _key=None, units='Pa')

    elif variable == "U10":
        wrf_var = wrf.g_uvmet.get_uvmet10(ncfile, timeidx=wrf.ALL_TIMES,\
                                          method='cat', squeeze=True, cache=None,\
                                          meta=False, _key=None, units='m s-1')[0]

    elif variable == "V10":
        wrf_var = wrf.g_uvmet.get_uvmet10(ncfile, timeidx=wrf.ALL_TIMES,\
                                      method='cat', squeeze=True, cache=None,\
                                      meta=False, _key=None, units='m s-1')[1]

    else:
        try:
            wrf_var = wrf.getvar(ncfile, variable, timeidx=wrf.ALL_TIMES,\
                             method='cat', squeeze=True, cache=None, meta=False)
        except:
            sys.exit("INVALID VARIABLE OPTION")

    return wrf_var

def get_obs_data(data, variable):
    """These variables from your data file should match the variable names above
    You will use those header variable names to get the data from WRF and the
    observation dataset. The user will need to configure to fit their data."""
    # PER VARIABLE - VERIFICATION
    if variable == 'Wind_Speed (m/s)':
        variable_data = np.array(data['Wind_Speed (m/s)'])
    elif variable == 'Wind_Direction (deg)':
        variable_data = np.array(data['Wind_Direction (deg)'])
    elif variable == 'Air_Temperature (K)':
        variable_data = np.array(data['Air_Temperature (K)'])
    elif variable == 'Dewpoint_Temperature (K)':
        variable_data = np.array(data['Dewpoint_Temperature (K)'])
    elif variable == "Relative Humidity (%)":
        variable_data = np.array(data['Relative Humidity (%)'])
    elif variable == "Pressure (Pa)":
        variable_data = np.array(data['Pressure (Pa)'])
    elif variable in ("U10", "V10"):
        u10, v10 = wind_components(np.array(data['Wind_Speed (m/s)']),\
                                   np.array(data['Wind_Direction (deg)']))
        if variable == "U10":
            variable_data = u10
        elif variable == "V10":
            variable_data = v10
        else:
            print("MAJOR ERROR IN U/V10 GATHERING.")
    else:
        try:
            variable_data = np.array(data[variable])
        except:
            sys.exit("INVALID VARIABLE OPTION")
    return variable_data

def get_obs_metadata(data):
    """Get the observation data metadata"""
    id_string = np.array(data['ID_String'])
    obs_lat_list = np.array(data['Latitude'])
    obs_lon_list = np.array(data['Longitude'])
    fm_string_list = np.array(data['FM_string'])
    return id_string, obs_lat_list, obs_lon_list, fm_string_list


def get_substeps(wrf_interval_min, analysis_interval_min):
    """
    Calculates the analysis window. Doesn't go multiple months or years.

    (int) wrf_interval_min:  30
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
        sys.exit("Not an even time-step between the data and the model. Exiting get_substep")

    if analysis_interval_min < wrf_interval_min:
        sys.exit("Analysis cannot be more frequent than the WRF interval. Exiting get_substep")
    return wrf_substeps, analysis_substeps


# Get analysis window
def get_analysis_window(case_time, analysis_start_hour_utc, analysis_length_hrs, runtime):
    """
    Calculates the analysis window. Doesn't go multiple months or years.

    (str) Case_Time: i.e. '2014-06-04_12:00'
    (int) analysis_start_hour:  12 # 00UTC
    (int) analysis_length_hrs: i.e. 24 (00UTC + 1 day)
    """
    if analysis_start_hour_utc + analysis_length_hrs > runtime:
        sys.exit("Analysis extends longer than declared runtime. Exiting...")
    else:
        tdelta_analysis = timedelta(hours=analysis_start_hour_utc)
        tdelta_end = timedelta(hours=analysis_start_hour_utc+analysis_length_hrs)

        time_object = datetime.strptime(case_time, '%Y-%m-%d_%H:%M')
        analysis_start = time_object + tdelta_analysis
        analysis_end = time_object+tdelta_end
        return analysis_start, analysis_end


def get_land_value(ncfile, wrf_var, latitude, longitude):
    """WRF LANDMAKS VALUE AT ONE LOCATION"""
    try:
        x_y = wrf.ll_to_xy(ncfile, latitude, longitude, meta=False)
        return wrf_var[int(x_y[1]), int(x_y[0])]
    except ValueError:
        return None


def get_values_loc(ncfile, wrf_var, landmask, land_type, latitude, longitude, analysis_type=True):
    """WRF VARIABLE FULL TIME SLICE AT ONE LOCATION"""
    #current_spot_value
    #count = 0
    #Current
    #x_y[1], x_y[0]
    #x_y[1]+1, x_y[0]
    #x_y[1]-1, x_y[0]
    #x_y[1], x_y[0]+1
    #x_y[1], x_y[0]-1
    #ADD
    #x_y[1]+1,  x_y[0]+1
    #x_y[1]-1,  x_y[0]-1
    #x_y[1]+1,  x_y[0]-1
    #x_y[1]-1,  x_y[0]+1
    x_y = wrf.ll_to_xy(ncfile, latitude, longitude, meta=False)
    try:
        valid_loc = wrf_var[int(x_y[1]), int(x_y[0])]
    except ValueError:
        return None
    if analysis_type:
        #Value at the point
        return valid_loc
    else:
        sum_values = 0.0
        num_values = 0
        #Value at the point 0 = west-east and 1 = north-south
        for i in range(-1, 1+1):
            for j in range(-1, 1+1):
                #print("X+", j, "Y+",i)
                try:
                    temp = wrf_var[int(x_y[1]+j), int(x_y[0]+i)]
                    ltype = landmask[int(x_y[1]+j), int(x_y[0]+i)]
                except ValueError:
                    continue

                if land_type == ltype:
                    sum_values += temp
                    num_values += 1
                else:
                    pass
                #print(land_type, ltype, temp, num_values)
        #print(sum_values, num_values)
        if num_values == 0:
            return None
        return sum_values/num_values

def wind_components(wspd, wdir):
    """CALCULATE U and V"""
    degrad = math.pi / 180.0
    wdir_rads = wdir * degrad
    u_wind = -wspd * np.sin(wdir_rads)
    v_wind = -wspd * np.cos(wdir_rads)
    return u_wind, v_wind


def remove_data_outside(ncfile, data):
    """Identify and remove any observations out of the range of the domain"""
    dom_lat_max = np.max(wrf.g_latlon.get_lat(ncfile, timeidx=0, meta=False))
    dom_lat_min = np.min(wrf.g_latlon.get_lat(ncfile, timeidx=0, meta=False))
    dom_lon_max = np.max(wrf.g_latlon.get_lon(ncfile, timeidx=0, meta=False))
    dom_lon_min = np.min(wrf.g_latlon.get_lon(ncfile, timeidx=0, meta=False))

    # HANDLES LAT/LON OUTSIDE WRF DOMAIN
    out_of_range = data[(data.Latitude > dom_lat_max) |\
                        (data.Latitude < dom_lat_min) &\
                        (data.Longitude > dom_lon_max) |\
                        (data.Longitude < dom_lon_min)].index
    if len(out_of_range) != 0:
        print("out_of_range INDEX", out_of_range)
    data.drop(out_of_range, inplace=True)
    return data


def get_wrf_datetime_obj(ncfile):
    """Get wrf timesteps as datetime objects"""
    #Get WRF time-step and reformat
    wrf_times = wrf.extract_times(ncfile, timeidx=wrf.ALL_TIMES,\
                              method='cat', squeeze=True, cache=None,\
                              meta=False, do_xtime=False).astype(str)

    wrf_dt = [""] * len(wrf_times)
    for ijk in range(len(wrf_times)):
        # FOR SOME REASON THERE ARE 9 miliseconds precision when there should be 6
        wrf_dt[ijk] = datetime.strptime(wrf_times[ijk][:-3], '%Y-%m-%dT%H:%M:%S.%f')

    diff_wrf = wrf_dt[-1] - wrf_dt[0]
    wrf_timestep = (wrf_dt[1] - wrf_dt[0]).total_seconds()
    tot_sec_wrf = diff_wrf.total_seconds()

    if len(wrf_dt) != (tot_sec_wrf / wrf_timestep) + 1:
        print("WRF TIME NOT THE RIGHT LENGTH")
        sys.exit(0)

    return wrf_dt


def get_obs_datetime_obj(data):
    """Get observation date-time data as datetime objects"""
    t_time = []
    #SAMPLE: '2014-06-04T06:00:00.000000000'
    year = np.array(data['YEAR'], dtype=int)
    month = np.array(data['MONTH'], dtype=int)
    day = np.array(data['DAY'], dtype=int)
    hour = np.array(data['HOUR'], dtype=int)
    minute = np.array(data['MINUTE'], dtype=int)
    for idx in range(len(year)):
        utc_dt = datetime(year[idx], month[idx], day[idx], hour[idx], minute[idx])
        t_time.append(utc_dt)
    return t_time


def print_table(table, variable, decimals):
    """Nicely print the statistics table"""
    blank_index = [''] * len(table)
    table.index = blank_index
    rounded_table = table.round(decimals)

    print()
    print()
    print('VARIABLE: ', variable)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        pd.set_option('display.max_rows', 15)
        pd.set_option('display.max_columns', 15)
        pd.set_option('display.width', 1000)
        print(rounded_table)
    print()
    print()


def split_list(lst, split):
    """Yield successive n-sized chunks from l."""
    if not split:#is 0
        split = len(lst)
    return [lst[i:i + split] for i in range(0, len(lst), split)]


def print_bad_output(badlist):
    """Nicely print the list of bad observation stations - by land type"""
    #All statistics for a single meteorological variable
    print("The following station(s) model-adjacent location(s) are opposite of their"+\
          " true\nland types (water/land). If single_point_analysis is False, "+\
          "then these are\ncorrected and the "+\
          "average consists of only neighboring grid cells that\nshare the same true land type.")
    print()
    bad_split = split_list(badlist, 5)
    for eric in range(len(bad_split)):
        bad_split[eric] = str(bad_split[eric]).replace("[", " ")
        bad_split[eric] = str(bad_split[eric]).replace("]", " ")
        print("\t", bad_split[eric])


def make_plot(fig_outfile, variable, df, stat_type, header, ylabel_str):
    """Make a time-series plot of the given statistic over time"""
    ## PLOT ERROR BY CASE BY HOUR
    fig2, ax1 = plt.subplots(figsize=(14, 8))
    colors = ['black', "gray", 'orange', 'green', 'blue', 'purple', 'magenta',\
              'red', 'green', 'blue', 'purple', 'magenta', 'teal']
                # Put new color at the front if including NARR run
    colorcount = 0
    for row in np.array(df):
        if "SST" in row[0] or "NDA" in row[0]:
            ax1.plot(header[1:-1], row[1:-1], color=colors[colorcount], marker="o",\
                     markeredgecolor='black', label=row[0])
        elif "Average" in row[0]:
            ax1.plot(header[1:-1], row[1:-1], color=colors[colorcount], label=row[0])
        else:
            ax1.plot(header[1:-1], row[1:-1], color=colors[colorcount],\
                     marker="d", label=row[0])
        colorcount += 1
    ax1.set_title(ylabel_str+" for All Configurations\n"+\
                  variable.replace("_", " "), fontsize=18, fontweight='bold')

    ax1.legend(loc='center left', bbox_to_anchor=(1, 0.65), numpoints=1, fontsize=14)
    ax1.set_xticks(header[1:-1][::2])
    ax1.minorticks_on()
    y_ticklst = ["%.1f"%item for item in ax1.get_yticks()]
    ax1.set_yticklabels(y_ticklst, fontsize=16, fontweight='bold')
    ax1.set_xticklabels(header[1:-1:2], fontsize=16, fontweight='bold')
    ax1.set_ylabel(ylabel_str +" ("+stat_type+")", fontsize=16, fontweight='bold')
    ax1.set_xlabel('Model Hour', fontsize=16, fontweight='bold')
    #plt.gcf().autofmt_xdate()
    plt.savefig(fig_outfile, bbox_inches='tight')
    #plt.show()
    plt.close()
