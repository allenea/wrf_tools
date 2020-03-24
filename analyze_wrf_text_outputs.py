#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 28 15:23:32 2018
Python 3.6
Last Modified:  9/20/2018 6:30PM

@author: allenea

Analyzes:
    WPS OUTPUTS
    OBSGRID OUTPUTS
    WRF OUTPUTS
"""
##IMPORTS
import os
#import sys
from datetime import datetime
import glob
import pandas as pd

# =============================================================================
### NAMING STRUCTURE THAT POINTS TO THE DIRECTORY or DIRECTORIES
DATES = ['YYYY-MM-DD_HH:MM']

INDEPENDENT_VARIABLES = ["RUN_NAME"]

MODEL_DATA_DIR = os.path.abspath('../../SAVE_OUTPUTS/')



for date in DATES:
    #for model in models
    for type1 in INDEPENDENT_VARIABLES:

        prefix_casestudy = "CaseStudy_"
        dtuple = datetime.strptime(date, "%Y-%m-%d_%H:%M")
        short_time = dtuple.strftime('%-m-%-d-%Y')
        mydir = MODEL_DATA_DIR+'/'+prefix_casestudy+ short_time + '/'+type1 +\
                                    '_' + short_time.replace('-', '_') + '/'

# =============================================================================
        ### ABOVE: POINT TO THE DIRECTORY...
        print("----------------------START OF Folder--------------------------")
        print(mydir)
        smallSize = len(mydir)
        filelist = glob.glob(mydir+'*')
        filelist.sort()

        #Case Numbers
        num_errors = 0
        num_warnings = 0
        num_tbounds = 0
        num_cfl = 0

        for file in filelist:
            shortfile = file[smallSize:]

            ## OBSGRID TEXT FILES
            if "obsgrid" in shortfile:
                infile = open(file, 'r')
                readData = infile.readlines()
                buddyCount = 0
                errmxCount = 0
                countQC = 0

                countEmpty = 0
                countOutside = 0
                countIngested = 0

                countReported = 0
                countDuplicates = 0
                countMerged = 0

                #print (shortfile)
                for row in readData:
                    row = row.rstrip("\n")
                    if "BUDDY" in row:
                        buddyCount += 1
                        if buddyCount > 9:
                            countQC += 1
                            #print date, "\t",  type1,"\t", buddyCount - 9, "Buddy Counts"
                    if "ERRMX" in row:
                        countQC += 1
                        errmxCount += 1
                        #print date, "\t",  type1,"\t", errmxCount , "ERRMX Counts"

                    if "Number of observations successfully ingested:" in row:
                        tmp = row.split(":")[1]
                        valINGEST = int(tmp.rstrip("."))
                        countIngested += valINGEST
                        #print "Ingested:  ",valINGEST, "  . Total:  ", countIngested

                    if "Number of empty observations discarded:" in row:
                        tmp = row.split(":")[1]
                        numEmpty = int(tmp.rstrip("."))
                        if numEmpty != 0:
                            countEmpty += numEmpty
                            print("EMPTY!!!:  ", numEmpty)

                    if "Number of observations discarded outside of domain:" in row:
                        tmp = row.split(":")[1]
                        numDiscard = int(tmp.rstrip("."))
                        if numDiscard != 0:
                            countOutside += numDiscard
                            #print("Discarded outside the domain:  ", countOutside)

                    if "merged locations" in row:
                        # Of the   100 observations reported,
                        #  80 of them are duplicates, leaving    20 merged locations
                        #print row
                        tmp = row.split("Of the")[1]
                        #print tmp
                        tmp2 = tmp.split(" observations reported,")
                        reported = tmp2[0]
                        #print reported
                        tmp3 = tmp2[1].split("of them are duplicates, leaving")
                        duplicates = tmp3[0]
                        #print tmp3
                        tmp4 = tmp3[1].split(" merged locations")
                        merged = tmp4[0]

                        #print "reported:  " ,reported,  "  .duplicates:  ",
                        #       duplicates, ".merged:  ", merged
                        #break
                        countReported += int(reported)
                        countDuplicates += int(duplicates)
                        countMerged += int(merged)

                print()
                print()
                print("Date:  " + date   + ".  Type:  " + type1)
                print(shortfile)
                print("Failed Quality Control:   ", countQC)
                print("        MAX ERROR TEST:   ", errmxCount)
                print("        BUDDY TEST:       ", buddyCount - 9)
                # 9 is the number of "BUDDY" variables in the namelist file
                print("Number of Observations Ingested:         ", countIngested)
                print("Number of Observations Empty:            ", countEmpty)
                print("Number of Observations Outside Domain:   ", countOutside)
                print()
                print("Number of Observations Reported:     ", countReported)
                print("Number of Observations Duplicates:   ", countDuplicates)
                print("Number of Observations Merged:       ", countMerged)
                print("AVAILABLE IN WRF:  ", countMerged)
                print()
                print()


            ## OBSGRID DATA FILES
            elif "OBS_DOMAIN" in shortfile:
                if os.stat(file).st_size == 0:
                    print("FILE IS EMPTY:"+ file)
                    continue
                infile = open(file, 'r')
                readData = infile.readlines()
                questionable = []
                missingData = 0
                countNoBuddy = 0
                print("AVAILABLE IN WRF:  ", len(readData)/5)
                for row in readData:
                    row = row.rstrip("\n")
                    if "16384" in row:
                        countNoBuddy += 1
                    if "-888888.000 -888888.000" in row:
                        myRow = row.split()
                        questionable.append(myRow)
                questDF = pd.DataFrame(questionable[:])
                shortDF = questDF.drop([2, 3, 12, 13, 16, 17], axis=1)
                numpy_matrix = shortDF.values

                for row2 in numpy_matrix:
                    if "-888888.000" in row2:
                        #print row2
                        missingData += 1
                print(shortfile + "   QC Flag because no buddy: ", countNoBuddy)
                print(shortfile + "   Data potentially missing or partial: ", missingData)

            ## ALL WRF/WPS TEXT FILES
            elif "rsl." in shortfile or ".out" in shortfile or ".log" in shortfile:
                if "namelist.output" in shortfile:
                    continue
                #if "rsl.out." in shortfile and "0000" not in shortfile:
                #    continue
                infile = open(file, 'r')
                readData = infile.readlines()

                okay_string = "traj_opt is zero, but num_traj is not zero; setting num_traj to zero"

                for row in readData:
                    if "ERROR" in row.upper():
                        if okay_string in row:
                            continue
                        print("CHECK "+shortfile+" :  ", row.strip())
                        num_errors += 1
                    if "WARNING" in row.upper():
                        if okay_string in row:
                            continue
                        print("CHECK "+shortfile+" :  ", row.strip())
                        num_warnings += 1

                    if "TBOUND" in row.upper():
                        if okay_string in row:
                            continue
                        print("CHECK "+shortfile+" :  ", row.strip())
                        num_tbounds += 1
                    if "EXCEEDED CFL"  in row.upper():
                        if okay_string in row:
                            continue
                        print("CHECK "+shortfile+" :  ", row.strip())
                        num_cfl += 1
                        # SHOULD BE CFL????
                    if "SUCCESS COMPLETE WRF" in row and "rsl.out.0000" in shortfile:
                        print("WRF RUN ON  " + date + "  FOR TYPE: " + type1 + " WAS SUCCESSFUL")
        print("Errors: ", num_errors)
        print("Warnings: ", num_warnings)
        print("TBOUND: ", num_tbounds)
        print("EXCEEDED CFL: ", num_cfl)
        print()
        print("-------------------------END OF FILE---------------------------")
        print()
        print()
        print()
