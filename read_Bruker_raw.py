# -*- coding: utf-8 -*-
"""
Created on Sun Oct 19 18:40:31 2025
@author: eljac

This code is used to read Bruker RAW4 file format.
Used for XRR, XRD and RSM measurements from a Bruker D8 Discover tool.
The format of the binary file was interpreted from wojdyr/xylib/Bruker_raw.cpp,
and this file is licensed under GNU Lesser General Public License v2.1 accoridngly.
"""
import struct
import json
from math import cos, sin

class DataRange:
    def __init__(self):
        self.meta = dict()
        self.tt = None
        self.I = None
        
    def calculate_x(self):
        try:
            start = self.meta['START_ANGLE']
            step = self.meta['STEP_SIZE']
            self.tt = [round(start+i*step, 4) for i in range(self.meta['STEPS'])]
        except:
            raise KeyError("Start, step size and/or steps meta info not this data range!")


class RawFile:
    """Reader for Bruker raw data files (format version 4)."""
    def __init__(self, raw_file_path):
        assert os.path.exists(raw_file_path), f"Passed RawFile '{raw_file}' does not exist"
        assert raw_file_path[-4:] == ".raw", f"Passed RawFile '{raw_file}' is not .raw"
        self.raw_file = raw_file_path
        # Open file as an io buffer and leave open to perform operations
        self.f = open(raw_file_path, "rb")
        # Get all the data from the file that we want and store it
        self.length = len(self.f.read())
        self.offset = 0
        self.meta = dict()
        self.ranges = []
        self.f.seek(0)
        try:
            self.load_raw4()
            pass
        finally:
            # After saving all the data, close the file, even if error
            self.f.close()
            self.f = None

    # Private methods (preceded by "__") to be used by load_raw4
    def __skip(self, length: int):
        """Skip forward a specified number of bytes in binary file."""
        self.offset += length
        self.f.seek(self.offset)

    def __read_string(self, length: int) -> str:
        """Read a fixed-length string from binary file."""
        data = self.f.read(length)
        self.offset += length
        self.f.seek(self.offset)
        # Remove null bytes and decode
        return data.strip(b'\x00').decode('utf-8', errors='ignore')

    def __read_uint32_le(self) -> int:
        """Read a 32-bit unsigned integer (little-endian)."""
        data = self.f.read(4)
        self.offset += 4
        self.f.seek(self.offset)
        if len(data) < 4:
            raise EOFError("Unexpected end of file")
        return struct.unpack('<I', data)[0]

    def __read_float_le(self) -> float:
        """Read a 32-bit float (little-endian)."""
        data = self.f.read(4)
        self.offset += 4
        self.f.seek(self.offset)
        return struct.unpack('<f', data)[0]

    def __read_double_le(self) -> float:
        """Read a 64-bit double (little-endian)."""
        data = self.f.read(8)
        self.offset += 8
        self.f.seek(self.offset)
        return struct.unpack('<d', data)[0]
    

    def load_raw4(self):
        """Parse the .raw file and extract the x and y values into stored data ranges"""
        assert self.f.closed == False, "File buffer has been closed, call __init__ to re-read data"
        # ---------- HEADER ----------
        self.meta['version'] = self.__read_string(4)
        self.__skip(8)
        self.meta["MEASURE_DATE"] = self.__read_string(12)  # address 12
        self.meta["MEASURE_TIME"] = self.__read_string(10)  # address 24
        self.__skip(27)
        # Offset = 61 = end of header
        
        # ---------- HEADER ----------
        # Loop through the global (scan-independent) metadata
        # seg_types are 10 (var info), 30 (hardware info), 60 (drive info). 160 is data, after meta
        drive_num = 0
        while True:
            segment_type = self.__read_uint32_le()  # offset = 65
            if segment_type == 0 or segment_type == 160:
                break  # Start of data range(s) so end of global metadata
            segment_len = self.__read_uint32_le()  # offset = 69
            assert segment_len >= 8, f"Invalid segment length: {segment_len}"
            #print(f"seg_type = {segment_type}, seg_len = {segment_len}")
    
            if segment_type == 5:  # HRXRD alignment info
                # Substrate vectors (32 bytes)
                self.__skip(8)
                self.meta["SUBSTRATE NORM"] = self.__read_string(12)
                self.meta["SUBSTRATE AZIMUTH"] = self.__read_string(12)
                # Skip non-understood bytes
                self.__skip(40)
                # Sample vectors (24 bytes)
                self.meta["SAMPLE NORMAL"] = self.__read_string(12)
                self.meta["SAMPLE AZIMUTH"] = self.__read_string(12)
                # Skip the rest of the bytes - don't know if they're significant
                self.__skip(segment_len - (28 + 44 + 24 + 8))
                
            elif segment_type == 10:  # var info
                assert segment_len >= 36, "var_info segment too short"
                self.__skip(4)  # offset +8 before
                tag_name = self.__read_string(24)  # offset +12
                self.meta[tag_name] = self.__read_string(segment_len-36)  # offset +36

            elif segment_type == 30:  # hardware info
                assert segment_len >= 120, "HardwareConfiguration segment too short"
                self.__skip(64)  # offset +8 before
                self.meta["ALPHA_AVERAGE"] = self.__read_double_le()  # offset +72
                self.meta["ALPHA1"] = self.__read_double_le()  # offset +80
                self.meta["ALPHA2"] = self.__read_double_le()  # offset +88
                self.meta["BETA"] = self.__read_double_le()  # offset +96
                self.meta["ALPHA_RATIO"] = self.__read_double_le()  # offset +104
                self.__skip(4)  # offset +112
                self.meta["ANODE_MATERIAL"] = self.__read_string(4)  # offset +116
                self.__skip(segment_len-120)  # offset +120

            elif segment_type == 60:  # drive info
                assert segment_len >= 76, "DriveAlignment segment too short"
                self.meta[f"DRIVE{drive_num}_ALIGN_FLAG"] = self.__read_uint32_le()  # offset +8 before
                self.meta[f"DRIVE{drive_num}_NAME"] = self.__read_string(24)  # offset +12
                self.__skip(32)  # offset +36
                self.meta[f"DRIVE{drive_num}_DELTA"] = self.__read_double_le()  # offset +68
                self.__skip(segment_len-76)  # offset +76
                drive_num += 1

            else:  # __skip unknown segment types
                self.__skip(segment_len-8)

        # Now process ranges
        range_num = -1
        while segment_type == 0 or segment_type == 160:
            range_num += 1
            d_range = DataRange()
            # Primary range header
            self.__skip(28)  # offset +4 before
            d_range.meta["SCAN_TYPE"] = self.__read_string(24)  # offset +32
            self.__skip(16)  # offset +56
            d_range.meta["START_ANGLE"] = self.__read_double_le()  # offset +72
            d_range.meta["STEP_SIZE"] = self.__read_double_le()  # offset +80
            d_range.meta["STEPS"] = self.__read_uint32_le()  # offset +88
            d_range.meta["TIME_PER_STEP"] = self.__read_float_le()  # offset +92
            self.__skip(4)  # offset +96
            d_range.meta["GENERATOR_VOLTAGE"] = self.__read_float_le()  # +100
            d_range.meta["GENERATOR_CURRENT"] = self.__read_float_le()  # +104
            self.__skip(4)  # offset +108
            d_range.meta["USED_LAMBDA"] = self.__read_double_le()  # offset +112
            self.__skip(16)  # offset +120
            datum_size = self.__read_uint32_le()  # offset +136
            hdr_size = self.__read_uint32_le()  # offset +140
            self.__skip(16)  # offset +144

            # Process Locked Coupled and Unlocked Coupled scan types
            if d_range.meta["SCAN_TYPE"] in ["Locked Coupled", "Unlocked Coupled", "PSD Fix Scan"]:
                # Process remaining block headers
                while hdr_size > 0:
                    seg_type = self.__read_uint32_le()  # offset +0
                    seg_len = self.__read_uint32_le()  # offset +4
                    assert seg_len >= 8, f"Invalid segment length: {seg_len}"

                    if seg_type == 50:
                        assert seg_len >= 64, "Segment type 50 too short"
                        self.__skip(4)  # offset +8
                        seg_name = self.__read_string(24)  # offset +12

                        if seg_name in ["Theta", "2Theta", "Divergence Slit", "Antiscattering Slit", "Phi", "Chi", "X-Drive", "Y-Drive", "Z-Drive"]:
                            self.__skip(20)  # offset +36
                            seg_value = self.__read_double_le()  # +56
                            d_range.meta[f"{seg_name.upper().replace('-', '_')}"] = seg_value
                            self.__skip(seg_len-64)
                        else:
                            self.__skip(seg_len-36)
                            
                    else:
                        self.__skip(seg_len-8)

                    hdr_size -= seg_len

                # Compute x values and read y values
                assert datum_size == 4, f"Unexpected datum size: {datum_size}"
                d_range.calculate_x()
                d_range.I = []
                for i in range(d_range.meta['STEPS']):
                    d_range.I.append(self.__read_float_le() / d_range.meta["TIME_PER_STEP"])
                assert len(d_range.tt) == len(d_range.I), f"x({len(d_range.tt)}) and y({len(d_range.I)}) vector lengths do not match!"

            else:  # __skip unknown scan types
                d_range.meta["UNKNOWN_RANGE_SCAN_TYPE"] = "true"
                self.__skip(hdr_size)
                self.__skip(datum_size * d_range.meta['STEPS'])

            self.ranges.append(d_range)

            # Now we are at the file end or start of next range if multirange scan
            try:
                if self.offset >= self.length:
                    raise EOFError("Current offset is larger than file length!")
                seg_type = self.__read_uint32_le()
            except EOFError:
                break


    def get_data(self, x_unit: str = "reciprocal", y_unit: str = "CPS"):
        """
        Return the data for the measurement loaded from the raw file.
        x (angular or reciprocal units) and intensity for XRR / XRD / RSM (2D) files.

        Parameters
        ----------
        x_unit : str, optional
            Units to return for x, default "reciprocal" or "deg".
        y_unit : str, optional
            Units for the intensity, default "cps" or "counts".
        """
        rad, dwell, lam = 0.01745329252, self.ranges[0].meta["TIME_PER_STEP"], self.meta['ALPHA_AVERAGE']
        if len(self.ranges) == 1:
            tt = self.ranges[0].tt
            qz = [20*sin(i/2 * rad) / lam for i in tt]  # in 1/nm
            I = self.ranges[0].I if y_unit=="CPS" else [i*dwell for i in self.ranges[0].I]
            return (tt if x_unit=="deg" else qz), I
        else:
            tth = [r.tt for r in self.ranges]  # All 2Theta ranges
            n, m = len(tth), len(tth[0])  # length of each range
            w = [[r.meta['THETA'] for i in range(m)] for r in self.ranges]  # All theta values for each range
            Is = [[i*(1 if y_unit=="CPS" else dwell) for i in r.I] for r in self.ranges]
            assert len(tth) == len(w) == len(Is) and len(tth[0]) == len(w[0]) == len(Is[0]), "Shape mismatch in theta, 2theta and intensity"
            if x_unit == "deg":
                return tth, w, Is
            
            qx = [[10*(cos((tth[i][j]-w[i][j])*rad) - cos(w[i][j]*rad))/lam for j in range(m)] for i in range(n)]
            qz = [[10*(sin((tth[i][j]-w[i][j])*rad) + sin(w[i][j]*rad))/lam for j in range(m)] for i in range(n)]
            
            return qx, qz, Is


    def get_json(self):
        return json.dumps({
            "offset":self.offset,
            "length":self.length,
            "meta":self.meta,
            "ranges":[vars(r) for r in self.ranges]
            }, indent=4)
    
    
    def save_asc(self, x_unit: str = "deg", y_unit: str = "CPS"):
        """
        Save the data from the raw file to an asc file - ignore header.

        Parameters
        ----------
        x_unit : str, optional
            Units to return for x, default "deg" or "reciprocal".
        y_unit : str, optional
            Units for the intensity, default "CPS" or "counts".
        """
        asc_file = self.raw_file.replace(".raw",".asc")
        if os.path.exists(asc_file):
            print(f"{asc_file} already exists!")
            return
        print(f".\nExtracting x, y(, z) data from:\n\t{self.raw_file} -\n-> and saving to .asc format\n.")
        
        tup = self.get_data(x_unit, y_unit)
        if len(tup) == 2:
            print(f"1D measurement: x and y data, ({len(tup[0])}, 2).")
            hdr = "2Theta_deg  Counts"
            try:
                import numpy as np
                print("saving 1D data - numpy")
                np.savetxt(asc_file, np.stack(tup).T, fmt="%-14.5f%-10.5e", header=hdr)
            except ImportError:
                print("saving 1D data - manual python")
                with open(asc_file, "w+") as f:
                    f.write("#" + hdr + "\n")
                    xs,ys = tup
                    for x,y in zip(xs,ys):
                        f.write(f"{x:<13.5f}{y:<10.5e}\n")            
            
        elif len(tup) == 3:
            hdr = "2Theta_deg  omega_deg  Counts"
            try:
                import numpy as np
                print("saving 2D data - numpy")
                new_tup = tuple([np.array(t).flatten() for t in tup])
                print(f"2D measurement: x, y and z data, (({len(tup[0])}, {len(tup[0][0])}), 3)->({len(new_tup[0])}, 3).")
                np.savetxt(asc_file, np.stack(new_tup).T, fmt="%-13.5f%-11.5f%-10.5e", header=hdr)
            except ImportError:
                print("saving 2D data - manual python")
                with open(asc_file, "w+") as f:
                    f.write("#" + hdr + "\n")
                    xs,ys,zs = tup
                    for i in range(len(xs)):
                        for j in range(len(xs[0])):
                            f.write(f"{xs[i][j]:<13.5f}{ys[i][j]:<11.5f}{zs[i][j]:<10.5e}\n") 
            



#%% Code for right-click open-with execution, via .bat file
if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) <= 1:
        print("No argument passed")
    else:
        for raw_file in sys.argv[1:]:
            if not os.path.exists(raw_file):
                print(f"Passed RawFile '{raw_file}' does not exist")
                continue
            if not raw_file[-4:] == ".raw":
                print(f"Passed RawFile '{raw_file}' is not .raw")
                continue
            
            RawFile(raw_file).save_asc("deg", "counts")
                
        print("---------- Done! ----------")



# Type the following in the bash script
# """
# @echo off
# PATH_TO_PYTHON PATH_TO_PYTHON_SCRIPT %*
# pause
# """


# The following admin powershell code should add the bash script to the right-click context menu
# """
# $path = 'Registry::HKEY_CLASSES_ROOT\Directory\Background\shell\convert_raw2asc\command'
# $path_to_bash_script = PATH_TO_BASH_SCRIPT
# New-Item -Path $path -force
# Set-ItemProperty -Path $path -Name "(default)" -Value $path_to_bash_script
# """



