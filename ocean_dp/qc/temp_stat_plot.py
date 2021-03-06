# Copyright (C) 2020 Ben Weeding
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import numpy.ma as ma
import sys
from netCDF4 import Dataset, num2date
from dateutil import parser
import numpy as np
import argparse
import glob
import pytz
import os
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.ticker import PercentFormatter
from sigfig import round
import pandas as pd

import warnings
import scipy.stats as st
import statsmodels as sm
import matplotlib


############################# Data extraction ################################

# creates an empty array to store the names of the SOTS deployments
deployments = []

checked_files = []

processed_files = []

# loops through all the folders and files contained in the folder
for x in os.listdir("/Users/tru050/Desktop/cloudstor/Shared/SOTS-Temp-Raw-Data"):
    
    # if the folder/file name contains 'Pulse' or 'SOFS' and doesn't contain '.', append it to deployments
    if (('Pulse' in x) or ('SOFS' in x)) and ('.p' not in x):
        
        deployments.append(x)
    
# create a dataframe to store extract information
sots_temp_ensemble = pd.DataFrame(columns = ["dTemp/dtime","dTemp/dSample","QC","Nominal depth","Deployment"])

# loops through all files in the directory
for root, dirs, files in os.walk("/Users/tru050/Desktop/cloudstor/Shared/SOTS-Temp-Raw-Data"):
    
    for fname in files:
        
        # append the filename to the list of checked files
        checked_files.append(fname)
        
        # for each netcdf file labelled as FV01 and containing a deployment in its name
        if fname.endswith('.nc') and 'FV01' in fname and any(ele in fname for ele in deployments):
        
            # print the filename
            print(fname)  
            
            # open the file
            nc = Dataset(os.path.join(root,fname), mode = 'a')
            
            # check file contains temperature data
            if 'TEMP' in list(nc.variables):
            
                # check that the in_out_water test has been run on the file, if not run in_out_water code
                if not 'TEMP_quality_control_io' in list(nc.variables):
                
                    # run in_out_water script - uncommented at this point as just copied and pasted
                    var_name = 'TEMP'
                    nc_vars = nc.variables
                    to_add = []
                    if var_name:
                        to_add.append(var_name)
                    else:
                        for v in nc_vars:
                            #print (vars[v].dimensions)
                            if v != 'TIME':
                                to_add.append(v)
                
                    time_var = nc_vars["TIME"]
                    time = num2date(time_var[:], units=time_var.units, calendar=time_var.calendar)
                
                    time_deploy = parser.parse(nc.time_deployment_start, ignoretz=True)
                    time_recovery = parser.parse(nc.time_deployment_end, ignoretz=True)
                
                    print('deployment time', time_deploy)
                
                    print(to_add)
                
                    # create a mask for the time range
                    mask = (time <= time_deploy) | (time >= time_recovery)
                
                    for v in to_add:
                        if "TIME" in nc_vars[v].dimensions:
                            if v.endswith("_quality_control"):
                                print("QC time dim ", v)
                
                                ncVarOut = nc_vars[v]
                                ncVarOut[mask] = 7
                            else:
                                # create a qc variable just for this test flags
                                if v + "_quality_control_io" in nc.variables:
                                    ncVarOut = nc.variables[v + "_quality_control_io"]
                                else:
                                    ncVarOut = nc.createVariable(v + "_quality_control_io", "i1", nc_vars[v].dimensions, fill_value=99, zlib=True)  # fill_value=0 otherwise defaults to max
                                ncVarOut[:] = np.zeros(nc_vars[v].shape)
                                ncVarOut.long_name = "quality flag for " + v
                                ncVarOut.flag_values = np.array([0, 1, 2, 3, 4, 6, 7, 9], dtype=np.int8)
                                ncVarOut.flag_meanings = 'unknown good_data probably_good_data probably_bad_data bad_data not_deployed interpolated missing_value'
                
                                nc_vars[v].ancillary_variables = nc_vars[v].ancillary_variables + " " + v + "_quality_control_io"
                                ncVarOut[mask] = 7
                        
                        nc.variables[v + "_quality_control"][:] = np.maximum(nc.variables[v + "_quality_control_io"][:],nc.variables[v + "_quality_control"][:])
                
                    nc.file_version = "Level 1 - Quality Controlled Data"
                
                
                
                # check that the file has a single dimension temperature vector, and that the time format is correct
                if np.array(nc.variables['TEMP'][:]).ndim == 1 and nc.variables['TIME'].getncattr('units') =='days since 1950-01-01 00:00:00 UTC':
                    
                    # calculate temperature changes for in water data
                    nc_temp_diffs = np.diff(np.array(nc.variables['TEMP'][np.array(nc.variables['TEMP_quality_control'][:])!=7]))
                
                    # extract the time data
                    nc_time = np.array(nc.variables['TIME'][np.array(nc.variables['TEMP_quality_control'][:])!=7])
            
                    # Convert from days to hours
                    nc_time_hr = nc_time*24
                    
                    # Calculate time changes in hours
                    nc_time_hr_diffs = np.diff(nc_time_hr)
                    
                    # calculate the rate of change of temperature wrt time (degrees °C per hour)
                    nc_dtemp_dtime = np.divide(nc_temp_diffs,nc_time_hr_diffs)
                    
                    
                    
                    # extract temp_qc data
                    nc_temp_qc = np.array(nc.variables['TEMP_quality_control'][np.array(nc.variables['TEMP_quality_control'][:])!=7])
                    
                    # calculate qc values for each nc_dtemp_dtime by taking the maximum of the qc values of the two contributing temps
                    nc_dtemp_dtime_qc = pd.Series(nc_temp_qc).rolling(2).max().dropna().to_numpy()
                    
                    
                    
                    # extract sensor nominal depth
                    nc_nom_depth = np.array(nc.variables['NOMINAL_DEPTH'])
                    
                    # create a vector the same size as nc_dtemp_dtime with the nominal depth
                    nc_nom_depth_vector = np.repeat(nc_nom_depth,len(nc_dtemp_dtime))
                    
                    
                    
                    # extract deployment name
                    nc_deployment = nc.deployment_code
                    
                    # create a list the same size as nc_dtemp_dtime with the deployment name
                    nc_deployment_list = [nc_deployment] * len(nc_dtemp_dtime)
                    
                    
                    
                    # combine information into an length x 4 dataframe
                    nc_temp_ensemble = pd.DataFrame({"dTemp/dtime":nc_dtemp_dtime,"dTemp/dSample":nc_temp_diffs,"QC":nc_dtemp_dtime_qc,"Nominal depth":nc_nom_depth_vector,"Deployment":nc_deployment_list})
                    
                    # append the current netcdf's dataframe to the sots_temp_ensemble
                    sots_temp_ensemble = sots_temp_ensemble.append(nc_temp_ensemble)
                    
                    # append the filename to the list of processed files
                    processed_files.append(fname)
                    
                    
            nc.close()
                    
                    
