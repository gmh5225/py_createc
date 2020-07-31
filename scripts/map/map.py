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

def make_document(doc):

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
            img = level_correction(file.imgs[0])
            threshold = np.mean(img)+3*np.std(img)
            img[img>threshold] = threshold  
            
            temp = file.nom_size.y-file.size.y if file.scan_ymode == 2 else 0
            anchor = XY2D(x=file.offset.x-file.nom_size.x/2, 
                          y=(file.offset.y+temp))

            anchor = point_rot2D_y_inv(anchor, XY2D(x=file.offset.x, y=file.offset.y), 
                                 np.deg2rad(file.rotation))

            temp_file_name = 'image' + filename + '.png'
            path = os.path.join(os.path.dirname(__file__), 'temp', temp_file_name)
            
            plt.imsave(path, img, cmap='gray')
            p.image_url([temp_file_name], x=anchor.x, y=anchor.y, anchor='top_left',
                                     w=file.size.x, h=file.size.y, 
                                     angle=file.rotation, angle_units='deg',
                                     name = filename)
            path_que.append(path)


    rect_que = deque()

    # setup a map with y-axis inverted, dummy for initialization
    p = figure(match_aspect=True)
    p.y_range.flipped = True
    p.image_url(['image_dummy.png'], 0, 0, 0, 0)
    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
    

    # for upload file
    file_input = FileInput(accept=".dat", multiple=True)
    file_input.on_change('value', upload_data)

    # buttons for clear marks and send xy coordinates
    clear_marks_bn = Button(label="Clear Marks", button_type="success")
    clear_marks_bn.on_click(clear_callback)
    send_xy_bn = Button(label="Send XY to STM", button_type="success")
    send_xy_bn.on_click(send_xy_callback)

    # A tapping on the map will show the xy coordinates as well as mark a scanning area
    textxy_tap = TextInput(title='', value='', disabled=True)
    show_coord_cb = CustomJS(args=dict(textxy_tap=textxy_tap), code="""
                            textxy_tap.value = cb_obj.x + ',' + cb_obj.y
                            """)
    p.js_on_event(DoubleTap, show_coord_cb)
    p.on_event(DoubleTap, mark_area_callback)

    # layout includes the map and the controls below
    controls = row([file_input, textxy_tap, clear_marks_bn, send_xy_bn], 
                   sizing_mode='stretch_width')
    doc.add_root(column([p, controls], sizing_mode='stretch_width'))


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