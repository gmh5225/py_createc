# -*- coding: utf-8 -*-
"""
     Oscilloscope with logging (graphing by Bokeh)
     Implemented with producer/consumer model
     Main thread :  data_producer and a Bokeh server for graphing
     Child thread : Logger (consumer)
"""

from bokeh.server.server import Server
from bokeh.models import ColumnDataSource, Label, HoverTool
from bokeh.plotting import figure
from bokeh.layouts import column
from functools import partial
import time
import datetime as dt
from threading import Thread, Event
import queue
import argparse

# Scope_Points = 50000  # total points to show in each channel in the scope
# Log_Avg_Len = 5  # Average through recent X points for logging
# Format_Specifier = '.2f'  # Format specifier for the values shown in the logger as well as in the scope annotation
# Stream_Interval = 0.2  # I/O data fetching interval in seconds (Stream_Interval <= Consumer_Timeout)
Consumer_Timeout = None  # timeout for consumers in second, None for never timeout


def logger(buffer_q, labels, log_name, quit_sig, log_interval, format_specifier, interval):
    """
    A logger function logging result to stdout and/or file

    Parameters
    ----------
    buffer_q : queue.Queue
        A queue of data from data producer
    labels : list(str)
        List of osc labels
    log_name : str
        For logger file name
    quit_sig : threading.Event
        Thread quit signal
    log_interval : int
        Log interval in seconds
    format_specifier : str
        Format specifier for the values shown in the logger
    interval: int
        Stream interval in milliseconds
    """
    import logging.config
    import logging
    import os

    this_dir = os.path.dirname(__file__)
    log_config = os.path.join(this_dir, 'logger.config')
    log_file = log_name + '_' + dt.datetime.now().strftime("%Y%m%d_%H%M%S") + '.log'
    logging.config.fileConfig(log_config, defaults={'logfilename': os.path.join(this_dir, 'logs', log_file).replace("\\", "/")})
    this_logger = logging.getLogger('this_logger')

    try:
        data_pak = buffer_q.get(timeout=Consumer_Timeout)
    except queue.Empty:
        print('Logger timeouts waiting for data stream, try adjusting Stream_Interval and/or Consumer_Timeout')
        return None
    prev = []
    for index, data in enumerate(data_pak):
        prev.append(data[0])  # if v2 does not work, it is b/c of this line cannot be fixed with only 1 queue
        msg = f'{labels[index]}\t{data[0]:%Y-%m-%d %H:%M:%S}\t{data[1]:{format_specifier}}'
        this_logger.info(msg)

    while not quit_sig.is_set():
        try:
            data_pak = buffer_q.get(timeout=Consumer_Timeout)
        except queue.Empty:
            print('Logger timeouts waiting for data stream, try adjusting Stream_Interval and/or Consumer_Timeout')
            return
        for index, data in enumerate(data_pak):
            delta = data[0] - prev[index]
            if delta.total_seconds() >= log_interval:
                msg = f'{labels[index]}\t{data[0]:%Y-%m-%d %H:%M:%S}\t{data[1]:{format_specifier}}'
                this_logger.info(msg)
                prev[index] = data[0]
        #time.sleep(interval * 0.001)  # try to be in sync with producer, but not necessary


