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


def logger(buffer_q, labels, logger_cfg_file):
    """
    A logger function logging result to stdout and/or file
    :param buffer_q: a queue of data from data producer
    :param labels: the labels for all channels
    :return: None
    """
    import yaml
    import logging.config

    with open(logger_cfg_file, 'rt') as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
    logger = logging.getLogger(__name__)

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
        annotations.append(Label(x=10, y=10, text='text', text_font_size='10vh', text_color='white',
                                 x_units='screen', y_units='screen', background_fill_color=None))
        figs[i].add_layout(annotations[i])
        # annotations[i].text_font_size = str(figs[i].plot_height * 0.01)+'rem'
        
    doc.theme = 'dark_minimal'
    doc.title = "Oscilloscope"
    doc.add_root(column([fig for fig in figs], sizing_mode='stretch_both'))
    doc.add_periodic_callback(callback=update, period_milliseconds=Stream_Interval*1000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='An oscilloscope')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-z", "-i", "--zi", help="show feedback Z and current", action="store_true")
    group.add_argument("-t", "--temperature", help="show temperatures", action="store_true")
    group.add_argument("-r", "--random", help="show random values", action="store_true")
    args = parser.parse_args()

    if args.zi:
        producer_funcs = [dp.createc_fbz,
                          partial(dp.createc_adc, channel=0, kelvin=False)]
        y_labels = ['Feedback Z', 'Current']
        logger_cfg = './osc/logging_stream_ZI.yaml'  
    elif args.temperature:
        producer_funcs = [partial(dp.createc_adc, channel=2, kelvin=True), 
                          partial(dp.createc_adc, channel=3, kelvin=True)]
        y_labels = ['STM(K)', 'LHe(K)']
        logger_cfg = './osc/logging_stream_T.yaml'
    elif args.random:
        producer_funcs = [dp.f_random, dp.f_random2]
        y_labels = ['Random1', 'Random2']
        logger_cfg = './osc/logging_stream_R.yaml'
    else:
        producer_funcs = [dp.f_cpu, dp.f_ram]                     
        y_labels = ['CPU', 'RAM']
        logger_cfg = './osc/logging_stream_C.yaml'
    
    # Two queues, one for graphing one for logging
    channels = len(producer_funcs)
    graph_q = queue.Queue()
    logger_q = queue.Queue()

    # Start the data producer thread and the logger thread
    producer = Thread(target=data_producer, args=(producer_funcs, graph_q, logger_q))
    producer.start()
    logging = Thread(target=logger, args=(logger_q, y_labels, logger_cfg))
    logging.start()
    print('Start')

    # Main thread for graphing
    print('Opening Bokeh application on http://localhost:5006/')
    server = Server({'/ZI': partial(make_document, buffer_q=graph_q, labels=y_labels)})
    server.start()
    server.io_loop.add_callback(server.show, "/")
    try:
        server.io_loop.start()
    except KeyboardInterrupt:
        print('keyboard interruption')
    print('Done')
