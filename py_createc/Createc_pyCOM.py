# -*- coding: utf-8 -*-
"""
Created on Thu May 16 17:07:44 2019

@author: xuc1
"""
import numpy as np
import time
import win32com.client as win32
from utils.misc import XY2D

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
        
    def _ramp_bias_same_pole(self, _end_bias_mV, _init_bias_mV, _speed):
        """
        To be used by ramp_bias_mV(). 
        The end result is that the machine will ramp the bias gradually.
        input: _end_bias in mV and _init_bias in mV, which are of the same polarity.
               _speed can be any integer larger than 0. 1 means the fastest, default to 100
        output: None
        """
        bias_pole = np.sign(_init_bias_mV)
        init = _speed * np.log10(np.abs(_init_bias_mV))
        end = _speed * np.log10(np.abs(_end_bias_mV))
        sign = np.int(np.sign(end-init))
        for i in range(np.int(init)+sign, np.int(end)+ sign, sign):
            time.sleep(0.01)
            self.client.setparam('Biasvolt.[mV]', bias_pole*10**((i)/_speed))
        self.client.setparam('Biasvolt.[mV]', _end_bias_mV)
        
    def ramp_bias_mV(self, end_bias_mV, speed=100):
        """
        Ramp bias from one value to another value
        input: end_bias in mV
               speed can be any integer larger than 0. 1 means the fastest, default to 100
        output: None
        """
        speed = int(speed)
        assert speed > 0, 'speed should be larger than 0' 

        init_bias_mV = float(self.client.getparam('Biasvolt.[mV]'))
        if init_bias_mV * end_bias_mV == 0: pass
        elif init_bias_mV == end_bias_mV: pass
        elif init_bias_mV * end_bias_mV > 0:
            self._ramp_bias_same_pole(end_bias_mV, init_bias_mV, speed)
        else:
            if np.abs(init_bias_mV) > np.abs(end_bias_mV):
                self.client.setparam('Biasvolt.[mV]', -init_bias_mV)
                self._ramp_bias_same_pole(end_bias_mV, -init_bias_mV, speed)
            elif np.abs(init_bias_mV) < np.abs(end_bias_mV):
                self._ramp_bias_same_pole(-end_bias_mV, init_bias_mV, speed)
                self.client.setparam('Biasvolt.[mV]', end_bias_mV)
            else:
                self.client.setparam('Biasvolt.[mV]', end_bias_mV)
                
    def ramp_current_pA(self, end_FBLogIset, speed=100):
        """
        Ramp current from one value to another value
        input: end_current in pA
               speed can be any integer larger than 0. 1 means the fastest, default to 100
        output: None
        """
        speed = int(speed)
        assert speed > 0, 'speed should be larger than 0'
        
        init_FBLogIset = np.float(self.client.getparam('FBLogIset').split()[-1])
        if init_FBLogIset == end_FBLogIset: return
        if end_FBLogIset < 0: return
        # init_FBLogIset = np.int(init_FBLogIset)
        # end_FBLogIset = np.int(end_FBLogIset)
        # if init_FBLogIset == 0:
        _init_FBLogIset = init_FBLogIset if init_FBLogIset else 0.1
        _end_FBLogIset = end_FBLogIset if end_FBLogIset else 0.1
        init = np.int(speed * np.log10(np.abs(_init_FBLogIset)))
        end = np.int(speed * np.log10(np.abs(_end_FBLogIset)))
        one_step = np.int(np.sign(end - init))
        now = init
        while now!=end:
            time.sleep(0.01)
            now += one_step
            self.client.setparam('FBLogIset', 10**(now/speed))
        self.client.setparam('FBLogIset', end_FBLogIset)
    
    @property
    def current_pA(self):
        """
        Return current in pA
        """
        return self.client.getparam('FBLogIset')

    @property
    def bias_mV(self):
        """
        Return the bias in mV
        """
        return self.client.getparam('Biasvolt.[mV]')

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
    
    def pre_scan_01(self, chmode, rotation, ddeltaX, deltaX_dac, channels_code, ch_zoff=None, ch_bias=None):
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

    @property
    def nom_size(self):
        """
        return nominal size of image in angstrom in namedtuple (x, y)
        """
        x = float(self.client.getparam('Length x[A]'))
        y = float(self.client.getparam('Length y[A]'))
        return XY2D(x=x, y=y)

    @property
    def angle(self):
        """
        return the angle in deg
        """
        return float(self.client.getparam('Rotation'))
    
    