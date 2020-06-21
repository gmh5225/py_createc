from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource
from bokeh.layouts import column
import py_createc.Createc_pyFile as cpf



def make_document(doc):
    import numpy as np
    from bokeh.plotting import figure, show

    img = cpf.DAT_IMG('./data/A200619.213320.dat')
    p = figure(match_aspect=True)

    # must give a vector of image data for image parameter
    p.image(image=[img.imgs[0]], x=0, y=0, dw=img.get_size().x, dh=img.get_size().y, palette="Greys256")
    doc.add_root(column(p, sizing_mode='stretch_both'))

apps = {'/': make_document}

server = Server(apps)
server.start()
server.io_loop.add_callback(server.show, "/")
try:
    server.io_loop.start()
except KeyboardInterrupt:
    print('keyboard interruption')
print('Done')