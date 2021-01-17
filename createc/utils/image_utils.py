# -*- coding: utf-8 -*-
#


def level_correction(img):
    """
    Do level correction for an input image img in the format of numpy 2d array
    returns the result image in numpy 2d array

    Parameters
    ----------
    img : numpy.array
        An image in 2d numpy.array
    Returns
    -------
    result : numpy.array
        Level corrected image in 2d numpy.array
    """
    import numpy as np

    m, n = img.shape
    assert m >= 2 and n >= 2
    X1, X2 = np.mgrid[:m, :n]
    X = np.hstack((np.reshape(X1, (m * n, 1)), np.reshape(X2, (m * n, 1))))
    X = np.hstack((np.ones((m * n, 1)), X))
    YY = np.reshape(img, (m * n, 1))
    theta = np.dot(np.dot(np.linalg.pinv(np.dot(X.transpose(), X)), X.transpose()), YY)
    plane = np.reshape(np.dot(X, theta), (m, n))
    return img - plane
