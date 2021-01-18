# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 17:09:47 2020

@author: xuc1
"""
import numpy as np

para1 = {'ZL': 1.294390, 'ZU': 1.680000,
         'A': [6.429274, -7.514262, -0.725882, -1.117846, -0.562041, -0.360239, -0.229751, -0.135713, -0.068203,
               -0.029755]}
para2 = {'ZL': 1.112300, 'ZU': 1.383730,
         'A': [17.244846, -7.964373, 0.625343, -0.105068, 0.292196, -0.344492, 0.271670, -0.151722, 0.121320, -0.035566,
               0.045966]}
para3 = {'ZL': 0.909416, 'ZU': 1.122751,
         'A': [82.017868, -59.064244, -1.356615, 1.055396, 0.837341, 0.431875, 0.440840, -0.061588, 0.209414, -0.120882,
               0.055734, -0.035974]}
para4 = {'ZL': 0.070000, 'ZU': 0.997990,
         'A': [306.592351, -205.393808, -4.695680, -2.031603, -0.071792, -0.437682, 0.176352, -0.182516, 0.064687,
               -0.027019, 0.010019]}


def _Chebychev(volt, p):
    """
    Chebychev function to convert voltage to temperature

    Parameters
    ----------
    volt : float
        Voltage value in Volt
    p : dict
        Parameters dict

    Returns
    -------
    T : float
        Temperature in Kelvin
    """
    X = ((volt - p['ZL']) - (p['ZU'] - volt)) / (p['ZU'] - p['ZL'])
    T = 0
    for I, A in enumerate(p['A']):
        T = T + A * np.cos(I * np.arccos(X))
    return T


def Volt2Kelvin(volt):
    """
    Convert voltage to temperature

    Parameters
    ----------
    volt : float
        Voltage value in Volt

    Returns
    -------
    T : float
        Temperature in Kelvin
    """
    if volt < 0.090681 or volt > 1.65:
        return 0  # malfunctioning
    elif volt >= 1.334990:
        return _Chebychev(volt, para1)
    elif volt >= 1.1226855:
        return _Chebychev(volt, para2)
    elif volt >= 0.986974:
        return _Chebychev(volt, para3)
    else:
        return _Chebychev(volt, para4)
