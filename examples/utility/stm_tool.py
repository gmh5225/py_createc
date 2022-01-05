from bokeh.layouts import column, row
from bokeh.server.server import Server
from bokeh.models import Button, TextInput, Slider, Select
from bokeh.models.formatters import FuncTickFormatter

from createc.Createc_pyCOM import CreatecWin32
import logging.config
import logging
import os
import datetime
from functools import partial


def make_document(doc):
    """
    The make doc func for bokeh

    """

    def connect_stm_callback(event):
        """
        Callback to connect to the STM software
        """
        status_text.value = 'Connecting to STM'
        connect_stm_bn.disabled = True

        def process():
            nonlocal stm
            stm = CreatecWin32()
            status_text.value = 'STM connected'
            connect_stm_bn.disabled = False
            bias_mV_input.value = stm.bias_mV
            current_pA_input.value = stm.current_pA
            img_size_text.value = str(stm.imgX_size_bits)
            img_real_size.value = str(stm.nom_size.x)
            img_duration_text.value = str(stm.img_dDeltaX_bits)
            img_real_duration.value = str(datetime.timedelta(seconds=stm.duration))
            msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' Connect to STM'
            this_logger.info(msg)

        doc.add_next_tick_callback(process)

    def process_bias():
        try:
            bias_target = float(bias_mV_input.value)
        except ValueError:
            status_text.value = 'Invalid bias'
            ramping_bias_bn.disabled = False
            return
        try:
            steps = int(steps_bias_ramping.value)
        except ValueError:
            status_text.value = 'Invalid steps'
            ramping_bias_bn.disabled = False
            return
        stm.ramp_bias_mV(bias_target, steps)
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = msg + f' Ramp bias to {bias_target} mV with steps speed {steps}'
        this_logger.info(msg)
        status_text.value = 'Ramping bias done'
        ramping_bias_bn.disabled = False

    def preprocess_bias():
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        status_text.value = 'Ramping bias'
        ramping_bias_bn.disabled = True

    def ramping_bias_cb_bn(event):
        """
        Callback for ramping bias
        """
        preprocess_bias()
        doc.add_next_tick_callback(process_bias)

    def ramping_bias_cb_ti(attr, old, new):
        preprocess_bias()
        doc.add_next_tick_callback(process_bias)

    def process_current():
        try:
            current_target = float(current_pA_input.value)
        except ValueError:
            status_text.value = 'Invalid current'
            ramping_current_bn.disabled = False
            return
        try:
            steps = int(steps_current_ramping.value)
        except ValueError:
            status_text.value = 'Invalid steps'
            ramping_current_bn.disabled = False
            return
        stm.ramp_current_pA(current_target, steps)
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = msg + f' Ramp current to {current_target} pA with steps speed {steps}'
        this_logger.info(msg)
        status_text.value = 'Ramping current done'
        ramping_current_bn.disabled = False

    def preprocess_current():
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        status_text.value = 'Ramping current'
        ramping_current_bn.disabled = True

    def ramping_current_cb_bn(event):
        """
        Callback for ramping current
        """
        preprocess_current()
        doc.add_next_tick_callback(process_current)

    def ramping_current_cb_ti(attr, old, new):
        preprocess_current()
        doc.add_next_tick_callback(process_current)

    def img_size_select_cb(attr, old, new):
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        stm.setparam('Delta X [Dac]', int(img_size_select.value))
        status_text.value = 'Image size changed'
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' Image size changed to ' + img_size_select.value
        this_logger.info(msg)

    def img_size_change_cb(event, op):
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        old_size = stm.imgX_size_bits
        if op == 'plus1':
            new_size = old_size + 1
        elif op == 'minus1':
            new_size = old_size - 1
        elif op == 'times2':
            new_size = old_size * 2
        elif op == 'divides2':
            new_size = old_size / 2
        else:
            raise ValueError('operation is not supported')

        stm.imgX_size_bits = new_size
        new_size = stm.imgX_size_bits
        status_text.value = 'Image size changed'
        img_size_text.value = str(new_size)
        img_real_size.value = str(stm.nom_size.x)
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' Image size changed to ' + str(new_size)
        this_logger.info(msg)

    def img_speed_select_cb(attr, old, new):
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        stm.setparam('DX/DDeltaX', int(img_speed_select.value))
        status_text.value = 'Image speed changed'
        msg = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S") + ' Image speed changed to ' + img_speed_select.value
        this_logger.info(msg)

    def img_duration_change_cb(event, op):
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        old_duration = stm.img_dDeltaX_bits
        if op == 'plus1':
            new_duration = old_duration + 1
        elif op == 'minus1':
            new_duration = old_duration - 1
        elif op == 'times2':
            new_duration = old_duration * 2
        elif op == 'divides2':
            new_duration = old_duration / 2
        else:
            raise ValueError('operation is not supported')

        stm.img_dDeltaX_bits = new_duration
        new_duration = stm.img_dDeltaX_bits
        status_text.value = 'Image duration changed'
        img_duration_text.value = str(new_duration)
        img_real_duration.value = str(datetime.timedelta(seconds=stm.duration))
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' Image duration changed to ' + str(new_duration)
        this_logger.info(msg)

    """
    Main body below
    """
    stm = None

    # A button to (re)connect to the STM software
    connect_stm_bn = Button(label="(Re)Connect to STM / Refresh", button_type="success",
                            sizing_mode='stretch_width',
                            min_width=10, default_size=2)
    connect_stm_bn.on_click(connect_stm_callback)

    # show the status of the interface
    status_text = TextInput(title='', value='Ready', disabled=True,
                            sizing_mode='stretch_width',
                            min_width=10, default_size=2)

    # input for bias value in mV
    bias_mV_input = TextInput(title='Bias (mV)', value_input='10', value='10', min_width=50)
    # bias_mV_input.on_change('value', ramping_bias_cb_ti)

    # steps for ramping bias
    steps_bias_ramping = TextInput(title='Steps', value_input='40', value='40', min_width=50)

    # button for ramping bias
    ramping_bias_bn = Button(label="Ramp Bias", button_type="success",
                             min_width=10, default_size=2)
    ramping_bias_bn.on_click(ramping_bias_cb_bn)

    # slider not in use
    slider_bias = Slider(start=-2, end=4, value=0, step=0.01,
                         show_value=False,
                         format=FuncTickFormatter(code="return Math.pow(10, tick).toFixed(2)"))

    # input for current value in pA
    current_pA_input = TextInput(title='Current (pA)', value='10', value_input='10', min_width=50)
    # current_pA_input.on_change('value', ramping_current_cb_ti)

    # steps for ramping bias
    steps_current_ramping = TextInput(title='Steps', value_input='40', value='40', min_width=50)

    # button for ramping bias
    ramping_current_bn = Button(label="Ramp Current", button_type="success",
                                min_width=10, default_size=2)
    ramping_current_bn.on_click(ramping_current_cb_bn)

    # image size selection
    size_range = [str(i) for i in range(1, 64)]
    size_range = size_range + [str(2 ** i) for i in range(6, 13)]
    size_range = ['3985'] + size_range[::-1]
    img_size_select = Select(title="Image Size (bits)", value="128", options=size_range)
    img_size_select.on_change('value', img_size_select_cb)

    # show the image size in bits
    img_size_text = TextInput(title='Image Size (bits)', value='', disabled=True,
                              sizing_mode='stretch_width',
                              min_width=10, default_size=2)

    img_real_size = TextInput(title='Angstrom', value='', disabled=True,
                              sizing_mode='stretch_width',
                              min_width=10, default_size=2)

    img_size_increases1_bn = Button(label="+1", button_type="success")
    img_size_increases1_bn.on_click(partial(img_size_change_cb, op='plus1'))
    img_size_decreases1_bn = Button(label="-1", button_type="success")
    img_size_decreases1_bn.on_click(partial(img_size_change_cb, op='minus1'))
    img_size_times2_bn = Button(label="x2", button_type="success")
    img_size_times2_bn.on_click(partial(img_size_change_cb, op='times2'))
    img_size_divides2_bn = Button(label="/2", button_type="success")
    img_size_divides2_bn.on_click(partial(img_size_change_cb, op='divides2'))

    # image speed selection
    speed_range = [str(i) for i in range(1, 64)]
    speed_range = speed_range + [str(2 ** i) for i in range(6, 14)]
    speed_range = speed_range[::-1]
    img_speed_select = Select(title="Image Speed (bits)", value="128", options=speed_range)
    img_speed_select.on_change('value', img_speed_select_cb)

    # show the image duration in bits
    img_duration_text = TextInput(title='Duration (bits)', value='', disabled=True,
                                  sizing_mode='stretch_width',
                                  min_width=10, default_size=2)

    img_real_duration = TextInput(title='Time (h:m:s)', value='', disabled=True,
                                  sizing_mode='stretch_width',
                                  min_width=10, default_size=2)

    img_duration_increases1_bn = Button(label="+1", button_type="success")
    img_duration_increases1_bn.on_click(partial(img_duration_change_cb, op='plus1'))
    img_duration_decreases1_bn = Button(label="-1", button_type="success")
    img_duration_decreases1_bn.on_click(partial(img_duration_change_cb, op='minus1'))
    img_duration_times2_bn = Button(label="x2", button_type="success")
    img_duration_times2_bn.on_click(partial(img_duration_change_cb, op='times2'))
    img_duration_divides2_bn = Button(label="/2", button_type="success")
    img_duration_divides2_bn.on_click(partial(img_duration_change_cb, op='divides2'))

    # layout includes the map and the controls below
    controls_a = column([status_text, connect_stm_bn], sizing_mode='stretch_both')
    controls_b = column([row([bias_mV_input,
                              steps_bias_ramping],
                             sizing_mode='stretch_width'),
                         ramping_bias_bn],
                        sizing_mode='stretch_width')
    controls_c = column([row([current_pA_input,
                              steps_current_ramping],
                             sizing_mode='stretch_width'),
                         ramping_current_bn],
                        sizing_mode='stretch_width')
    controls_d = row([img_size_text,
                      img_real_size],
                     sizing_mode='stretch_width')
    controls_e = row([img_size_divides2_bn,
                      img_size_decreases1_bn,
                      img_size_increases1_bn,
                      img_size_times2_bn],
                     sizing_mode='stretch_width')
    controls_f = row([img_duration_text,
                      img_real_duration],
                     sizing_mode='stretch_width')
    controls_g = row([img_duration_divides2_bn,
                      img_duration_decreases1_bn,
                      img_duration_increases1_bn,
                      img_duration_times2_bn],
                     sizing_mode='stretch_width')
    doc.add_root(column([controls_a, controls_b, controls_c,
                         controls_d, controls_e, controls_f, controls_g],
                        sizing_mode='stretch_width'))


this_dir = os.path.dirname(__file__)
log_config = os.path.join(this_dir, 'logger.config')
log_file = 'stm_tool.log'
# logging.config.fileConfig(log_config, defaults={'logfilename': this_dir + '\/' + log_file})
logging.config.fileConfig(log_config, defaults={'logfilename': os.path.join(this_dir, log_file).replace('\\', '\\\\')})
this_logger = logging.getLogger('this_logger')

apps = {'/': make_document}
server = Server(apps, port=5987)
server.start()
server.io_loop.add_callback(server.show, "/")
try:
    server.io_loop.start()
except KeyboardInterrupt:
    print('keyboard interruption')
