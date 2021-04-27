from bokeh.io import output_file, curdoc, show
from bokeh.models import FileInput, ColumnDataSource, CustomJSHover
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.server.server import Server
from bokeh.models.tools import PanTool, BoxZoomTool, WheelZoomTool, \
UndoTool, RedoTool, ResetTool, SaveTool, HoverTool
from bokeh.palettes import Greys256
from bokeh.models import Button, HoverTool, TapTool, TextInput, CustomJS, Select
from bokeh.events import Tap, DoubleTap

import base64
from collections import deque, namedtuple
import matplotlib.pyplot as plt
import tornado.web
import numpy as np
import os
import secrets
from createc.Createc_pyFile import DAT_IMG
from createc.Createc_pyCOM import CreatecWin32
from createc.utils.misc import XY2D, point_rot2D_y_inv
from createc.utils.image_utils import level_correction


SCAN_BOUNDARY_X = 3000 # scanner range in angstrom
SCAN_BOUNDARY_Y = 3000
NUM_SIGMA = 3 # remove any outlier pixels of an image beyond a defined several sigmas
MAX_CH = 8 # maxium channel number, temp variable
FILE_TUPLE = namedtuple('FILE_TUPLE', ['file', 'filename'])

def make_document(doc):

    def show_area_callback(event):
        """
        Show current STM scan area
        """
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            send_xy_bn.disabled = True
            show_stm_area_bn.disabled = True
            return

        x0 = stm.offset.x + np.sin(np.deg2rad(stm.angle)) * stm.nom_size.y / 2
        y0 = stm.offset.y + np.cos(np.deg2rad(stm.angle)) * stm.nom_size.y / 2

        plot = p.rect(x=x0, y=y0, width=stm.nom_size.x, height=stm.nom_size.y, 
                      angle=stm.angle, angle_units='deg',
                      fill_alpha=0, line_color='blue')
        rect_que.append(plot)
        textxy_show.value = f'x={stm.offset.x:.2f}, y={stm.offset.y:.2f}'
        textxy_tap.value = f'{stm.offset.x:.2f},{stm.offset.y:.2f}'
        status_text.value = 'STM location shown'

    def mark_area_callback(event):
        """
        Callback for Double tap to mark a new scan area in the map
        """
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            send_xy_bn.disabled = True
            show_stm_area_bn.disabled = True
            return

        assert ',' in textxy_tap.value, 'A valid coordinate string should contain a comma'
        x, y = textxy_tap.value.split(',')
        x = float(x)
        y = float(y)
        x0 = x + np.sin(np.deg2rad(stm.angle)) * stm.nom_size.y / 2
        y0 = y + np.cos(np.deg2rad(stm.angle)) * stm.nom_size.y / 2

        plot = p.rect(x=x0, y=y0, width=stm.nom_size.x, height=stm.nom_size.y, 
                      angle=stm.angle, angle_units='deg',
                      fill_alpha=0, line_color='green')
        rect_que.append(plot)
        status_text.value = 'Area selected'

    def clear_callback(event):
        """
        Callback to clear all marks on map
        """
        while len(rect_que) > 0:
            temp = rect_que.pop()
            temp.visible = False
        status_text.value = 'Marks cleared'

    def send_xy_callback(event):
        """
        Callback to send x y coordinates to STM software
        """
        if stm is None or not stm.is_active():
            status_text.value = 'No STM is connected'
            send_xy_bn.disabled = True
            show_stm_area_bn.disabled = True
            return
        if textxy_tap.value == '':
            status_text.value = 'Coordinate invalid'
            return
        if ',' not in textxy_tap.value:
            status_text.value = 'Coordinate invalid'
            return            
        # assert ',' in textxy_tap.value, 'A valid coordinate string should contain a comma'
        x, y = textxy_tap.value.split(',')
        x_volt = float(x) / stm.xPiezoConst
        y_volt = float(y) / stm.yPiezoConst

        stm.client.setxyoffvolt(x_volt, y_volt)
        stm.client.setparam('RotCMode', 0)
        status_text.value = 'XY coordinate sent'

    def plot_img():
        """
        The main function to plot image onto the frame
        """

        if file_holder is None:
            return
        file = file_holder.file
        filename = file_holder.filename

        channel = int(ch_select.value[-1])
        if channel >= file.channels:
            channel = file.channels-1
            ch_select.value = f'{ch_select.value[:-1]}{channel}'

        img = file.imgs[channel]
        # img = level_correction(file.imgs[channel])

        # remove any outlier
        threshold = np.mean(img)+NUM_SIGMA*np.std(img)
        img[img>threshold] = threshold
        threshold = np.mean(img)-NUM_SIGMA*np.std(img)
        img[img<threshold] = threshold

        temp = file.nom_size.y-file.size.y if file.scan_ymode == 2 else 0
        anchor = XY2D(x=file.offset.x, 
                      y=(file.offset.y+temp+file.size.y/2))

        anchor = point_rot2D_y_inv(anchor, XY2D(x=file.offset.x, y=file.offset.y), 
                             np.deg2rad(file.rotation))
        # print('offset:', file.offset)
        # print('angle:', file.rotation)
        if int(file.rotation*100) not in [0, 9000, -9000, 18000, -18000]:
            temp_file_name = f'image{filename}_{channel}.png'
            path = os.path.join(os.path.dirname(__file__), 'temp', temp_file_name)
            
            plt.imsave(path, img, cmap='gray')
            p.image_url([temp_file_name], x=anchor.x, y=anchor.y, anchor='center',
                                     w=file.size.x, h=file.size.y, 
                                     angle=file.rotation, 
                                     angle_units='deg',
                                     name = filename)
            path_que.append(path)
            return None

        elif int(file.rotation*100) == 0:
            anchor = XY2D(x=anchor.x-file.size.x/2, y=anchor.y+file.size.y/2)
            width = file.size.x
            height = file.size.y
        elif int(file.rotation*100) == 9000:
            img = img.swapaxes(-2,-1)[...,::-1,:]
            anchor = XY2D(x=anchor.x-file.size.y/2, y=anchor.y+file.size.x/2)
            width = file.size.y
            height = file.size.x
        elif int(file.rotation*100) == -9000:
            img = img.swapaxes(-2,-1)[...,::-1]
            anchor = XY2D(x=anchor.x-file.size.y/2, y=anchor.y+file.size.x/2)
            width = file.size.y
            height = file.size.x
        else:
            img = img[...,::-1,::-1]
            anchor = XY2D(x=anchor.x-file.size.x/2, y=anchor.y+file.size.y/2)
            width = file.size.x
            height = file.size.y
        p.image(image=[np.flipud(img)], x=anchor.x, y=anchor.y, 
                dw=width, dh=height, palette="Greys256")

    def file_input_callback(attr, old, new):
        """
        Callback to upload file
        """
        for value, filename in zip(file_input.value, file_input.filename):
            file = DAT_IMG(file_binary=base64.b64decode(value), file_name=filename)
            nonlocal file_holder
            file_holder = FILE_TUPLE(file=file, filename=filename)
            plot_img()
        status_text.value = 'File uploaded'

    def channel_selection_callback(attr, old, new):
        """
        Callback to change channel of image to show
        """
        plot_img()
        status_text.value = 'Channel changed'

    def connect_stm_callback(event):
        """
        Callback to connect to the STM software
        """
        nonlocal stm
        stm = CreatecWin32()
        send_xy_bn.disabled=False
        show_stm_area_bn.disabled=False
        status_text.value = 'STM connected'
        

    """
    Main body below
    """
    rect_que = deque()
    file_holder = None
    stm = None
    
    # setup a map with y-axis inverted, and a virtual boundary of the scanner range
    p = figure(match_aspect=True, tools=[PanTool(), UndoTool(), RedoTool(), ResetTool(), SaveTool()])
    p.y_range.flipped = True
    # plot = p.rect(x=0, y=0, width=SCAN_BOUNDARY_X, height=SCAN_BOUNDARY_Y, 
    #               fill_alpha=0, line_color='gray', name='none')
    p.line([-SCAN_BOUNDARY_X, -SCAN_BOUNDARY_X, SCAN_BOUNDARY_X, SCAN_BOUNDARY_X, -SCAN_BOUNDARY_X], 
           [SCAN_BOUNDARY_Y, -SCAN_BOUNDARY_Y, -SCAN_BOUNDARY_Y, SCAN_BOUNDARY_Y, SCAN_BOUNDARY_Y])

    # Add the wheel zoom tool
    wheel_zoom_tool = WheelZoomTool(zoom_on_axis=False)
    p.add_tools(wheel_zoom_tool)
    p.toolbar.active_scroll = wheel_zoom_tool
    
    # Button for uploading file
    file_input = FileInput(accept=".dat", multiple=True)
    file_input.on_change('value', file_input_callback)

    # buttons for clearing marks and sending xy coordinates
    clear_marks_bn = Button(label="Clear Marks", button_type="success")
    clear_marks_bn.on_click(clear_callback)
    send_xy_bn = Button(label="Send XY to STM", button_type="success", disabled=True)
    send_xy_bn.on_click(send_xy_callback)
    show_stm_area_bn = Button(label="Show STM Location", button_type="success", disabled=True)
    show_stm_area_bn.on_click(show_area_callback)

    # A double-tapping on the map will show the xy coordinates as well as mark a scanning area
    textxy_tap = TextInput(title='', value='', disabled=True)
    textxy_show = TextInput(title='', value='', disabled=True)
    show_coord_cb = CustomJS(args=dict(textxy_tap=textxy_tap, textxy_show=textxy_show), code="""
                            var x=cb_obj.x;
                            var y=cb_obj.y;
                            textxy_tap.value = x.toFixed(2) + ',' + y.toFixed(2);
                            textxy_show.value = 'x='+ x.toFixed(2) + ', y=' + y.toFixed(2);
                            """)
    p.js_on_event(DoubleTap, show_coord_cb)
    p.on_event(DoubleTap, mark_area_callback)
    
    # Show coordinates when hovering over the canvas
    textxy_hover = TextInput(title='', value='', disabled=True)
    hover_coord_cb = CustomJS(args=dict(textxy_hover=textxy_hover), code="""
                              var x=cb_data['geometry'].x;
                              var y=cb_data['geometry'].y;
                              textxy_hover.value = 'x='+ x.toFixed(2) + ', y=' + y.toFixed(2);
                              """)
    p.add_tools(HoverTool(callback=hover_coord_cb, tooltips=None))

    # Hide the toolbar
    p.toolbar_location = None
    
    # Dropdown menu to select which channel to show
    ch_select = Select(title="", value="ch0", options=[f'ch{number}' for number in range(MAX_CH)])
    ch_select.on_change('value', channel_selection_callback)
    
    # A button to (re)connect to the STM software
    connect_stm_bn = Button(label="(Re)Connect to STM", button_type="success")
    connect_stm_bn.on_click(connect_stm_callback)

    # show the status of the interface
    status_text = TextInput(title='', value='Ready', disabled=True)
    # layout includes the map and the controls below
    controls_1 = row([file_input, ch_select, textxy_show], sizing_mode='stretch_width')
    controls_2 = row([textxy_hover, clear_marks_bn, status_text], sizing_mode='stretch_width')
    controls_3 = row([connect_stm_bn, show_stm_area_bn, send_xy_bn], sizing_mode='stretch_width')
    doc.add_root(column([p, controls_1, controls_2, controls_3], sizing_mode='stretch_both'))


path_que = deque()
apps = {'/': make_document}
extra_patterns = [(r"/(image(.*))", tornado.web.StaticFileHandler, 
                  {"path": os.path.join(os.path.dirname(__file__), 'temp')}),
                  (r"/(favicon.ico)", tornado.web.StaticFileHandler, 
                  {"path": os.path.join(os.path.dirname(__file__), 'temp')})]
server = Server(apps, extra_patterns=extra_patterns)
server.start()
server.io_loop.add_callback(server.show, "/")
try:
    server.io_loop.start()
except KeyboardInterrupt:
    print('keyboard interruption')
finally:
    while len(path_que):
        file = path_que.pop()
        if os.path.isfile(file):
            os.remove(file)
    print('Done')
