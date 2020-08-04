from bokeh.io import output_file, curdoc, show
from bokeh.models import FileInput
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.server.server import Server
from bokeh.models.tools import PanTool, BoxZoomTool, WheelZoomTool, \
UndoTool, RedoTool, ResetTool, SaveTool, HoverTool
from bokeh.palettes import Greys256
from bokeh.models import Button, HoverTool, TapTool, TextInput, CustomJS
from bokeh.events import Tap, DoubleTap

import base64
from collections import deque
import matplotlib.pyplot as plt
import tornado.web
import numpy as np
import os
import secrets
from py_createc.Createc_pyFile import DAT_IMG
from py_createc.Createc_pyCOM import CreatecWin32
from utils.misc import XY2D, point_rot2D_y_inv
from utils.image_utils import level_correction

IMAGE_CHANNEL = 1 # channel number of image to show
SCAN_BOUNDARY_X = 6000 # scanner range in angstrom
SCAN_BOUNDARY_Y = 6000

def make_document(doc):

    def show_area_callback(event):
        """
        Show current STM scan area
        """
        x0 = stm.offset.x + np.sin(np.deg2rad(stm.angle)) * stm.nom_size.y / 2
        y0 = stm.offset.y + np.cos(np.deg2rad(stm.angle)) * stm.nom_size.y / 2

        plot = p.rect(x=x0, y=y0, width=stm.nom_size.x, height=stm.nom_size.y, 
                      angle=stm.angle, angle_units='deg',
                      fill_alpha=0, line_color='blue')
        rect_que.append(plot)

    def mark_area_callback(event):
        """
        Callback for Double tap to mark a new scan area in the map
        """
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

    def clear_callback(event):
        """
        Callback to clear all marks on map
        """
        while len(rect_que) > 0:
            temp = rect_que.pop()
            temp.visible = False
        print('cleared')

    def send_xy_callback(event):
        """
        Callback to send x y coordinates to STM software
        """
        assert ',' in textxy_tap.value, 'A valid coordinate string should contain a comma'
        x, y = textxy_tap.value.split(',')
        x_volt = float(x) / stm.xPiezoConst
        y_volt = float(y) / stm.yPiezoConst

        stm.client.setxyoffvolt(x_volt, y_volt)
        stm.client.setparam('RotCMode', 0)
        print('XY coordinate sent')
        print(f'x={x} y={y}')

    def upload_data(attr, old, new):
        """
        Callback to upload image to the map
        """
        for value, filename in zip(file_input.value, file_input.filename):
            file = DAT_IMG(file_binary=base64.b64decode(value), file_name=filename)
            img = level_correction(file.imgs[IMAGE_CHANNEL])
            threshold = np.mean(img)+3*np.std(img)
            img[img>threshold] = threshold  
            
            temp = file.nom_size.y-file.size.y if file.scan_ymode == 2 else 0
            anchor = XY2D(x=file.offset.x, 
                          y=(file.offset.y+temp+file.size.y/2))

            anchor = point_rot2D_y_inv(anchor, XY2D(x=file.offset.x, y=file.offset.y), 
                                 np.deg2rad(file.rotation))
            print('anchor:', anchor)
            temp_file_name = 'image' + filename + '.png'
            path = os.path.join(os.path.dirname(__file__), 'temp', temp_file_name)
            
            plt.imsave(path, img, cmap='gray')
            p.image_url([temp_file_name], x=anchor.x, y=anchor.y, anchor='center',
                                     w=file.size.x, h=file.size.y, 
                                     angle=file.rotation, 
                                     angle_units='deg',
                                     name = filename)
            path_que.append(path)


    rect_que = deque()

    # setup a map with y-axis inverted, and a virtual boundary of the scanner range
    p = figure(match_aspect=True, tools=[PanTool(), UndoTool(), RedoTool(), ResetTool(), SaveTool()])
    p.y_range.flipped = True
    plot = p.rect(x=0, y=0, width=SCAN_BOUNDARY_X, height=SCAN_BOUNDARY_Y, 
                  fill_alpha=0, line_color='gray')
	
	# add wheel zoom tool
    wheel_zoom_tool = WheelZoomTool(zoom_on_axis=False)
    p.add_tools(wheel_zoom_tool)
    p.toolbar.active_scroll = wheel_zoom_tool
    
    # for upload file
    file_input = FileInput(accept=".dat", multiple=True)
    file_input.on_change('value', upload_data)

    # buttons for clear marks and send xy coordinates
    clear_marks_bn = Button(label="Clear Marks", button_type="success")
    clear_marks_bn.on_click(clear_callback)
    send_xy_bn = Button(label="Send XY to STM", button_type="success")
    send_xy_bn.on_click(send_xy_callback)
    show_stm_area_bn = Button(label="Show STM Location", button_type="success")
    show_stm_area_bn.on_click(show_area_callback)


    # A tapping on the map will show the xy coordinates as well as mark a scanning area
    textxy_tap = TextInput(title='', value='', disabled=True)
    textxy_tap_show = TextInput(title='', value='', disabled=True)
    show_coord_cb = CustomJS(args=dict(textxy_tap=textxy_tap, textxy_tap_show=textxy_tap_show), code="""
                            var x=cb_obj.x;
                            var y=cb_obj.y;
                            textxy_tap.value = x + ',' + y;
                            textxy_tap_show.value = 'x='+ x.toFixed(2) + ', y=' + y.toFixed(2);
                            """)
    p.js_on_event(DoubleTap, show_coord_cb)
    p.on_event(DoubleTap, mark_area_callback)

    textxy_hover = TextInput(title='', value='', disabled=True)
    hover_coord_cb = CustomJS(args=dict(textxy_hover=textxy_hover), code="""
                              var x=cb_data['geometry'].x;
                              var y=cb_data['geometry'].y;
                              textxy_hover.value = 'x='+ x.toFixed(2) + ', y=' + y.toFixed(2);
                              """)
    p.add_tools(HoverTool(callback=hover_coord_cb, tooltips=None))
    p.toolbar_location = None
    # layout includes the map and the controls below
    controls_1 = row([file_input, show_stm_area_bn, textxy_tap_show], sizing_mode='stretch_width')
    controls_2 = row([textxy_hover, clear_marks_bn, send_xy_bn], sizing_mode='stretch_width')
    doc.add_root(column([p, controls_1, controls_2], sizing_mode='stretch_both'))


stm = CreatecWin32()
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