def make_document(doc, log_q, funcs, labels, scope_points, format_specifier, y_axis_type, interval):
    """
    The document for bokeh server, it takes care of data producer in the update() function

    Parameters
    ----------
    doc :
        The current doc
    log_q : queue.Queue
        The queue holding the data for logger
    funcs : list(functions)
        List of producer functions
    labels : list(str)
        List of osc labels
    scope_points : int
        Total points shown in a scope
    format_specifier : str
        Format specifier for the values shown in the scope annotation

    Returns
    -------
    None : None
    """

    def update():
        """
        The data producer and updater for bokeh server
        """
        data_list = []
        for func in funcs:
            data_list += [(dt.datetime.now(), res) for res in func()]

        data_pak = tuple(data_list)
        log_q.put(data_pak)
        for index, data in enumerate(data_pak):
            sources[index].stream(dict(time=[data[0]], data=[data[1]]), scope_points)
            annotations[index].text = f'{data[1]:{format_specifier}}'

    sources = [ColumnDataSource(dict(time=[], data=[])) for _ in range(len(labels))]
    figs = []
    annotations = []
    font_size = str(20 / len(labels)) + 'vh'
    hover = HoverTool(
        tooltips=[
            ("value", "$y"),
            ("time", "$x{%F %T}")
        ],
        formatters={"$x": "datetime"}
    )
    for i in range(len(labels)):
        figs.append(figure(x_axis_type='datetime',
                           y_axis_type=y_axis_type,
                           y_axis_label=labels[i],
                           toolbar_location=None, active_drag=None, active_scroll=None, tools=[hover]))
        figs[i].line(x='time', y='data', source=sources[i], line_color='red')
        annotations.append(Label(x=10, y=10, text='text', text_font_size=font_size, text_color='white',
                                 x_units='screen', y_units='screen', background_fill_color=None))
        figs[i].add_layout(annotations[i])

    doc.theme = 'dark_minimal'
    doc.title = "Oscilloscope"
    doc.add_root(column([fig for fig in figs], sizing_mode='stretch_both'))
    doc.add_periodic_callback(callback=update, period_milliseconds=interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='An oscilloscope, showing random signals if no argument is given.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-z", "--zi", help="show feedback Z and current", action="store_true")
    group.add_argument("-t", "--temperature", help="show temperatures", action="store_true")
    group.add_argument("-c", "--cpu", help="show cpu usage", action="store_true")
    group.add_argument("-a", "--adc", help="show ADC signals board 1..2 channel 0..5", action="store_true")
    group.add_argument("-p", "--pressure", help="show pressure", action="store_true")

    parser.add_argument("-o", "--port", help="specify a port", default=5001, type=int)
    parser.add_argument("-l", "--log_interval", help="log interval in seconds", default=5, type=int)
    parser.add_argument("-s", "--scope_points", help="total points shown in a scope", default=50000, type=int)
    parser.add_argument("-i", "--interval", help="stream interval in milliseconds", default=500, type=int)

    args = parser.parse_args()
    y_axis_type = 'linear'
    fs = '.2f'
    if args.zi:
        import createc.utils.data_producer as dp
        from createc.Createc_pyCOM import CreatecWin32

        stm = CreatecWin32()
        producer_funcs = [partial(dp.createc_fbz, stm=stm),
                          partial(dp.createc_adc, stm=stm, channel=0, kelvin=False, board=1)]
        y_labels = ['Feedback Z', 'Current']
        logger_name = 'zi'
    elif args.temperature:
        import createc.utils.data_producer as dp
        from createc.Createc_pyCOM import CreatecWin32

        stm = CreatecWin32()
        producer_funcs = [partial(dp.createc_auxadc_6, stm=stm),
                          # new version STMAFM 4.3 provides direct read of temperature as string.
                          partial(dp.createc_auxadc_7,
                                  stm=stm)]  # these two get the temperature as float number in Kelvin
        y_labels = ['STM(K)', 'LHe(K)']
        logger_name = 'temperature'
    elif args.cpu:
        import createc.utils.data_producer as dp

        producer_funcs = [dp.f_cpu]
        y_labels = ['CPU']
        logger_name = 'CPU'
    elif args.adc:
        import createc.utils.data_producer as dp
        from createc.Createc_pyCOM import CreatecWin32

        stm = CreatecWin32()
        producer_funcs = [partial(dp.createc_adc, stm=stm, channel=0, board=1),
                          partial(dp.createc_adc, stm=stm, channel=1, board=1),
                          partial(dp.createc_adc, stm=stm, channel=2, board=1),
                          partial(dp.createc_adc, stm=stm, channel=3, board=1),
                          partial(dp.createc_adc, stm=stm, channel=4, board=1),
                          partial(dp.createc_adc, stm=stm, channel=5, board=1),
                          partial(dp.createc_adc, stm=stm, channel=0, board=2),
                          partial(dp.createc_adc, stm=stm, channel=1, board=2),
                          partial(dp.createc_adc, stm=stm, channel=2, board=2),
                          partial(dp.createc_adc, stm=stm, channel=3, board=2),
                          partial(dp.createc_adc, stm=stm, channel=4, board=2),
                          partial(dp.createc_adc, stm=stm, channel=5, board=2)]
        y_labels = ['ADC' + str(i) for i in range(12)]
        logger_name = 'ADC'
    elif args.pressure:
        def prep_p_dp(ser):
            """

            Parameters
            ----------
            ser : serial.Serial
                Serial instance

            Returns
            -------
            response : float
                Pressure in mbar
            """
            ser.write('#RD\r'.encode())
            response = ser.readline()
            if len(response) == 0:
                return 0
            return float(response[2:-1]),


        def loadlock_p_dp(ser):
            """

            Parameters
            ----------
            ser : serial.Serial
                Serial instance

            Returns
            -------
            response : float
                Pressure in mbar
            """
            ser.write(b"RPV1\r")
            response = ser.read(size=50).decode('ascii').split(',')
            try:
                return float(response[1]),
            except IndexError:
                return 0,


        def gasline_p_dp(ser):
            """

            Parameters
            ----------
            ser : serial.Serial
                Serial instance

            Returns
            -------
            response : float
                Pressure in mbar
            """
            ser.write(b"RPV3\r")
            response = ser.read(size=50).decode('ascii').split(',')
            try:
                return float(response[1]),
            except IndexError:
                return 0,
            

        def vacom_p_dp(ser):
            """

            Parameters
            ----------
            ser : serial.Serial
                Serial instance

            Returns
            -------
            response : tuple
                Pressures in mbar
            """
            ser.write(b"RPV3\r")
            try:
                p = ser.read(size=100).decode('cp1252', errors='ignore').strip().split('0,')
            except IndexError:
                p = ['000', '000']
            ser.write(b"RPV3\r")
            ser.write(b"RPV1\r")
            return float(p[-1].strip()), float(p[1].strip())

        def main_ion_p_dp(ser):
            """

            Parameters
            ----------
            ser : serial.Serial
                Serial instance

            Returns
            -------
            response : float
                Pressure in mbar
            """
            ser.write(b'~ 05 0B 02 00\r')
            response = ser.readline()
            return float(response.split()[3]),


        import serial

        ser_prep_p = serial.Serial('COM4', timeout=0)
        ser_vacom_p = serial.Serial('COM6', timeout=0)
        ser_main_ion_p = serial.Serial('COM7', timeout=0)
        producer_funcs = [partial(main_ion_p_dp, ser=ser_main_ion_p),
                          partial(prep_p_dp, ser=ser_prep_p),
                          partial(vacom_p_dp, ser=ser_vacom_p)
                          ]
        y_labels = ['Main_Ion_P',
                    'Prep_P', 
                    'Loadlock_P',
                    'Gasline_P'
                    ]
        logger_name = 'pressure'
        fs = '.2e'
        y_axis_type = 'log'
    else:
        import createc.utils.data_producer as dp

        producer_funcs = [dp.f_random_tuple1, dp.f_random_tuple2]
        y_labels = ['Random1', 'Random2-1', 'Random2-2']
        logger_name = 'random'

    logger_q = queue.Queue()

    # Start the data producer thread and the logger thread
    quit_signal = Event()  # signal for terminating all threads

    logging = Thread(target=logger,
                     args=(logger_q, y_labels, logger_name, quit_signal, args.log_interval, fs, args.interval))
    logging.start()
    print('Start logging thread')

    # Main thread for graphing
    server = Server({'/': partial(make_document, log_q=logger_q, funcs=producer_funcs, labels=y_labels,
                                  scope_points=args.scope_points, format_specifier=fs,
                                  y_axis_type=y_axis_type, interval=args.interval)},
                    port=args.port)
    server.start()
    server.io_loop.add_callback(server.show, "/")
    try:
        server.io_loop.start()
    except KeyboardInterrupt:
        quit_signal.set()
        print('Keyboard interruption')
"""
    finally:
        try: 
            ser_prep_p
        except NameError:
            pass
        else:
            if ser_prep_p.isOpen():
                ser_prep_p.close()
                
        try:
            ser_vacom_p
        except NameError:
            pass
        else:
            if ser_vacom_p.isOpen():
                ser_vacom_p.close()
                
        try:
            ser_main_ion_p
        except NameError:
            pass
        else:
            if ser_main_ion_p.isOpen():
                ser_main_ion_p.close()
"""
