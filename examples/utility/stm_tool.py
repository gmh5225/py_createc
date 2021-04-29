from bokeh.layouts import column, row
from bokeh.server.server import Server
from bokeh.models import Button, TextInput, Slider
from bokeh.models.formatters import FuncTickFormatter

from createc.Createc_pyCOM import CreatecWin32
import logging.config
import logging
import os
import datetime

def make_document(doc):
    def connect_stm_callback(event):
        """
        Callback to connect to the STM software
        """
        nonlocal stm
        stm = CreatecWin32()
        status_text.value = 'STM connected'
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' Connect STM'
        this_logger.info(msg)

    def ramping_bias_callback(event):
        """
        Callback for ramping bias
        """
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        status_text.value = 'Ramping bias'
        try:
            bias_target = float(bias_mV_input.value_input)
        except ValueError:
            status_text.value = 'Invalid bias'
            return
        try:
            steps = int(steps_bias_ramping.value_input)
        except ValueError:
            status_text.value = 'Invalid steps'
            return
        stm.ramp_bias_mV(bias_target, steps)
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = msg + f' Ramp bias to {bias_target} mV with steps speed {steps}'
        this_logger.info(msg)
        status_text.value = 'Ramping bias done'

    def ramping_current_callback(event):
        """
        Callback for ramping current
        """
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            return
        status_text.value = 'Ramping current'
        try:
            current_target = float(current_pA_input.value_input)
        except ValueError:
            status_text.value = 'Invalid current'
            return
        try:
            steps = int(steps_current_ramping.value_input)
        except ValueError:
            status_text.value = 'Invalid steps'
            return
        stm.ramp_current_pA(current_target, steps)
        msg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = msg + f' Ramp current to {current_target} pA with steps speed {steps}'
        this_logger.info(msg)
        status_text.value = 'Ramping current done'

    """
    Main body below
    """
    stm = None

    # A button to (re)connect to the STM software
    connect_stm_bn = Button(label="(Re)Connect to STM", button_type="success",
                            sizing_mode='stretch_width',
                            min_width=10, default_size=2)
    connect_stm_bn.on_click(connect_stm_callback)

    # show the status of the interface
    status_text = TextInput(title='', value='Ready', disabled=True,
                            sizing_mode='stretch_width',
                            min_width=10, default_size=2)

    # input for bias value in mV
    bias_mV_input = TextInput(title='Bias (mV)', value_input='10', value='10',
                              min_width=50)

    # steps for ramping bias
    steps_bias_ramping = TextInput(title='Steps', value_input='100', value='100',
                                   min_width=50)

    # button for ramping bias
    ramping_bias_bn = Button(label="Ramp Bias", button_type="success",
                             min_width=10, default_size=2)
    ramping_bias_bn.on_click(ramping_bias_callback)

    # slider not in use
    slider_bias = Slider(start=-2, end=4, value=0, step=0.01,
                         show_value=False,
                         format=FuncTickFormatter(code="return Math.pow(10, tick).toFixed(2)"))

    # input for current value in pA
    current_pA_input = TextInput(title='Current (pA)', value='10', value_input='10',
                                 min_width=50)

    # steps for ramping bias
    steps_current_ramping = TextInput(title='Steps', value_input='100', value='100',
                                      min_width=50)

    # button for ramping bias
    ramping_current_bn = Button(label="Ramp Current", button_type="success",
                                min_width=10, default_size=2)
    ramping_current_bn.on_click(ramping_current_callback)

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

    doc.add_root(column([controls_a, controls_b, controls_c], sizing_mode='stretch_both'))


this_dir = os.path.dirname(__file__)
log_config = os.path.join(this_dir, 'logger.config')
log_file = 'stm_tool.log'
logging.config.fileConfig(log_config, defaults={'logfilename': this_dir + '/' + log_file})
this_logger = logging.getLogger('this_logger')

apps = {'/': make_document}
server = Server(apps, port=5987)
server.start()
server.io_loop.add_callback(server.show, "/")
try:
    server.io_loop.start()
except KeyboardInterrupt:
    print('keyboard interruption')
