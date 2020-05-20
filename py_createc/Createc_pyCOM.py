# -*- coding: utf-8 -*-
"""
Created on Thu May 16 17:07:44 2019

@author: xuc1
"""
import numpy as np
import time
import win32com.client as win32

class CreatecWin32():
    """
    A Createc wrapper class
    input: None
    output:  Createc Win32COM object with some customized methods
    See http://spm-wiki.createc.de for a complete list for factory default methods
    """
    def __init__(self):
        self.client = win32.gencache.EnsureDispatch("pstmafm.stmafmrem")
        self.savedatfilename = self.client.savedatfilename
        
    def _ramp_bias_same_pole(self, _end_bias_mV, _init_bias_mV):
        """
        To be used by ramp_bias_mV(). 
        The end result is that the machine will ramp the bias gradually.
        input: _end_bias in mV and _init_bias in mV, which are of the same polarity.
        output: None
        """
        bias_pole = np.sign(_init_bias_mV)
        init = 100 * np.log10(np.abs(_init_bias_mV))
        end = 100 * np.log10(np.abs(_end_bias_mV))
        sign = np.int(np.sign(end-init))
        for i in range(np.int(init)+sign, np.int(end)+ sign, sign):
            time.sleep(0.01)
    #        print (10**((i)/100.))
            self.client.setparam('Biasvolt.[mV]', bias_pole*10**((i)/100.))
        self.client.setparam('Biasvolt.[mV]', _end_bias_mV)
        
    def ramp_bias_mV(self, end_bias_mV, init_bias_mV = None):
        """
        Ramp bias from one value to another value
        input: end_bias in mV, and optionally init_bias in mV
        output: None
        """
        if init_bias_mV is None:
            init_bias_mV = float(self.client.getparam('Biasvolt.[mV]'))
        if init_bias_mV * end_bias_mV == 0: pass
        elif init_bias_mV == end_bias_mV: pass
        elif init_bias_mV * end_bias_mV > 0:
            self._ramp_bias_same_pole(end_bias_mV, init_bias_mV)
        else:
            if np.abs(init_bias_mV) > np.abs(end_bias_mV):
                self.client.setparam('Biasvolt.[mV]', -init_bias_mV)
                self._ramp_bias_same_pole(end_bias_mV, -init_bias_mV)
            elif np.abs(init_bias_mV) < np.abs(end_bias_mV):
                self._ramp_bias_same_pole(-end_bias_mV, init_bias_mV)
                self.client.setparam('Biasvolt.[mV]', end_bias_mV)
            else:
                self.client.setparam('Biasvolt.[mV]', end_bias_mV)
                
    def ramp_current_log(self, end_FBLogIset, init_FBLogIset = None):
        """
        Ramp current from one value to another value
        input: end_current in Log10 form and optionally initial current in Log10 form
        output: None
        """
        if np.float(self.show_current_log_value()) == end_FBLogIset: return
        if init_FBLogIset is None:
            init_FBLogIset = np.float(self.client.getparam('FBLogIset').split()[-1])
        sign = np.sign(end_FBLogIset - init_FBLogIset)
        for i in range(np.int(init_FBLogIset + sign), np.int(end_FBLogIset + sign), np.int(sign)):
            time.sleep(0.001)
            self.client.setparam('FBLogIset', i*1.)
        self.client.setparam('FBLogIset', end_FBLogIset)
    
    def show_current_log_value(self):
        """
        Return current as log value
        """
        return self.client.getparam('FBLogIset')
    
    def scan_varying_size(self, chmod=0):
        """
        Not in use.
        """
        pass
    
    def setxyoffpixel(self, dx=0, dy=0):
        """
        Set xy offset by pixel
        input: dx , dy in pixel
        output: None
        """
        self.client.setxyoffpixel(dx, dy)
    
    def pre_scan_config_01(self, chmode, rotation, ddeltaX, deltaX_dac, channels_code, ch_zoff=None, ch_bias=None):
        """
        Parameters configuration before scanning an image.
        input: 
            chmod: constant height mode, int 0 or 1, which is false or true
            rotation: float number -360 ~ 360
            ddeltaX: scan speed, int, usually 16, 32, 64 ...
            deltaX_dac: scan size, assume deltaY_dac is the same, int, usually take 32, 64, 128...
            channels_code: int, 3 for const current mode, 30 for const height mode, see online manual for detail
            ch_zoff: optional, const height mode z offset in angstrom, float
            ch_bias: optional, const height mode bias in mV, float
        output: None
        """
        self.client.setparam('CHMode', chmode)        
        self.client.setparam('Rotation', rotation)
        self.client.setparam('DX/DDeltaX', ddeltaX)
        self.client.setparam('Delta X [Dac]', deltaX_dac)
        self.client.setparam('Delta Y [Dac]', deltaX_dac) #square shaped pixel
        self.client.setparam('ChannelSelectVal', channels_code)
        if ch_zoff is not None: self.client.setchmodezoff(ch_zoff)
        if ch_bias is not None: self.client.setparam('CHModeBias[mV]', ch_bias)
        
    def do_scan_01(self):
        """
        Do the scan, and return the .dat file name with full path
        input: None
        output: None
        """
        self.client.scanstart()
        self.client.scanwaitfinished()   