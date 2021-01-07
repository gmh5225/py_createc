# -*- coding: utf-8 -*-
"""
Created on Thu May 16 17:07:44 2019

@author: xuc1
"""
import numpy as np
import time
import win32com.client as win32
from .utils.misc import XY2D
import yaml
import os 
from pywintypes import com_error

dir = os.path.dirname(__file__)
cgc_file = os.path.join(dir, 'Createc_global_const.yaml')
with open(cgc_file, 'rt') as f:
    cgc = yaml.safe_load(f.read())

class CreatecWin32():
    """
    A Createc wrapper class
    input: None
    output:  Createc Win32COM object with some customized methods
    See http://spm-wiki.createc.de for a complete list for factory default methods
    """
    def __init__(self):
        #self.client = win32.gencache.EnsureDispatch("pstmafm.stmafmrem") # does not work for the new version STMAFM 4.3
        try:
            self.client = win32.DispatchEx("pstmafm.stmafmrem") # Works for the new version STMAFM 4.3
        except com_error as error:
            print('com_error')
            print(error)
            print('Cannot connect to STMAFM software')
            return
        self.savedatfilename = self.client.savedatfilename
        # self.xPiezoConst = float(self.client.getparam('XPiezoconst')) # different from py_File where it's 'Xpiezoconst'
        # self.yPiezoConst = float(self.client.getparam('YPiezoconst'))
        # self.zPiezoConst = float(self.client.getparam('ZPiezoconst'))
    
    def is_active(self):
        try: 
            self.client.scanstatus
            return True
        except com_error:
            return False

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
    
    def pre_scan_01(self, chmode=None, rotation=None, ddeltaX=None, 
                    deltaX_dac=None, deltaY_dac=None, channels_code=None, 
                    ch_zoff=None, ch_bias=None):
        """
        Parameters configuration before scanning an image.
        input: 
            chmod: constant height mode, int 0 or 1, which is false or true
            rotation: float number -360 ~ 360
            ddeltaX: scan speed, int, usually 16, 32, 64 ...
            deltaX_dac: scan size, int, usually take 32, 64, 128...
            deltaY_dac: scan size, int, usually take 32, 64, 128...
            channels_code: int, 3 for const current mode, 30 for const height mode, see online manual for detail
            ch_zoff: optional, const height mode z offset in angstrom, float
            ch_bias: optional, const height mode bias in mV, float
        output: None
        """
        if chmode is not None: self.client.setparam('CHMode', chmode)        
        if rotation is not None: self.client.setparam('Rotation', rotation)
        if ddeltaX is not None: self.client.setparam('DX/DDeltaX', ddeltaX)
        if deltaX_dac is not None: self.client.setparam('Delta X [Dac]', deltaX_dac)
        if deltaY_dac is not None: self.client.setparam('Delta Y [Dac]', deltaY_dac)
        if channels_code is not None:self.client.setparam('ChannelSelectVal', channels_code)
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
    

    @property
    def xPiezoConst(self):
        return float(self.client.getparam('XPiezoconst')) # different from py_File where it's 'Xpiezoconst'
    
    @property
    def yPiezoConst(self):
        return float(self.client.getparam('YPiezoconst'))

    @property
    def zPiezoConst(self):
        return float(self.client.getparam('ZPiezoconst'))

    @property
    def offset(self):
        """
        return offset relatvie to the whole range in angstrom in the format of 
        namedtuple (x, y)
        """
        x_offset = float(self.client.getparam('OffsetX'))
        y_offset = float(self.client.getparam('OffsetY'))

        x_offset = -x_offset*cgc['g_XY_volt']*self.xPiezoConst/2**cgc['g_XY_bits']
        y_offset = -y_offset*cgc['g_XY_volt']*self.yPiezoConst/2**cgc['g_XY_bits']

        return XY2D(y=y_offset, x=x_offset)