############################# Data processing ################################
            
# creates a new dataframe containing only data with QC < 3
sots_temp_ensemble_qc210 = sots_temp_ensemble[sots_temp_ensemble["QC"]<3]

# calculates overall standard deviation
std_time_total = np.std(sots_temp_ensemble_qc210["dTemp/dtime"])




# creates an emply list to store data deployment by deployment
std_by_deployment_data = []

# creates a dict of deployment names and standard deviations
for i in sots_temp_ensemble_qc210.Deployment.unique():
    std_by_deployment_data.append(
        {
            'Deployment': i,
            'STD time': np.std(sots_temp_ensemble_qc210["dTemp/dtime"][sots_temp_ensemble_qc210["Deployment"]==i]),
            'STD sample': np.std(sots_temp_ensemble_qc210["dTemp/dSample"][sots_temp_ensemble_qc210["Deployment"]==i])
        }
    )

# creates a Dataframe from the dict
std_by_deployment = pd.DataFrame(std_by_deployment_data)





# =============================================================================
# std_by_depth: this function takes two compulsary arguments (top: the shallowest 
# depth(m)), bottom: the deepest depth(m)) and one option argument (deployment_in: 
# the deployment from which data will be taken). The function will return the standard
# deviation of the d(Temp)/d(Time) data from sensors with nominal depths at and 
# between the two depths, and from only the deployment_in if specified.
#
# sample call: std_by_depth(500,10000,'SOFS-7.5-2018')
#
# this will give the std of all d(Temp)/d(Time) data from SOFS-7.5-2018 from 
# sensors with 500m <= nominal depth <= 10000m
# =============================================================================

