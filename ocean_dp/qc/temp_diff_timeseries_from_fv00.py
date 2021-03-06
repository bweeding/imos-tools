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

def last_four(entry):
    
    output = entry[-4::]
    
    return output


def sp_layout(num_in):
    
    sp_nums = np.array([1,2,4,6,9,12,16,20,25,30])
    
    sp_dict={1:[1,1],2:[2,1],4:[2,2],6:[3,2],9:[3,3],12:[4,3],16:[4,4],20:[5,4],25:[5,5],30:[6,5]}
    
    return sp_dict[sp_nums[np.where(num_in<=sp_nums)[0][0]]]



cmap = colors.ListedColormap(['blue','orange','red'])

boundaries = [0,20,30,2000]

norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)



deployments = []

for x in next(os.walk("/Users/tru050/Desktop/cloudstor/Shared/SOTS-Temp-Raw-Data"))[1]:
    
    if (('Pulse' in x) or ('SOFS' in x)):

        
        deployments.append(x)

deployments.sort(key=last_four)






for current_deployment in deployments:
    
    acceptable_files = []
    
    acceptable_depths = []
    
    print('current deployment is '+current_deployment)
    
    deployment_dtemp_dtime = np.array([])
    
    for root, dirs, files in os.walk("/Users/tru050/Desktop/cloudstor/Shared/SOTS-Temp-Raw-Data"):
    
        for fname in files:
            
            print('checking '+fname)
          
            if current_deployment in fname and fname.endswith('.nc') and 'FV00' in fname:
                
                print('opening '+fname)
                
                nc = Dataset(os.path.join(root,fname), mode = 'r')
            
                if 'TEMP' in nc.variables and np.array(nc.variables['TEMP'][:]).ndim == 1 and nc.variables['TIME'].getncattr('units') =='days since 1950-01-01 00:00:00 UTC':
                
                    acceptable_files.append(os.path.join(root,fname))
                    
                    acceptable_depths.append(nc.instrument_nominal_depth)
                    
                    print(fname+' accepted')
                
                nc.close()
                
    
    acceptable_files = [x for _,x in sorted(zip(acceptable_depths,acceptable_files))]            
                
                    
    fig, ax = plt.subplots(sp_layout(len(acceptable_files))[0],sp_layout(len(acceptable_files))[1],figsize=((12,8)),constrained_layout=True,sharex=True)

    ax=ax.flatten()
    
    fig.suptitle(current_deployment, fontsize=14)
    
                
    for fpath,f_idx in zip(acceptable_files, range(0,len(acceptable_files))):      
            
        nc = Dataset(fpath, mode = 'r') #mismatching files and folders?? looking for sofs7.5 file in pulse 7 folder!?!?
            
        time_var = nc.variables["TIME"]
        
        time = num2date(time_var[:], units=time_var.units, calendar=time_var.calendar)
    
        time_deploy = parser.parse(nc.time_deployment_start, ignoretz=True)
        
        time_recovery = parser.parse(nc.time_deployment_end, ignoretz=True)
        
        #print('using '+fname)
        
        temp_extract = np.array(nc.variables['TEMP'][:][(time > time_deploy) & (time < time_recovery)])
        
        # Calculate temperature changes
        nc_temp_diffs = np.diff(temp_extract)
        
        # Extract the time data
        nc_time = np.array(nc.variables['TIME'][:][(time > time_deploy) & (time < time_recovery)])
    
        # Convert from days to hours
        nc_time_hr = nc_time*24
        
        # Calculate time changes
        nc_time_hr_diffs = np.diff(nc_time_hr)
        
        # Calculate the rate of change of temperature wrt time
        nc_dtemp_dtime = np.divide(nc_temp_diffs,nc_time_hr_diffs)
        
        im=ax[f_idx].scatter(nc_time,temp_extract,s=0.2,c=np.concatenate((np.array([0]),np.abs(nc_dtemp_dtime))),cmap=cmap,norm=norm)
        
        im=ax[f_idx].scatter(nc_time[np.concatenate((np.array([0]),np.abs(nc_dtemp_dtime)))>20],temp_extract[np.concatenate((np.array([0]),np.abs(nc_dtemp_dtime)))>20],s=0.5,c=np.concatenate((np.array([0]),np.abs(nc_dtemp_dtime)))[np.concatenate((np.array([0]),np.abs(nc_dtemp_dtime)))>20],cmap=cmap,norm=norm)
        
        ax[f_idx].set_title(str(nc.instrument_nominal_depth)+'m',fontsize=10)
        
        # Add the results for this netcdf to the record for the deployment
        deployment_dtemp_dtime = np.concatenate((deployment_dtemp_dtime,nc_dtemp_dtime))
        
        nc.close()
        
        if f_idx==0:
            
            fig.colorbar(im)
            
    for f_idx in range(len(acceptable_files),len(ax)):       
            
        ax[f_idx].set_axis_off()


