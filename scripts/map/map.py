from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource
import py_createc.Createc_pyFile as cpf

def make_document(doc):
    import numpy as np
    from bokeh.plotting import figure, show

    img = cpf.DAT_IMG('./data/A200306.161609.dat')
    a = np.array([[1,2], [3, 4]])
    p = figure(x_range=(0, 2), y_range=(0, 2))

    # must give a vector of image data for image parameter
    p.image(image=[img.imgs[0]], x=0, y=0, dw=2, dh=2, palette="Greys256")
    doc.add_root(p)

apps = {'/': make_document}

server = Server(apps)
server.start()
server.io_loop.add_callback(server.show, "/")
try:
    server.io_loop.start()
except KeyboardInterrupt:
    print('keyboard interruption')
print('Done')