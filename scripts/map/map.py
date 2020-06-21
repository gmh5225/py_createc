from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource

def make_document(doc):
	import numpy as np
	from bokeh.plotting import figure, show

	a = np.array([[1,2], [3, 4]])
	p = figure(x_range=(0, 2), y_range=(0, 2))

	# must give a vector of image data for image parameter
	p.image(image=[a], x=0, y=0, dw=2, dh=2, palette="Spectral11")
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