##############################################################################

fig, ax = plt.subplots(sp_layout(len(deployments))[0],sp_layout(len(deployments))[1],figsize=((12,8)),constrained_layout=True,sharex=False)

ax=ax.flatten()

for current_deployment,d_idx in zip(deployments,range(0,len(deployments))):
    
    acceptable_files = []
    
    acceptable_depths = []
    
    print('current deployment is '+current_deployment)
    
    deployment_dtemp_dtime = np.array([])
    
    for root, dirs, files in os.walk("/Users/tru050/Desktop/cloudstor/Shared/SOTS-Temp-Raw-Data"):
    
        for fname in files:
            
            print('checking '+fname)
          
            if current_deployment in fname and fname.endswith('.nc') and 'FV00' in fname:
                
                print('opening '+fname)
                
                nc = Dataset(os.path.join(root,fname), mode = 'r')
            
                if 'TEMP' in nc.variables and np.array(nc.variables['TEMP'][:]).ndim == 1 and nc.variables['TIME'].getncattr('units') =='days since 1950-01-01 00:00:00 UTC':
                
                    acceptable_files.append(os.path.join(root,fname))
                    
                    acceptable_depths.append(nc.instrument_nominal_depth)
                    
                    print(fname+' accepted')
                
                nc.close()
                
    
    acceptable_files = [x for _,x in sorted(zip(acceptable_depths,acceptable_files))]            
                    
                
    for fpath in acceptable_files:      
            
        nc = Dataset(fpath, mode = 'r') #mismatching files and folders?? looking for sofs7.5 file in pulse 7 folder!?!?
            
        time_var = nc.variables["TIME"]
        
        time = num2date(time_var[:], units=time_var.units, calendar=time_var.calendar)
    
        time_deploy = parser.parse(nc.time_deployment_start, ignoretz=True)
        
        time_recovery = parser.parse(nc.time_deployment_end, ignoretz=True)
        
        #print('using '+fname)
        
        temp_extract = np.array(nc.variables['TEMP'][:][(time > time_deploy) & (time < time_recovery)])
        
        # Calculate temperature changes
        nc_temp_diffs = np.diff(temp_extract)
        
        # Extract the time data
        nc_time = np.array(nc.variables['TIME'][:][(time > time_deploy) & (time < time_recovery)])
    
        # Convert from days to hours
        nc_time_hr = nc_time*24
        
        # Calculate time changes
        nc_time_hr_diffs = np.diff(nc_time_hr)
        
        # Calculate the rate of change of temperature wrt time
        nc_dtemp_dtime = np.divide(nc_temp_diffs,nc_time_hr_diffs)
        
        # Add the results for this netcdf to the record for the deployment
        deployment_dtemp_dtime = np.concatenate((deployment_dtemp_dtime,nc_dtemp_dtime))
        
        nc.close()
        
    ax[d_idx].hist(deployment_dtemp_dtime,21,log=True)
    
    ax[d_idx].set_title(current_deployment,fontsize=10)
        





















