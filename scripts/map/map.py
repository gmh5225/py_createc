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
from utils.misc import XY2D, point_rot2D
from utils.image_utils import level_correction

def make_document(doc):

    def tap_callback(event):
        x, y = textxy.value.split(',')
        x = float(x)
        y = float(y)
        x0 = x + np.sin(np.deg2rad(stm.angle)) * stm.nom_size.y / 2
        y0 = y - np.cos(np.deg2rad(stm.angle)) * stm.nom_size.y / 2

        plot = p.rect(x=x0, y=y0, width=stm.nom_size.x, height=stm.nom_size.y, 
                      angle=stm.angle, angle_units='deg',
                      fill_alpha=0, line_color='green')
        rect_que.append(plot)

        # print(f'x={x}, y={y}')
        # print(f'x0={x0}, y0={y0}')
        # print(f'size.x={stm.nom_size.x}, size.y={stm.nom_size.y}')

    def clear_callback(event):
        while len(rect_que) > 0:
            temp = rect_que.pop()
            temp.visible = False
        print('cleared')

    def upload_data(attr, old, new):

        file = DAT_IMG(file_binary=base64.b64decode(file_input.value), file_name=file_input.filename)
        img = level_correction(file.imgs[0])
        threshold = np.mean(img)+3*np.std(img)
        img[img>threshold] = threshold  
        
        temp = file.nom_size.y-file.size.y if file.scan_ymode == 2 else 0
        anchor = XY2D(x=file.offset.x-file.nom_size.x/2, 
                      y=-(file.offset.y+temp))

        anchor = point_rot2D(anchor, XY2D(x=file.offset.x, y=-file.offset.y), 
                             np.deg2rad(file.rotation))

        temp_file_name = 'image' + file_input.filename + '.png'
        path = os.path.join(os.path.dirname(__file__), 'temp', temp_file_name)
        
        plt.imsave(path, img, cmap='gray')
        p.image_url([temp_file_name], x=anchor.x, y=anchor.y, anchor='top_left',
                                 w=file.size.x, h=file.size.y, 
                                 angle=file.rotation, angle_units='deg')
        path_que.append(path)


    rect_que = deque()

    p = figure(match_aspect=True)
    p.image_url(['image_dummy.png'], 0, 0, 0, 1) 
       
    textxy = TextInput(title='', value='',disabled=True)
    callback_hover = CustomJS(args=dict(textxy=textxy), code="""
        textxy.value = cb_data['geometry'].x + ',' + cb_data['geometry'].y;
        console.log(textxy.value);
        """)

    file_input = FileInput(accept=".dat")
    file_input.on_change('value', upload_data)

    button = Button(label="Clear", button_type="success")
    button.on_click(clear_callback)

    hover_tool = HoverTool(callback=callback_hover, tooltips=None)
    p.add_tools(hover_tool)
    taptool = p.select(type=TapTool)
    p.on_event(DoubleTap, tap_callback)
    p.toolbar.active_scroll = p.select_one(WheelZoomTool)
    p.add_tools(UndoTool())
    controls = row([textxy, button, file_input], sizing_mode='stretch_width')
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