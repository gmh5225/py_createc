from collections import namedtuple
import numpy as np


Point2D = namedtuple('Point2D', ['x', 'y'])

def point_rot2D(target=Point2D(1,1), origin=Point2D(0,0), radians=0):

    cos_rad = np.cos(radians)
    sin_rad = np.sin(radians)
    adjusted = Point2D(x = target.x - origin.x, 
    	               y = target.y - origin.y)
    return Point2D(x = origin.x + cos_rad * adjusted.x - sin_rad * adjusted.y,
    	           y = origin.y + sin_rad * adjusted.x + cos_rad * adjusted.y)
