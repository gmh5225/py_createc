# -*- coding: utf-8 -*-
"""
     Oscilloscope with logging (graphing by Bokeh)
     Implemented with producer/consumer model
     Main thread :  data_producer and a Bokeh server for graphing
     Child thread : Logger (consumer)
"""


import createc.utils.data_producer as dp
from createc.Createc_pyCOM import CreatecWin32
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


Scope_Points = 50000  # total points to show in each channel in the scope
Log_Avg_Len = 5  # Average through recent X points for logging
Log_Interval = 60  # Logging every X seconds
Stream_Interval = 0.2  # I/O data fetching interval in seconds (Stream_Interval <= Consumer_Timeout)
Consumer_Timeout = None  # timeout for consumers in second, None for never timeout


def logger(buffer_q, labels, log_name, quit_sig):
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
        Thead quit signal
    """
    import logging.config
    import logging
    import os

    this_dir = os.path.dirname(__file__)
    log_config = os.path.join(this_dir, 'logger.config')
    log_file = log_name + '.log'
    logging.config.fileConfig(log_config, defaults={'logfilename': this_dir+'/'+log_file})
    this_logger = logging.getLogger('this_logger')

    try:
        data_pak = buffer_q.get(timeout=Consumer_Timeout)
    except queue.Empty:
        print('Logger timeouts waiting for data stream, try adjusting Stream_Interval and/or Consumer_Timeout')
        return None
    prev = []
    for index, data in enumerate(data_pak):
        prev.append(data[0])  # if v2 does not work, it is b/c of this line cannot be fixed with only 1 queue
        msg = f'{labels[index]}\t{data[0]:%Y-%m-%d %H:%M:%S}\t{data[1]:.3f}'
        this_logger.info(msg)

    while not quit_sig.is_set():
        try:
            data_pak = buffer_q.get(timeout=Consumer_Timeout)
        except queue.Empty:
            print('Logger timeouts waiting for data stream, try adjusting Stream_Interval and/or Consumer_Timeout')
            return
        for index, data in enumerate(data_pak):
            delta = data[0] - prev[index]
            if delta.total_seconds() >= Log_Interval:
                msg = f'{labels[index]}\t{data[0]:%Y-%m-%d %H:%M:%S}\t{data[1]:.3f}'
                this_logger.info(msg)
                prev[index] = data[0]
        time.sleep(Stream_Interval)  # try to be in sync with producer, but not necessary


def make_document(doc, log_q, funcs, labels):
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

    Returns
    -------
    None : None
    """

    def update():
        """
        The data producer and updater for bokeh server
        """
        data_pak = tuple((dt.datetime.now(), func()) for func in funcs)
        log_q.put(data_pak)
        for index, data in enumerate(data_pak):
            sources[index].stream(dict(time=[data[0]], data=[data[1]]), Scope_Points)
            annotations[index].text = f'{data[1]: .2f}'

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
                           y_axis_label=labels[i],
                           toolbar_location=None, active_drag=None, active_scroll=None, tools=[hover]))
        figs[i].line(x='time', y='data', source=sources[i], line_color='red')
        annotations.append(Label(x=10, y=10, text='text', text_font_size=font_size, text_color='white',
                                 x_units='screen', y_units='screen', background_fill_color=None))
        figs[i].add_layout(annotations[i])

    doc.theme = 'dark_minimal'
    doc.title = "Oscilloscope"
    doc.add_root(column([fig for fig in figs], sizing_mode='stretch_both'))
    doc.add_periodic_callback(callback=update, period_milliseconds=Stream_Interval * 1000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='An oscilloscope, showing random signals if no args given')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-z", "-i", "--zi", help="show feedback Z and current", action="store_true")
    group.add_argument("-t", "--temperature", help="show temperatures", action="store_true")
    group.add_argument("-c", "--cpu", help="show cpu usage", action="store_true")
    group.add_argument("-a", "--adc", help="show ADC signals board 1..2 channel 0..5", action="store_true")
    parser.add_argument("-p", "--port", help="specify a port", default=5001, type=int)
    args = parser.parse_args()

    if args.zi:
        stm = CreatecWin32()
        producer_funcs = [partial(dp.createc_fbz, stm=stm),
                          partial(dp.createc_adc, stm=stm, channel=0, kelvin=False, board=1)]
        y_labels = ['Feedback Z', 'Current']
        logger_name = 'zi'
    elif args.temperature:
        stm = CreatecWin32()
        producer_funcs = [partial(dp.createc_auxadc_6, stm=stm),  # new version STMAFM 4.3 provides direct read of temperature as string.
                          partial(dp.createc_auxadc_7, stm=stm)]  # these two get the temperature as float number in Kelvin
        y_labels = ['STM(K)', 'LHe(K)']
        logger_name = 'temperature'
    elif args.cpu:
        producer_funcs = [dp.f_cpu]
        y_labels = ['CPU']
        logger_name = 'CPU'
    elif args.adc:
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
        y_labels = ['ADC'+str(i) for i in range(12)]
        logger_name = 'ADC'
    else:
        producer_funcs = [dp.f_random, dp.f_random2, dp.f_emitter]
        y_labels = ['Random1', 'Random2', 'Emitter']
        logger_name = 'random'

    logger_q = queue.Queue()

    # Start the data producer thread and the logger thread
    quit_signal = Event()  # signal for terminating all threads

    logging = Thread(target=logger, args=(logger_q, y_labels, logger_name, quit_signal))
    logging.start()
    print('Start logging thread')

    # Main thread for graphing
    server = Server({'/': partial(make_document, log_q=logger_q, funcs=producer_funcs, labels=y_labels)}, port=args.port)
    server.start()
    server.io_loop.add_callback(server.show, "/")
    try:
        server.io_loop.start()
    except KeyboardInterrupt:
        quit_signal.set()
        print('Keyboard interruption')
    print('Done')
