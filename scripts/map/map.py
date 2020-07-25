from bokeh.io import output_file, curdoc, show
from bokeh.models import FileInput
from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.server.server import Server
from bokeh.models.tools import PanTool, BoxZoomTool, WheelZoomTool, \
UndoTool, RedoTool, ResetTool, SaveTool, HoverTool
from bokeh.palettes import Greys256

import base64
from collections import deque
import matplotlib.pyplot as plt
import tornado.web
import numpy as np
import os
import secrets
from py_createc.Createc_pyFile import DAT_IMG
from utils.misc import Point2D, point_rot2D
from utils.image_utils import level_correction

def make_document(doc):

    def upload_data(attr, old, new):

        file = DAT_IMG(file_binary=base64.b64decode(file_input.value), file_name=file_input.filename)
        img = level_correction(file.imgs[0])
        img[img>np.mean(img)] = np.mean(img)   
        
        temp = file.nom_size.y-file.size.y if file.scan_ymode == 2 else 0
        anchor = Point2D(x=file.offset.x-file.nom_size.x/2, 
                         y=-(file.offset.y+temp))

        anchor = point_rot2D(anchor, Point2D(file.offset.x, -file.offset.y), 
                             np.deg2rad(file.rotation))

        temp_file_name = 'image' + file_input.filename + '.png'
        path = os.path.join(os.path.dirname(__file__), 'temp', temp_file_name)
        
        plt.imsave(path, img, cmap='gray')
        p.image_url([temp_file_name], x=anchor.x, y=anchor.y, anchor='top_left',
                                 w=file.size.x, h=file.size.y, 
                                 angle=file.rotation, angle_units='deg')
        path_que.append(path)
        # p.image(image=[np.flipud(img)], x=anchor.x, y=anchor.y, 
        #         dw=file.size.x, dh=file.size.y, palette="Greys256")

    file_input = FileInput(accept=".dat")
    file_input.on_change('value', upload_data)

    p = figure(match_aspect=True, tools='pan,hover,wheel_zoom', active_scroll='wheel_zoom')
    p.image_url(['image_dummy.png'], 0, 0, 0, 1)
    doc.add_root(column([p, file_input], sizing_mode='stretch_width'))

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