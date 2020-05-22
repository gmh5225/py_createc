# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 09:53:38 2020

@author: xuc1

Repo of data generators and functions
"""
import numpy as np
import datetime
import time

Log_Avg_Len = 5  # Average through recent X points for logging
Log_Interval = 60  # Logging every X seconds


def createc_fbz():
    """   
    function returning Createc channel feedback z value
    """
    import py_createc.Createc_pyCOM as cp
    createc = cp.CreatecWin32()
    return createc.client.getdacvalfb()


def createc_adc(channel, kelvin=False, arg0=1):
    """   
    function returning Createc channel ADC value
    """
    import py_createc.Createc_pyCOM as cp
    createc = cp.CreatecWin32()
    data = createc.client.getadcvalf(arg0, channel)
    if kelvin:
        import py_createc.DT670
        data = py_createc.DT670.Volt2Kelvin(data)
    return data


def f_cpu():
    """   
    function returning cpu in percetage
    """
    import psutil
    return psutil.cpu_percent(percpu=False)


def f_random():
    """   
    function returning a random value
    """
    return np.random.rand()


def f_random2():
    """   
    Another function returning a random value
    """
    try:
        data = f_random2.data
    except AttributeError:
        data = 0
    data += np.random.uniform(-1, 1) * 0.1
    f_random2.data = data
    return data


def f_sinewave():
    """
    Testing func returning a sinewave stream based on current time.

    Returns
    ------
    float
        the current streaming data
    """
    return np.sin(time.time()/1.)



def f_emitter(p=0.1):
    """
    Testing func returning a random value with probability p, else 0.
    Parameters
    ----------
    p : float, optional
        probablility. The default is 0.1.

    Returns
    ------
    float
        the current streaming data
    """
    v = np.random.rand()        
    return 0. if v>p else v


"""
The codes below are for archive
"""


def g_emitter(p=0.1):
    """
    Testing generator returning a random value with probability p, else 0.
    Parameters
    ----------
    p : float, optional
        probablility. The default is 0.1.

    Yields
    ------
    (datetime, float)
        A tuple of datetime object and a random float between (0,1)
    """
    while True:
        v = np.random.rand()        
        yield (datetime.datetime.now(), 0. if v>p else v)


def g_random():
    while True:
        data = np.random.rand()
        data = (datetime.datetime.now(), data)
        yield data


def g_sinewave():
    """
    Testing generator returning a sinewave stream based on current time.

    Yields
    ------
    (datetime, float)
        A tuple of datetime object and the current streaming data
    """
    while True:
        data = np.sin(time.time()/1.)
        data = (datetime.datetime.now(), data)
        yield data


def createc_ADC1_T():
    """   
    Generator returning Createc channel ADC1 and converting to Temperature
    
    Returns
    -------
    (datetime, float)
        A tuple of datetime object and the current streaming data
    """
    import Createc_pyCOM as cp
    import DT670
    createc = cp.CreatecWin32()
    while True:
        ADC1 = createc.client.getadcvalf(1, 1)
        yield(datetime.datetime.now(), DT670.Volt2Kelvin(ADC1))


def createc_ADC2_T():
    """   
    Generator returning Createc channel ADC2 and converting to Temperature
    
    Returns
    -------
    (datetime, float)
        A tuple of datetime object and the current streaming data
    """
    import Createc_pyCOM as cp
    import DT670
    createc = cp.CreatecWin32()
    while True:
        ADC2 = createc.client.getadcvalf(1, 2)
        yield(datetime.datetime.now(), DT670.Volt2Kelvin(ADC2))


def identity(x):
    return x


def logger():
    """
    Old logger generator, no use.
    """
    import collections
    gen = g_sinewave()
    old_data = collections.deque()
    old_data.append(next(gen))
    while True:
        data = next(gen)
        old_data.append(data)
        delta_t = data[0]-old_data[0][0]
        if delta_t.total_seconds() >= Log_Interval:
            temp = list(zip(*old_data))[1]
            ave = np.mean(temp[-(len(old_data) if len(old_data)<Log_Avg_Len else Log_Avg_Len):])
            print(f'{data[0]:%Y-%m-%d %H:%M} {ave:.3f}')
            old_data.clear()
        yield data


if __name__ == '__main__':
    import itertools
    from multiprocessing import Process
    gen_logger, gen_plot = itertools.tee(g_sinewave())


    def p1():
        for _ in range(5):
            print ('p1 ',next(gen_plot))
            time.sleep(0.2)


    def p2():
        for _ in range(5):
            print('p2 ', next(gen_logger))
            time.sleep(0.2)
    
    process1 = Process(target=p1)
    process2 = Process(target=p2)
    process1.start()
    process2.start()
    process1.join()
    process2.join()
