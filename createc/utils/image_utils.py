import numpy as np

def level_correction(Y):
    """
    Do level correction for an input image Y in the format of numpy 2d array
    returns the result image in numpy 2d array
    """
    m, n = Y.shape
    assert m >=2 and n >= 2
    X1, X2 = np.mgrid[:m, :n]
    X = np.hstack((np.reshape(X1, (m*n, 1)), np.reshape(X2, (m*n, 1))))
    X = np.hstack((np.ones((m*n, 1)), X))
    YY = np.reshape(Y, (m*n, 1))
    theta = np.dot(np.dot(np.linalg.pinv(np.dot(X.transpose(), X)), X.transpose()), YY)
    plane = np.reshape(np.dot(X, theta), (m, n))
    return Y-plane
