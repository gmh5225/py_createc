from collections import namedtuple
import numpy as np


XY2D = namedtuple('XY2D', ['x', 'y'])

def point_rot2D(target=XY2D(1,1), origin=XY2D(0,0), radians=0):

    cos_rad = np.cos(radians)
    sin_rad = np.sin(radians)
    adjusted = XY2D(x = target.x - origin.x, 
    	               y = target.y - origin.y)
    return XY2D(x = origin.x + cos_rad * adjusted.x - sin_rad * adjusted.y,
    	           y = origin.y + sin_rad * adjusted.x + cos_rad * adjusted.y)

def point_rot2D_y_inv(target=XY2D(1,1), origin=XY2D(0,0), radians=0):

    result = point_rot2D(target=XY2D(x=target.x, y=-target.y), 
    	                 origin=XY2D(x=origin.x, y=-origin.y),
    	                 radians=radians)
    return XY2D(x=result.x, y=-result.y)