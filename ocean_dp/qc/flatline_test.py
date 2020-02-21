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

import re
from datetime import datetime, timedelta
from netCDF4 import num2date, date2num
from netCDF4 import stringtochar
import numpy.ma as ma
import sys
from netCDF4 import Dataset
import numpy as np
import argparse
import glob
import pytz
import os

def flatline_test(target_files,target_vars_in=[],window=3,flag=3):
    
    # If files aren't specified, take all the IMOS.nc files in the current folder
    if not target_files:
        
        target_files = glob.glob('IMOS*.nc')
    
    # Loop through each files in target_files
    for current_file in target_files:
        
        # Print each filename
        print("input file %s" % current_file)
        
        # Extract netcdf data into nc
        nc = Dataset(current_file, mode="a")
        
        # Extract time
        ncTime = nc.get_variables_by_attributes(standard_name='time')
    
        # If target_vars aren't user specified, set it to all the variables of 
        # the current_file, removing unwanted variables
        if target_vars_in == []:
            
            target_vars = list(nc.variables.keys())
            
            # Remove TIME
            target_vars.remove('TIME')
            
            # Remove any quality_control variables
            qc_vars = [s for s in target_vars if 'quality_control' in s]
            
            target_vars = [s for s in target_vars if s not in qc_vars]
                            
            # Remove any variables of single length
            single_vars = [s for s in target_vars if nc.variables[s].size==1]
            
            target_vars = [s for s in target_vars if s not in single_vars]
            
            print('target_vars are '+' '.join(target_vars))
            
        else:
            target_vars = target_vars_in
            
        # For each variable, extract the data 
        for current_var in target_vars:
            
            var_data = np.array(nc.variables[current_var])
            
            print('checking '+current_var)
            
            # Step through the data, one element at a time, using the window
            for i in range(0,(len(var_data)-window+1)):
                
                # This is true if 'window' elements in a row are equal
                if len(set(var_data[i:(i+window)])) == 1:
                    
                    # set corresponding QC value to...
                    nc.variables[current_var+'_quality_control'][i:(i+window)] = flag
                   
        nc.history += ' ' + datetime.utcnow().strftime("%Y%m%d:") + 'flatline_test performed, flatlines of '+str(window)+' consecutive values or more were flagged with '+str(flag)            
                    
        nc.close()
    
            
            
            
            
    
    
    
    