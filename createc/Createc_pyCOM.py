# -*- coding: utf-8 -*-
"""
Created on Thu May 16 17:07:44 2019

@author: xuc1
"""
import numpy as np
import time
from .utils.misc import XY2D
import yaml
import os

this_dir = os.path.dirname(__file__)
cgc_file = os.path.join(this_dir, 'Createc_global_const.yaml')
with open(cgc_file, 'rt') as f:
    cgc = yaml.safe_load(f.read())


class CreatecWin32:
    """
    The Createc wrapper class.

    The remote operation from http://spm-wiki.createc.de already provides lots of methods,
    this class is just a wrapper so many more custom methods can be added.
    """

    def __init__(self):
        """
        Initiator for CreatecWin32 class.

        Returns
        -------
        CreatecWin32
        """
        import win32com.client as win32
        from pywintypes import com_error

        try:
            # print('Trying EnsureDispatch')
            self.client = win32.gencache.EnsureDispatch(
                "pstmafm.stmafmrem")  # does not work for the new version STMAFM 4.3
        except com_error:
            # print('EnsureDispatch failed')
            try:
                # print('Trying again with DispatchEx')
                self.client = win32.DispatchEx("pstmafm.stmafmrem")  # Works for the new version STMAFM 4.3
            except com_error as error:
                # print('com_error')
                # print(error)
                # print('Cannot connect to STMAFM software')
                return

        self.savedatfilename = self.client.savedatfilename
        # self.xPiezoConst = float(self.client.getparam('XPiezoconst')) # different from py_File where it's 'Xpiezoconst'
        # self.yPiezoConst = float(self.client.getparam('YPiezoconst'))
        # self.zPiezoConst = float(self.client.getparam('ZPiezoconst'))

    def is_active(self):
        """
        To check if the STM software is still listening to python

        Returns
        -------
        is_active : Boolean
        """
        from pywintypes import com_error
        try:
            self.client.scanstatus
            return True
        except com_error:
            return False

    def _ramp_bias_same_pole(self, _end_bias_mV: float, _init_bias_mV: float, _speed: float):
        """
        To be called by ramp_bias_mV().
        The end result is the machine will ramp the bias gradually to the target value.

        Parameters
        ----------
        _end_bias_mV : float
            target bias in mV
        _init_bias_mV : float
            starting bias in mV, it should be of the same polarity of _end_bias_mV
        _speed : int
            speed is actually steps, it can be any integer larger than 0.
            1 means directly stepping to the final bias, it is default to 100.

        Returns
        -------
        None : None
        """
        bias_pole = np.sign(_init_bias_mV)
        init = _speed * np.log10(np.abs(_init_bias_mV))
        end = _speed * np.log10(np.abs(_end_bias_mV))
        sign = np.int(np.sign(end - init))
        for i in range(np.int(init) + sign, np.int(end) + sign, sign):
            time.sleep(0.01)
            self.client.setparam('Biasvolt.[mV]', bias_pole * 10 ** ((i) / _speed))
        self.client.setparam('Biasvolt.[mV]', _end_bias_mV)

    def ramp_bias_mV(self, end_bias_mV: float, speed: int = 100):
        """
        Ramp bias from current value to another value

        Parameters
        ----------
        end_bias_mV : float
            target bias in mV
        speed : int
            speed is actually steps, it can be any integer larger than 0.
            1 means directly stepping to the final value, it is default to 100.

        Returns
        -------
        None : None
        """
        speed = int(speed)
        assert speed > 0, "speed should be larger than 0"

        init_bias_mV = float(self.client.getparam('Biasvolt.[mV]'))
        if init_bias_mV * end_bias_mV == 0:
            pass
        elif init_bias_mV == end_bias_mV:
            pass
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

    def ramp_current_pA(self, end_FBLogIset: float, speed: int = 100):
        """
        Ramp current to the target value

        Parameters
        ----------
        end_FBLogIset : float
            end_current in pA
        speed : int
            speed is actually steps, it can be any integer larger than 0.
            1 means directly stepping to the final value, it is default to 100.

        Returns
        -------
        None : None
        """

        speed = int(speed)
        assert speed > 0, 'speed should be larger than 0'

        init_FBLogIset = np.float(self.client.getparam('FBLogIset').split()[-1])
        if init_FBLogIset == end_FBLogIset: return
        if end_FBLogIset < 0: return
        end_FBLogIset = end_FBLogIset * 10 ** (self.preampgain - cgc['g_preamp_gain'])
        # init_FBLogIset = np.int(init_FBLogIset)
        # end_FBLogIset = np.int(end_FBLogIset)
        # if init_FBLogIset == 0:
        _init_FBLogIset = init_FBLogIset if init_FBLogIset else 0.1
        _end_FBLogIset = end_FBLogIset if end_FBLogIset else 0.1
        init = np.int(speed * np.log10(np.abs(_init_FBLogIset)))
        end = np.int(speed * np.log10(np.abs(_end_FBLogIset)))
        one_step = np.int(np.sign(end - init))
        now = init
        while now != end:
            time.sleep(0.01)
            now += one_step
            self.client.setparam('FBLogIset', 10 ** (now / speed))
        self.client.setparam('FBLogIset', end_FBLogIset)

    @property
    def current_pA(self):
        """
        Return current in pA

        Returns
        -------
        current : str
        """
        current = float(self.client.getparam('FBLogIset')) * 10 ** (cgc['g_preamp_gain'] - self.preampgain)
        return f'{current:.2f}'

    @property
    def bias_mV(self):
        """
        Return the bias in mV

        Returns
        -------
        bias : str
        """
        return self.client.getparam('Biasvolt.[mV]')

    def scan_varying_size(self, chmod=0):
        """
        Not in use.
        """
        pass

    def setxyoffpixel(self, dx: int = 0, dy: int = 0):
        """
        Set xy offset by pixel

        Parameters
        ----------
        dx : int
            dx , dy in pixel
        dy : int
            dx , dy in pixel

        Returns
        -------
        None : None

        """
        self.client.setxyoffpixel(dx, dy)

    def pre_scan_config(self, chmode: int = None, rotation: float = None, ddeltaX: int = None,
                    deltaX_dac: int = None, deltaY_dac: int = None, channels_code: int = None,
                    ch_zoff: float = None, ch_bias: float = None, bias: float = None,
                    current: float = None):
        """
        Parameters configuration before scanning an image.

        Parameters
        ----------
        chmode : int
            constant height mode, int 0 or 1, which means false or true
        rotation : float
            angle in degree -360 ~ 360
        ddeltaX : int
            scan speed, int, usually 16, 32, 64 ...
        deltaX_dac : int
            scan size, usually take 32, 64, 128...
        deltaY_dac : int
            scan size, usually take 32, 64, 128...
        channels_code : int
            3 for const current mode, see online manual for more detail
        ch_zoff : float
            const height mode z offset in angstrom
        ch_bias : gloat
            const height mode bias in mV

        Returns
        -------
        None : None
        """
        if chmode is not None: self.client.setparam('CHMode', chmode)
        if rotation is not None: self.client.setparam('Rotation', rotation)
        if ddeltaX is not None: self.client.setparam('DX/DDeltaX', ddeltaX)
        if deltaX_dac is not None: self.client.setparam('Delta X [Dac]', deltaX_dac)
        if deltaY_dac is not None: self.client.setparam('Delta Y [Dac]', deltaY_dac)
        if channels_code is not None: self.client.setparam('ChannelSelectVal', channels_code)
        if ch_zoff is not None: self.client.setchmodezoff(ch_zoff)
        if ch_bias is not None: self.client.setparam('CHModeBias[mV]', ch_bias)
        if bias is not None: self.ramp_bias_mV(bias)
        if current is not None: self.ramp_current_pA(current)

    def do_scan_01(self):
        """
        Do the scan, and return the .dat file name with full path

        Not recommended to use because `scanwaitfinished` will freeze the STM software
        """
        self.client.scanstart()
        self.client.scanwaitfinished()

    @property
    def nom_size(self):
        """
        Get the nominal size of the image in Angstrom

        Returns
        -------
        nominal_size : XY2D

        """
        x = float(self.client.getparam('Length x[A]'))
        y = float(self.client.getparam('Length y[A]'))
        return XY2D(x=x, y=y)

    @property
    def angle(self):
        """
        return the scan rotation angle in deg

        Returns
        -------
        angle : float
        """
        return float(self.client.getparam('Rotation'))

    @property
    def xPiezoConst(self):
        """
        Get the X Piezo Constant

        Returns
        -------
        xPiezoConst : float
        """
        return float(self.client.getparam('XPiezoconst'))  # different from py_File where it's 'Xpiezoconst'

    @property
    def yPiezoConst(self):
        """
        Get the Y Piezo Constant

        Returns
        -------
        yPiezoConst : float
        """
        return float(self.client.getparam('YPiezoconst'))

    @property
    def zPiezoConst(self):
        """
        Get the Z Piezo Constant

        Returns
        -------
        zPiezoConst : float
        """
        return float(self.client.getparam('ZPiezoconst'))

    @property
    def offset(self):
        """
        Return offset relatvie to the whole scan range in angstrom

        Returns
        -------
        offset : XY2D
        """
        x_offset = float(self.client.getparam('OffsetX'))
        y_offset = float(self.client.getparam('OffsetY'))

        x_offset = -x_offset * cgc['g_XY_volt'] * self.xPiezoConst / 2 ** cgc['g_XY_bits']
        y_offset = -y_offset * cgc['g_XY_volt'] * self.yPiezoConst / 2 ** cgc['g_XY_bits']

        return XY2D(y=y_offset, x=x_offset)

    @property
    def preampgain(self):
        """
        Pre amplifier gain

        Returns
        -------
        gain : int
        """
        return int(self.client.getparam('GainPre 10^'))
