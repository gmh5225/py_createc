import numpy as np
import os

this_dir = os.path.dirname(__file__)


def test_DAT_IMG():
    """
    To test the class DAT_IMG
    """
    from createc.Createc_pyFile import DAT_IMG
    file = DAT_IMG(os.path.join(this_dir, 'A200622.081914.dat'))
    with open(os.path.join(this_dir, 'A200622.081914.npy'), 'rb') as f:
        for img in file.imgs:
            npy_img = np.load(f)
            assert img.shape == npy_img.shape
            np.testing.assert_allclose(img, npy_img)


def test_VERT_SPEC():
    """
    To test the class VERT_SPEC
    """
    from createc.Createc_pyFile import VERT_SPEC
    import pandas as pd
    from pandas._testing import assert_frame_equal

    file = VERT_SPEC(os.path.join(this_dir, 'A190824.135614.vert'))
    readin = pd.read_csv(os.path.join(this_dir, 'A190824.135614.csv'), index_col='idx')
    assert_frame_equal(readin, file.spec)

    file = VERT_SPEC(os.path.join(this_dir, 'A201222.074849.vert'))
    readin = pd.read_csv(os.path.join(this_dir, 'A201222.074849.csv'), index_col='idx')
    assert_frame_equal(readin, file.spec)


"""
    with open('A200622.081914.npy', 'wb') as f:
        for img in file.imgs:
            np.save(f, img)
"""

# test_DAT_IMG()
