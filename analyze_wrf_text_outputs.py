#!/usr/bin/env python3
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

            
#%% IMPORTS
import pandas as pd   # Numpy doesn't need an excuse to be used
import glob
import os

# =============================================================================

### NAMING STRUCTURE THAT POINTS TO THE DIRECTORY or DIRECTORIES
dates = ["M-D-YYYY", "M-D-YYYY","M-D-YYYY"]
independent_variables = ["VAR1","VAR2","VAR3","VAR4"] # DATA ASSIMILATION TYPES

#models = ["WRF","COAWST"]

model_data_dir = os.path.abspath('../Model_Outputs/')
for date in dates:
    #for model in models
    for type1 in independent_variables:
        mydir = model_data_dir+'/CaseStudy_' + date + '/'+type1 +'_' + date.replace('-','_') + '/'
        
        
# =============================================================================
        ### ABOVE: POINT TO THE DIRECTORY... 
        print ("----------------------START OF Folder--------------------------")
        print (mydir)
        smallSize= len(mydir)
        for file in glob.glob(mydir+'*'):
            shortfile = file[smallSize:]
            
            ## OBSGRID TEXT FILES   
            if "obsgrid" in shortfile:
                infile = open(file,'rU')
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
                print (shortfile)
                for row in readData:
                    row = row.rstrip("\n")
                    if "BUDDY" in row:
                        buddyCount +=1
                        if buddyCount > 9:
                            countQC +=1
                            #print date, "\t",  type1,"\t", buddyCount - 9, "Buddy Counts"
                    if "ERRMX" in row:
                        countQC +=1
                        errmxCount +=1
                        #print date, "\t",  type1,"\t", errmxCount , "ERRMX Counts"
                    
                    if "Number of observations successfully ingested:" in row:
                        tmp = row.split(":")[1]
                        valINGEST = int(tmp.rstrip("."))
                        countIngested += valINGEST
                        #print "Ingested:  ",valINGEST, "  . Total:  ", countIngested
                        
                    if "Number of empty observations discarded:" in row:
                        tmp =row.split(":")[1]
                        numEmpty =  int(tmp.rstrip("."))
                        if numEmpty != 0:
                            countEmpty += numEmpty
                            print ("EMPTY!!!:  ", numEmpty)
                            
                    if "Number of observations discarded outside of domain:" in row:
                        tmp =row.split(":")[1]
                        numDiscard = int(tmp.rstrip("."))
                        if numDiscard != 0:
                             countOutside += numDiscard
                             print ("Discarded outside the domain:  ", countOutside)

                    if "merged locations" in row: 
                        # Of the   100 observations reported,    80 of them are duplicates, leaving    20 merged locations
                        #print row
                        tmp =row.split("Of the")[1]
                        #print tmp
                        tmp2 = tmp.split(" observations reported,")
                        reported = tmp2[0]
                        #print reported
                        tmp3 = tmp2[1].split("of them are duplicates, leaving")
                        duplicates = tmp3[0]
                        #print tmp3
                        tmp4 = tmp3[1].split(" merged locations")
                        merged = tmp4[0]
                        
                        #print "reported:  " ,reported,  "  .duplicates:  ", duplicates, ".merged:  ", merged
                        #break
                        countReported += int(reported)
                        countDuplicates += int(duplicates)
                        countMerged += int(merged) 
                        
                print ("")
                print ("")      
                print ("Date:  " + date   + ".  Type:  " + type1)
                print ("Failed Quality Control:   ", countQC)
                print ("        MAX ERROR TEST:   ", errmxCount   )
                print ("        BUDDY TEST:       ", buddyCount - 9  )
                print ("Number of Observations Ingested:         ",countIngested)
                print ("Number of Observations Empty:            ",countEmpty)
                print ("Number of Observations Outside Domain:   ",countOutside)
                print ("")
                print ("Number of Observations Reported:     ",countReported)
                print ("Number of Observations Duplicates:   ",countDuplicates)
                print ("Number of Observations Merged:       ",countMerged)
                print ("AVAILABLE IN WRF:  ",countMerged)

                
                print ("")                    
                print ("")

                            
            ## OBSGRID DATA FILES   
            elif "OBS_DOMAIN" in shortfile:
                infile = open(file,'rU')
                readData = infile.readlines()
                questionable = []
                missingData = 0
                countNoBuddy = 0
                print ("AVAILABLE IN WRF:  ",  len(readData)/5)
                for row in readData:
                    row = row.rstrip("\n")
                    if "16384" in row:
                       countNoBuddy +=1
                       #print row
                    if "-888888.000 -888888.000" in row:
                        myRow = row.split()
                        questionable.append(myRow)
                questDF = pd.DataFrame(questionable[:])  
                shortDF = questDF.drop(questDF.columns[[2, 3, 12, 13,16, 17]], axis=1)
                #print shortDF
                #print len(questionable)
                #numpy_matrix = shortDF.as_matrix()
                numpy_matrix = shortDF.values

                for row2 in numpy_matrix:
                    if "-888888.000" in row2:
                        #print row2
                        missingData +=1
                print (shortfile + "   QC Flag because no buddy: " , countNoBuddy)
                print (shortfile + "   Data potentially missing or partial: ", missingData)
                
            ## ALL WRF/WPS TEXT FILES    
            elif "rsl.error.0000" in shortfile or ".out" in shortfile or ".log" in shortfile:
                infile = open(file,'rU')
                readData = infile.readlines()
                print (shortfile)
                for row in readData:
                    if "ERROR" in row or "error" in row or "Error" in row or "Warning" in row or "WARNING" in row:
                        print ("CHECK?:  ", row)
                    if "SUCCESS COMPLETE WRF" in row:
                        print ("WRF RUN ON  " + date + "  FOR TYPE: " + type1 + " WAS SUCCESSFUL")
                    
        print ("")                    
        print ("-------------------------END OF FILE---------------------------")             
        print ("")
        print ("")
        print ("")
