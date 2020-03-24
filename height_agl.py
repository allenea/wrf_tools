"""ERIC ALLEN CODE FOR Parallel WRF AGL HGT Analysis"""
import os
#import sys
import glob
import time
from datetime import datetime
import multiprocessing as mp
import numpy as np
from wrf import getvar
from netCDF4 import Dataset

print("Max Number of processors: ", mp.cpu_count())

GRAVITY = 9.81

def fmt_run_path(model_data_dir, case, ivc, dom):
    """
    SETS FILE FORMAT FOR CASES AND THEIR VARIATIONS
    Files should be arranged and named so you can simply look through.
    """
    filename = "wrfout_d"+dom+"_*"

    prefix_casestudy = "CaseStudy_"
    dtuple = datetime.strptime(case, "%Y-%m-%d_%H:%M")
    stime = dtuple.strftime('%-m-%-d-%Y')
    sims = "/"+prefix_casestudy+stime+"/"+ivc+"_"+stime.replace("-", "_")+"/"

    model_path = model_data_dir+sims+filename

    return model_path, stime

def get_agl(coordinate):
    """Convert Geopotential Height to actual height ASL --> AGL"""
    level, lat, lon = coordinate
    asl_hgt = ((ph.isel(bottom_top_stag=level, south_north=lat, west_east=lon) +\
                ph.isel(bottom_top_stag=level+1, south_north=lat, west_east=lon))/2) +\
                ((phb.isel(bottom_top_stag=level, south_north=lat, west_east=lon) +\
                  phb.isel(bottom_top_stag=level+1, south_north=lat, west_east=lon))/2) \
                  / GRAVITY
    agl_hgt = asl_hgt - hgt.isel(south_north=lat, west_east=lon)

    return (level, lat, lon, float(agl_hgt.values))

if __name__ == '__main__':
    start_time = time.time()
    # Model Run Information
    #data_directory = os.path.join("/", "home", "work", "clouds_wind_climate",\
    #                              "WRF4", "DelWRF", "SAVE_OUTPUTS")
    data_directory = os.path.join("/", "Volumes", "EA_BACKUP", "SAVE_OUTPUTS")

    domain = "03"
    casestudy_time = '2014-06-03_12:00'
    independent_var = "ALL"

    # Retrieve and Open the datafile
    simulation, _short_time = fmt_run_path(data_directory, casestudy_time, independent_var, domain)
    listing = glob.glob(simulation)
    ncfile = Dataset(listing[0])


    # Domain doesn't change so the reference time can stay the same
    reference_time_idx = 0

    # Retrieve the variables necessary to calculate AGL Height (m)
    # We need to unstagger the vertical coordinate  (effectively -1)
    # float PH(Time, bottom_top_stag, south_north, west_east) #"m2 s-2"
    # float PHB(Time, bottom_top_stag, south_north, west_east) #"m2 s-2"
    phb = getvar(ncfile, "PHB", timeidx=reference_time_idx)
    ph = getvar(ncfile, "PH", timeidx=reference_time_idx)
    hgt = getvar(ncfile, "HGT", timeidx=reference_time_idx) #"m"

    # Set the dimensions of the WRF domain
    levels = ncfile.dimensions.get('bottom_top').size
                        # MIN:must be greater than 0
                        # MAX:one less than the unstaggered dimension #

    south_north = ncfile.dimensions.get("south_north").size

    west_east = ncfile.dimensions.get("west_east").size


    # Create pairs for arguments (parallel)
    arg_pairs = [(k, i, j) for i in range(south_north)\
                             for j in range(west_east)\
                             for k in range(levels)]

    # Starts # of worker processor as the CPU has available
    pool = mp.Pool(processes=mp.cpu_count())
    print("Number of Processors: ", pool._processes)

    # Run func get_agl in parallel using the arg_pair coordinates
    return_values = pool.map(get_agl, arg_pairs)

    #Empty array which will eventually hold all the AGL data.
    data = np.empty((levels, south_north, west_east))
    for i, j, k, agl in return_values:
        data[i, j, k] = agl

    #AVERAGE OVER LAT/LON - Level specific average
    min_result = np.nanmin(np.nanmin(data, axis=2), axis=1)
    #print(min_result)
    max_result = np.nanmax(np.nanmax(data, axis=2), axis=1)
    #print(max_result)
    mean_result = np.nanmean(np.nanmean(data, axis=2), axis=1)
    #print(mean_result)
    #%%
    #Make a nice table
    print("\nThe Minimum, Maximum and Average AGL Height (m)\nAnalysis of WRF Output:\n\tDomain: "+\
          domain+", Case: "+_short_time+", Type: "+independent_var+"\n")
    print("%-6s"%"Level"+"\t%8s"%"Minimum"+"\t\t%8s"%"Maximum"+"\t\t%8s"%"Average")
    #print("Level   \tMinimum\t\t\tMaximum\t\t\tAverage")
    print("----------------------------------------------------------------")
    for lvl in range(levels):
        print("%-5i"%(lvl+1)+"\t%8.2f"%min_result[lvl]+\
              "\t\t%8.2f"%max_result[lvl]+"\t\t%8.2f"%mean_result[lvl])
    pool.close()
    print("\n--- %s seconds ---" % (time.time() - start_time))
    print("Unstaggered --> Staggered should result in one less vertical level.")
