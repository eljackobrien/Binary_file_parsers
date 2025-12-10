# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 00:06:13 2024

@author: eljac
"""
# Class to store all the (relevant) scan parameters, returned by the function
class scan_params():
    def __init__(self, text, silent=True):
        self.file_length = int(text.split("ANZ ")[-1].split("\n")[0].strip())  # = x_res*y_scans
        self.y_min = float(text.split("MIN ")[-1].split("\n")[0].strip())  # ?
        self.y_max = float(text.split("MAX ")[-1].split("\n")[0].strip())  # ?
        #self.JSS = int(text.split("JSS ")[-1].split("\n")[0].strip())  # ?

        # Below is stuff for 2D scans, ignore for 1D
        try:
            self.x_len = int(text.split("SSX ")[-1].split("\n")[0].strip())
            self.y_num = int(text.split("SSY ")[-1].split("\n")[0].strip())
            self.x0 = float(text.split("XXLB ")[-1].split("\n")[0].strip())
            self.x_range = float(text.split("XXWI ")[-1].split("\n")[0].strip())
            self.y0 = float(text.split("XYLB ")[-1].split("\n")[0].strip())
            self.y_range = float(text.split("XYWI ")[-1].split("\n")[0].strip())
            self.x_unit = text.split("XXUN ")[-1].split("\n")[0].strip()
            self.y_unit = text.split("XYUN ")[-1].split("\n")[0].strip()
        except:
            self.y_num = 1
            pass

        self.system = text.split("JON ")[-1].split("\n")[0].strip()
        self.date = text.split("JDA ")[-1].split("\n")[0].strip()
        self.time = text.split("JTM ")[-1].split("\n")[0].strip()
        self.calibration_file = text.split("JRE ")[-1].split("\n")[0].strip()

        self.x_scan_type = text.split("JEX ")[-1].split("\n")[0].strip()
        try:
            self.y_scan_type = text.split("JEY ")[-1].split("\n")[0].strip()
            self.x_res = self.x_len
            if not silent: print("2D scan")
        except:
            self.y_scan_type = None
            self.x_res = self.file_length
            if not silent: print("1D scan")

        #self.JSD = int(text.split("JSD ")[-1].split("\n")[0].strip())  # ?
        #self.CCF = int(text.split("CCF ")[-1].split("\n")[0].strip())  # ?

        self.field_centre = float(text.split("HCF ")[-1].split("\n")[0].strip())
        self.field_sweep_width = float(text.split("HSW ")[-1].split("\n")[0].strip())

        self.conv_time = float(text.split("RCT ")[-1].split("\n")[0].strip())
        self.time_constant = float(text.split("RTC ")[-1].split("\n")[0].strip())
        self.receiver_gain = float(text.split("RRG ")[-1].split("\n")[0].strip())
        self.mod_amp = float(text.split("RMA ")[-1].split("\n")[0].strip())

        self.freq = float(text.split("MF ")[-1].split("\n")[0].strip())
        self.power_uW = float(text.split("MP ")[-1].split("\n")[0].strip())
        self.attenuation = float(text.split("MPD ")[-1].split("\n")[0].strip())
        try:
            self.gonio = float(text.split("GAN ")[-1].split("\n")[0].strip())
        except:
            self.gonio = None
        self.gonio_step = float(text.split("GANS ")[-1].split("\n")[0].strip())


def get_scan_params(file_name, silent=True):
    if file_name[-4:] == ".spc" or file_name[-4:] == ".par":
        file_name = file_name[:-4]

    with open(file_name + '.par', "r") as fl:
        text = fl.read()

    params = scan_params(text, silent=silent)

    return params



# Test for a 1D and a 2D file
if __name__ == "__main__":
    file_name = "../Data/JO240202C_Ni80_no_Ta_6nm/240415_1/exp2/-100to-60deg_steps10deg_exp2"
    try:
        pars = get_scan_params(file_name, False)
        print(pars.field_centre)
        print(pars.freq)
        print(pars.gonio)
        print(pars.y_num)
        print("")
    except FileNotFoundError:
        print(f"Could not find test file: {file_name}")


    file_name = "../Data/Fe_samps_Cu_investigation_Dec2025/JO240726C/100"
    try:
        pars = get_scan_params(file_name, False)
        print(pars.field_centre)
        print(pars.freq)
        print(pars.gonio)
    except FileNotFoundError:
        print(f"Could not find test file: {file_name}")
