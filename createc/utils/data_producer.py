# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 09:53:38 2020

@author: xuc1

Repo of data generators and functions
"""
import numpy as np
import datetime
import time

# these two are not in use
Log_Avg_Len = 5  # Average through recent X points for logging
Log_Interval = 60  # Logging every X seconds


def createc_fbz(stm):
    """   
    Function returning Createc channel feedback z value

    Parameters
    ----------
    stm : createc.CreatecWin32
        Createc instance
    Returns
    -------
    value : tuple

    """
    # from createc.Createc_pyCOM import CreatecWin32
    # stm = CreatecWin32()
    return stm.getdacvalfb(),


def createc_adc(stm, channel, board, kelvin=False):
    """   
    Function returning Createc channel ADC value
    Note that the kelvin param is for the old software.
    For the new version STMAFM 4.3, only ADC values are meant to be read out.
    
    Parameters
    ----------
    stm : createc.CreatecWin32
        Createc instance
    channel : int
        Channel number
    board : int
        Board number
    kelvin : bool
        Whether it is for temperature
        
    Returns
    -------
    data : tuple

    """
    data = stm.getadcvalf(board, channel)
    if kelvin:
        import createc.utils.DT670
        data = createc.utils.DT670.Volt2Kelvin(data)
    return data,


def createc_auxadc_6(stm):
    """
    Function to return the STM temperature as float number in Kelvin

    Parameters
    ----------
    stm : createc.CreatecWin32
        Createc instance

    Returns
    -------
    temperature : tuple
    """
    stm.setparam('MEMO_STMAFM', '')  # dummy function to 'manually' update the temperature reading
    return float(stm.getparam('T_AUXADC6[K]')),


def createc_auxadc_7(stm):
    """
    Function to return the LHe temperature as float number in Kelvin

    Parameters
    ----------
    stm : createc.CreatecWin32
        Createc instance

    Returns
    -------
    temperature : tuple
    """
    stm.setparam('MEMO_STMAFM', '')  # dummy function to 'manually' update the temperature reading
    return float(stm.getparam('T_AUXADC7[K]')),


def f_cpu():
    """   
    Function returning cpu in percetage

    Returns
    -------
    cpu : tuple
    """
    import psutil
    return psutil.cpu_percent(percpu=False),


def f_ram():
    """   
    Function returning RAM in percetage

    Returns
    -------
    ram : float
    """
    import psutil
    return psutil.swap_memory().percent


def f_random():
    """   
    Function returning a random value

    Returns
    -------
    value : float
    """
    return np.random.rand()


def f_random2():
    """   
    Another function returning a random value

    Returns
    -------
    value : float
    """
    try:
        data = f_random2.data
    except AttributeError:
        data = 0
    data += np.random.uniform(-1, 1) * 0.1
    f_random2.data = data
    return data


def f_random_tuple2():
    """
    A function to return a tuple of two random floats

    Returns
    -------
    value : tuple
    """
    return np.random.rand(), np.random.rand()


def f_random_tuple1():
    """
    A function to return a tuple of one random float

    Returns
    -------
    value : tuple
    """
    return np.random.rand(),


def f_sinewave():
    """
    Testing func returning a sinewave stream based on current time.

    Returns
    -------
    value : float
    """
    return np.sin(time.time() / 1.)


def f_emitter(p=0.1):
    """
    Testing func returning a random value with probability p, else 0.

    Parameters
    ----------
    p : float, optional
        probablility. The default is 0.1.

    Returns
    -------
    value : float
    """
    v = np.random.rand()
    return 0. if v > p else v


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
        yield (datetime.datetime.now(), 0. if v > p else v)


def g_random():
    """
    Testing generator returning a random value

    Yields
    ------
    (datetime, float)
        A tuple of datetime object and a random float between (0, 1)

    """
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
        data = np.sin(time.time() / 1.)
        data = (datetime.datetime.now(), data)
        yield data


def createc_ADC1_T():
    """   
    Generator returning Createc channel ADC1 and converting to Temperature
    
    Yields
    -------
    (datetime, float)
        A tuple of datetime object and the current streaming data
    """
    import createc.Createc_pyCOM as cp
    import DT670
    stm = cp.CreatecWin32()
    while True:
        ADC1 = stm.getadcvalf(1, 1)
        yield (datetime.datetime.now(), DT670.Volt2Kelvin(ADC1))


def createc_ADC2_T():
    """   
    Generator returning Createc channel ADC2 and converting to Temperature
    
    Yields
    -------
    (datetime, float)
        A tuple of datetime object and the current streaming data
    """
    import createc.Createc_pyCOM as cp
    import DT670
    stm = cp.CreatecWin32()
    while True:
        ADC2 = stm.getadcvalf(1, 2)
        yield (datetime.datetime.now(), DT670.Volt2Kelvin(ADC2))


def identity(x):
    """
    An identity function return the variable itself

    Parameters
    ----------
    x : object
        any object
    Returns
    -------
    x : object
    """
    return x


def logger():
    """
    Old logger generator, no use.

    Yields
    -------
    (datetime, float)

    """
    import collections
    gen = g_sinewave()
    old_data = collections.deque()
    old_data.append(next(gen))
    while True:
        data = next(gen)
        old_data.append(data)
        delta_t = data[0] - old_data[0][0]
        if delta_t.total_seconds() >= Log_Interval:
            temp = list(zip(*old_data))[1]
            ave = np.mean(temp[-(len(old_data) if len(old_data) < Log_Avg_Len else Log_Avg_Len):])
            print(f'{data[0]:%Y-%m-%d %H:%M} {ave:.3f}')
            old_data.clear()
        yield data


if __name__ == '__main__':
    import itertools
    from multiprocessing import Process

    gen_logger, gen_plot = itertools.tee(g_sinewave())


    def p1():
        for _ in range(5):
            print('p1 ', next(gen_plot))
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