def std_by_depth_temp(top,bottom,deployment_in=None,rate='time'):
    
    selection = ''
    
    if rate == 'time':
        
        selection = "dTemp/dtime"
        
    elif rate == 'sample':
        
        selection = "dTemp/dSample"
        
    else:
        
        return "incorrect rate specification"
    
    
    
    # if user incorrectly inputs depths, swap them and run the code
    if top > bottom:
        
        top, bottom = bottom, top
    
    if deployment_in == None:
    
        # subsamples sots_temp_ensemble_qc210 based on depth
        target_ensemble = sots_temp_ensemble_qc210[(sots_temp_ensemble_qc210["Nominal depth"]>=top) & (sots_temp_ensemble_qc210["Nominal depth"]<=bottom)]
        
    elif isinstance(deployment_in, list):
        
        # subsamples sots_temp_ensemble_qc210 based on depth
        target_ensemble = sots_temp_ensemble_qc210[(sots_temp_ensemble_qc210["Nominal depth"]>=top) & (sots_temp_ensemble_qc210["Nominal depth"]<=bottom) & (sots_temp_ensemble_qc210.Deployment.isin(deployment_in))]
        
        
    else:   
    
        # subsamples sots_temp_ensemble_qc210 based on depth
        target_ensemble = sots_temp_ensemble_qc210[(sots_temp_ensemble_qc210["Nominal depth"]>=top) & (sots_temp_ensemble_qc210["Nominal depth"]<=bottom) & (sots_temp_ensemble_qc210["Deployment"]==deployment_in)]
    
    # if not data is available with the given choices, end the function
    if len(target_ensemble)==0:
        
        return 'No data available for those choices'
        
        
    # calculates the mean of the subsample
    target_mean = np.mean(target_ensemble[selection])
            
    # calculates the standard deviation of the subsample
    target_std = np.std(target_ensemble[selection])
        
    # sets line thickness for plot
    line_thick = 1
    
    # creates axes for histogram
    ax_hist=plt.axes()
    
    # plots a histogram of the data selected
    target_ensemble.hist(column=selection,bins=100,log=True,ax=ax_hist)
    
    # draws lines at the mean +- 3 STD on the histogram
    ax_hist.axvline(x=target_mean+3*target_std,color='r',linewidth=line_thick) 

    ax_hist.axvline(x=target_mean-3*target_std,color='r',linewidth=line_thick) 
    
    # sets the x label
    if rate == 'time':
        
         ax_hist.set_xlabel('°C/hr')
        
    elif rate == 'sample':
        
        ax_hist.set_xlabel('°C/sample')
    
    
    label_coords = (0.70, 0.99)
    label_method = 'axes fraction' 
    
    anno = 'mean = '+str(round(float(target_mean),sigfigs=3))
    
    anno += '\n3 STD = ' + str(round(float(3*target_std),sigfigs=3))
    
    anno += '\nno. samples = ' + str(len(target_ensemble))
    
    anno += '\n'+str(top)+'m <= depth <= '+str(bottom)+'m'
    
    if deployment_in == None:
        
        anno += '\nall available data'
        
    elif isinstance(deployment_in, list):
        
        anno += '\n'
        
        anno += '\n'.join(deployment_in)
        
    else:
        
        anno += '\n'+deployment_in
            
    ax_hist.annotate(anno,xy=label_coords, xycoords=label_method,fontsize=8,va = "top", ha="left")
    
    # returns the standard deviation of the subsample
    return target_std
    

























            
            
            