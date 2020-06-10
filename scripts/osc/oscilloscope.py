###########################
#      Oscilloscope with logging (graphing by Bokeh)
#      implemeted with producer/consumer model
#      individual thread for each producer/consumer
#                               --->(consumer)Bokeh server for graphing
#                             /
#       data_producer-
#                             \
#                               --->(consumer)Logger
###########################

import py_createc.data_producer as dp
from bokeh.server.server import Server
from bokeh.models import ColumnDataSource, Label, HoverTool
from bokeh.plotting import figure
from bokeh.layouts import column
from functools import partial
import time
import numpy as np
import datetime as dt
from threading import Thread, main_thread
import queue
import argparse


Scope_Points = 1200  # total points to show in each channel in the scope
Log_Avg_Len = 5  # Average through recent X points for logging
Log_Interval = 60  # Logging every X seconds
Stream_Interval = 0.2  # I/O data fetching interval in seconds (Stream_Interval <= Consumer_Timeout)
Consumer_Timeout = None  # timeout for consumers in second, None for never timeout


def data_producer(funcs, graph_q, logger_q):
    """
    To produce data
    :param funcs: data producer functions
    :param graph_q: a queue to hold data produced for graphing
    :param logger_q: q queue to hold the same data for logger
    :return: None
    """
    while main_thread().is_alive():
        data_pak = tuple((dt.datetime.now(), func()) for func in funcs)
        graph_q.put(data_pak)
        logger_q.put(data_pak)
        time.sleep(Stream_Interval)


def logger(buffer_q, labels, logger_name):
    """
    A logger function logging result to stdout and/or file
    :param buffer_q: a queue of data from data producer
    :param labels: the labels for all channels
    :return: None
    """
    import logging.config
    import logging

    logging.config.fileConfig('./scripts/osc/logger.config', defaults={'logfilename': './logs/osc_'+logger_name+'.log'})
    logger = logging.getLogger('this_logger')

    try:
        data_pak = buffer_q.get(timeout=Consumer_Timeout)
    except queue.Empty:
        print('Logger timeouts waiting for data stream, try adjusting Stream_Interval and/or Consumer_Timeout')
        return None
    prev = []
    for index, data in enumerate(data_pak):
        prev.append(data[0])  # if v2 does not work, it is b/c of this line cannot be fixed with only 1 queue
        msg = f'{labels[index]}\t{data[0]:%Y-%m-%d %H:%M:%S}\t{data[1]:.3f}'
        logger.info(msg)

    while main_thread().is_alive():
        try:
            data_pak = buffer_q.get(timeout=Consumer_Timeout)
        except queue.Empty:
            print('Logger timeouts waiting for data stream, try adjusting Stream_Interval and/or Consumer_Timeout')
            return
        for index, data in enumerate(data_pak):
            delta = data[0] - prev[index]
            if delta.total_seconds() >= Log_Interval:
                msg = f'{labels[index]}\t{data[0]:%Y-%m-%d %H:%M:%S}\t{data[1]:.3f}'
                logger.info(msg)
                prev[index] = data[0]
        time.sleep(Stream_Interval)  # try to be in sync with producer, but not necessary


def make_document(doc, buffer_q, labels):
    """
    The document for bokeh server
    :param doc: The current doc
    :param buffer_q: the queue holding the data from data producer
    :param labels: the labels for all channels
    :return: None
    """
    def update():
        data_pak = buffer_q.get(timeout=Consumer_Timeout)
        for index, data in enumerate(data_pak):
            sources[index].stream(dict(time=[data[0]], data=[data[1]]), Scope_Points)
            annotations[index].text = f'{data[1]: .2f}'

    sources = [ColumnDataSource(dict(time=[], data=[])) for _ in range(len(labels))]
    figs = []
    annotations = []
    font_size = str(20/len(labels))+'vh'
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
    doc.add_periodic_callback(callback=update, period_milliseconds=Stream_Interval*1000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='An oscilloscope, showing random signals if no args given')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-z", "-i", "--zi", help="show feedback Z and current", action="store_true")
    group.add_argument("-t", "--temperature", help="show temperatures", action="store_true")
    group.add_argument("-c", "--cpu", help="show cpu usage", action="store_true")
    group.add_argument("-a", "--adc", help="show ADC signals board 1..2 channel 0..5", action="store_true")
    args = parser.parse_args()

    if args.zi:
        producer_funcs = [dp.createc_fbz,
                          partial(dp.createc_adc, channel=0, kelvin=False, board=1)]
        y_labels = ['Feedback Z', 'Current']
        logger_name = 'zi'  
    elif args.temperature:
        producer_funcs = [partial(dp.createc_adc, channel=2, kelvin=True, board=1), 
                          partial(dp.createc_adc, channel=3, kelvin=True, board=1)]
        y_labels = ['STM(K)', 'LHe(K)']
        logger_name = 'temperature' 
    elif args.cpu:
        producer_funcs = [dp.f_cpu]                     
        y_labels = ['CPU']
        logger_name = 'CPU'
    elif args.adc:
        producer_funcs = [partial(dp.createc_adc, channel=0, board=1),
                          partial(dp.createc_adc, channel=1, board=1),
                          partial(dp.createc_adc, channel=2, board=1),
                          partial(dp.createc_adc, channel=3, board=1),
                          partial(dp.createc_adc, channel=4, board=1),
                          partial(dp.createc_adc, channel=5, board=1),
                          partial(dp.createc_adc, channel=0, board=2),
                          partial(dp.createc_adc, channel=1, board=2),
                          partial(dp.createc_adc, channel=2, board=2),
                          partial(dp.createc_adc, channel=3, board=2),
                          partial(dp.createc_adc, channel=4, board=2),
                          partial(dp.createc_adc, channel=5, board=2)]             
        y_labels = [str(i) for i in range(12)]
        logger_name = 'ADC'
    else:
        producer_funcs = [dp.f_random, dp.f_random2, dp.f_emitter]
        y_labels = ['Random1', 'Random2', 'Emitter']
        logger_name = 'random'   
    # Two queues, one for graphing one for logging
    channels = len(producer_funcs)
    graph_q = queue.Queue()
    logger_q = queue.Queue()

    # Start the data producer thread and the logger thread
    producer = Thread(target=data_producer, args=(producer_funcs, graph_q, logger_q))
    producer.start()
    logging = Thread(target=logger, args=(logger_q, y_labels, logger_name))
    logging.start()
    print('Start')

    # Main thread for graphing
    print('Opening Bokeh application on http://localhost:5006/')
    server = Server({'/': partial(make_document, buffer_q=graph_q, labels=y_labels)})
    server.start()
    server.io_loop.add_callback(server.show, "/")
    try:
        server.io_loop.start()
    except KeyboardInterrupt:
        print('keyboard interruption')
    print('Done')