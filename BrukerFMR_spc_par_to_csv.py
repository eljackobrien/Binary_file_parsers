# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 00:06:13 2024

@author: eljac

File format known from "A Brief Guide to SPC File Format" by Thermo Galactic, 2001
"""
# Imports
import os
import numpy as np
from BrukerFMR_par_import import get_scan_params


def create_csv(spc_file, silent=True):
    data = np.fromfile(spc_file, dtype="<f4")
    pars = get_scan_params(spc_file, silent=silent)

    # If the second dimension is an angular scan, get the angles
    angle = pars.gonio

    # Microwave bridge conditions
    freq, attenuation = pars.freq, pars.attenuation

    # Field information
    l = pars.x_res
    B_0, B_w = pars.field_centre, pars.field_sweep_width
    B = np.linspace(B_0 - B_w/2, B_0 + B_w/2, l) * 0.1  # mT

    if pars.y_num > 1:
        n = pars.y_num

        # Split the data into the sub-files
        signals = data.reshape(n,l)

        # If the second dimension is an angular scan, get the angles
        ang_step = pars.gonio_step
        if pars.y_scan_type == "angle-sweep":
            angles = np.arange(angle, angle + n*ang_step, ang_step) % 360

            for angle_i, y in zip(angles, signals):
                path = '/'.join( spc_file.replace("\\","/").split('/')[:-1] )
                csv_file = path + f"/{angle_i:.0f}deg_from_2D" + ".csv"
                header = "Field (mT), Resonance Signal"
                if not os.path.exists(csv_file):
                    print(csv_file)
                    np.savetxt(csv_file, np.vstack((B,y)).T, fmt='%12.4f,\t%14.3f', header=header)


        else:
            print("Cannot interpret 2D scans where second dimension is not angle yet")
            print("Skipping file")
            return None

    # 1D scan
    else:
        csv_file = f"{spc_file[:-4]}" + ".csv"
        header = "Field (mT), Resonance Signal"
        if not os.path.exists(csv_file):
            print(csv_file)
            np.savetxt(csv_file, np.vstack((B,data)).T, fmt='%12.4f,\t%14.3f', header=header)





if __name__ in "__main__":
    from glob import glob
    from print_clr import print_clr
    
    # 1D test files
    file = "../Data/test/test_spc_converter/10.spc"
    create_csv(file)
    
    print()
    # 2D test files - first file is 2D, others are 1D
    file = "../Data/test/test_spc_converter/0_to_200_20step.spc"
    create_csv(file)
    
    for file in glob("../Data/**/*spc", recursive=True):
        try:
            create_csv(file)
        except Exception as e:
            print_clr(f"{file} Failed:\n{e}", (255,0,0), end='\n')
