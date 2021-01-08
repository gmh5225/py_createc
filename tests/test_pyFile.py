import numpy as np


def test_DAT_IMG():

    """
    To test the class DAT_IMG
    """
    from createc.Createc_pyFile import DAT_IMG
    
    file = DAT_IMG('./A200622.081914.dat')
    with open('A200622.081914.npy', 'rb') as f:
        for img in file.imgs:
            npy_img = np.load(f)
            assert img.shape == npy_img.shape
            np.testing.assert_allclose(img, npy_img)
"""
    with open('A200622.081914.npy', 'wb') as f:
        for img in file.imgs:
            np.save(f, img)
"""

test_DAT_IMG()