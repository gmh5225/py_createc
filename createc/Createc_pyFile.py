# -*- coding: utf-8 -*-
"""
Created on Wed May  8 17:57:09 2019

@author: xuc1
"""

import io
import os
import re
import zlib
from itertools import compress

import numpy as np
import pandas as pd
import yaml

from .utils.misc import XY2D

this_dir = os.path.dirname(__file__)
cgc_file = os.path.join(this_dir, 'Createc_global_const.yaml')
with open(cgc_file, 'rt') as f:
    cgc = yaml.safe_load(f.read())


class GENERIC_FILE:
    """
    Generic file class, common for .dat, .vert files etc.

    Returns
    -------
    generic_file : GENERIC_FILE
    """

    def __init__(self, file_path=None, file_binary=None, file_name=None):
        self.meta = dict()

        if file_path is not None:
            self.fp = file_path
            _, self.fn = os.path.split(self.fp)
            self._meta_binary, self._data_binary = self._read_binary()
        else:
            self.fn = file_name
            self._meta_binary = file_binary[:int(cgc['g_file_data_bin_offset'])]
            self._data_binary = file_binary[int(cgc['g_file_data_bin_offset']):]

        self._bin2meta_dict()
        self._extracted_meta()

    def _read_binary(self):
        """
        Open file in raw binary format

        Returns
        -------
        _meta_binary : bin
            meta data in binary
        _data_binary : bin
            data in binary

        """

        with open(self.fp, 'rb') as f:
            _binary = f.read()

        return _binary[:cgc['g_file_data_bin_offset']], _binary[cgc['g_file_data_bin_offset']:]

    def _bin2meta_dict(self):
        """
        Convert meta binary to meta info using ansi encoding, filling out the meta dictionary
        Here ansi means Windows-1252 extended ascii code page CP-1252

        Returns
        -------
        None : None
        """

        meta_list = self._meta_binary.decode('cp1252', errors='ignore').split('\n')
        self.meta['file_version'] = meta_list[0]
        for line in meta_list:
            temp = line.split('=')
            if len(temp) == 2:
                keywords = temp[0].split(' / ')
                keywords = [kw.strip().lower() for kw in keywords]
                for kw in keywords:
                    self.meta[kw] = temp[1][:-1]

    def _extracted_meta(self):
        """
        Assign meta data to easily readable properties.
        One can expand these at will, one may use the method meta_key() to see what keys are available

        Returns
        -------
        None : None
            It just populates all the self.properties
        """
        self.file_version = self.meta['file_version']
        self.file_version = ''.join(e for e in self.file_version if e.isalnum())
        self.xPixel = int(self.meta['num.x'])
        self.yPixel = int(self.meta['num.y'])
        self.channels = int(self.meta['channels'])
        self.ch_zoff = float(self.meta['chmodezoff'])
        self.ch_bias = float(self.meta['chmodebias[mv]'])
        self.chmode = int(self.meta['chmode'])
        self.rotation = float(self.meta['rotation'])
        self.ddeltaX = int(self.meta['dx_div_ddelta-x'])
        self.deltaX_dac = int(self.meta['delta x'])
        self.channels_code = self.meta['channelselectval']
        self.scan_ymode = int(self.meta['scanymode'])
        self.xPiezoConst = float(self.meta['xpiezoconst'])
        self.yPiezoConst = float(self.meta['ypiezoconst'])
        self.zPiezoConst = float(self.meta['zpiezoconst'])
        self.bias = float(self.meta['biasvoltage'])
        self.current = float(self.meta['fblogiset'])

    def _spec_meta(self, spec_meta: str, index_header: str, vz_header: str, spec_headers: str):
        """
        Extract the spec meta data from the file, it includes Number of spec pts, X_position, Y_position and Channel code.

        Parameters
        ----------
        pos : int
            line position number in the file
        index_header : str
            which is e.g. 'idx'
        vz_header : list[str]
            which is e.g. ['V', 'Z']
        spec_headers : list[str]
            see Createc_global_const

        Returns
        -------
        None : None
            It populates: self.spec_total_pt, self.spec_pos_x, self.spec_pos_y, self.spec_channel_code, self.spec_headers
        """
        result = re.findall(r'(\d+)', spec_meta)
        self.spec_total_pt = int(result[0])
        self.spec_pos_x = int(result[1])
        self.spec_pos_y = int(result[2])
        self.spec_channel_code = int(result[3])
        try:
            self.spec_out_channel_count = 'v' + result[6]
        except IndexError:
            self.spec_out_channel_count = 'v2'  # dummy
        self._filter = [b == '1' for b in bin(self.spec_channel_code)[2:].rjust(len(cgc[spec_headers]))[::-1]]
        self.spec_headers = cgc[index_header] + \
                            cgc[vz_header][self.file_version][self.spec_out_channel_count] + \
                            list(compress(cgc[spec_headers][self.file_version], self._filter))

    def meta_keys(self):
        """
        Print all available keys in meta

        Returns
        -------
        None : None
        """

        return [k for k in self.meta]

    @property
    def offset(self):
        """
        Return offset relatvie to the whole range in angstrom in the format of namedtuple (x, y)

        Returns
        -------
        offset : XY2D
        """
        x_offset = np.float(self.meta['scanrotoffx'])
        y_offset = np.float(self.meta['scanrotoffy'])

        # x_piezo_const = np.float(self.meta['xpiezoconst'])
        # y_piezo_const = np.float(self.meta['ypiezoconst'])

        x_offset = -x_offset * cgc['g_XY_volt'] * self.xPiezoConst / 2 ** cgc['g_XY_bits']
        y_offset = -y_offset * cgc['g_XY_volt'] * self.yPiezoConst / 2 ** cgc['g_XY_bits']

        # Offset = namedtuple('Offset', ['y', 'x'])
        return XY2D(y=y_offset, x=x_offset)

    @property
    def size(self):
        """
        Return the true size of image in angstrom in namedtuple (x, y)

        Returns
        -------
        size : XY2D
        """
        x = float(self.meta['length x[a]']) * self.img_pixels.x / self.xPixel
        y = float(self.meta['length y[a]']) * self.img_pixels.y / self.yPixel
        # Size = namedtuple('Size', ['y', 'x'])
        return XY2D(y=y, x=x)

    @property
    def nom_size(self):
        """
        Return the nominal size of image in angstrom in namedtuple (x, y) assuming no pre-termination while scanning.

        Returns
        -------
        nom_size : XY2D
        """
        # Size = namedtuple('Size', ['y', 'x'])
        return XY2D(y=float(self.meta['length y[a]']),
                    x=float(self.meta['length x[a]']))

    @property
    def datetime(self):
        """
        Return datetime objext of the file using the file name

        Returns
        -------
        datatime : datatime.datetime
        """
        import textwrap, datetime
        temp = textwrap.wrap(''.join(filter(str.isdigit, self.fn)), 2)
        temp = [int(s) for s in temp]
        temp[0] += cgc['g_file_year_pre']
        return datetime.datetime(*temp)

    @property
    def timestamp(self):
        """
        Same as datetime, but it converts to seconds since 1970, 1, 1.

        Returns
        -------
        timestamp : datetime.timestamp
        """
        return self.datetime.timestamp()


class VERT_SPEC(GENERIC_FILE):
    """
    Read the .vert file and generate useful and managable stuff

    Parameters
    ----------
    file_path : str
        Full file path

    Returns
    -------
    vert_spec : VERT_SPEC
    """

    def __init__(self, file_path=None, file_binary=None, file_name=None):
        super().__init__(file_path, file_binary, file_name)

        spec_data = self._data_binary.decode('cp1252', errors='ignore')
        _, spec_meta, spec_f_obj = spec_data.split('\n', maxsplit=2)

        super()._spec_meta(spec_meta=spec_meta,
                           index_header='g_file_spec_index_header',
                           vz_header='g_file_spec_vz_header',
                           spec_headers='g_file_spec_headers')
        # f_obj = io.StringIO('\n'.join(self._line_list[cgc['g_file_spec_skip_rows'][self.file_version]:]))
        self.spec = pd.read_csv(filepath_or_buffer=io.StringIO(spec_f_obj), sep=cgc['g_file_spec_delimiter'],
                                header=None,
                                names=self.spec_headers,
                                index_col=cgc['g_file_spec_index_header'],
                                engine='python',
                                usecols=range(len(self.spec_headers)))


class DAT_IMG(GENERIC_FILE):
    """
    Read .dat file and generate meta data and images as numpy arrays.

    There are two options for input:

    option 1: one arg, i.e. the full path to the .dat file

    option 2: two named args

    a. the binary content of the file together

    b. the file_name as a string

    Parameters
    ----------
    file_path : str
        the full path to the .dat file
    file_binary : bin
        the binary content of the file together
    file_name : str
        the file_name as a string

    Returns
    -------
    dat_img : DAT_IMG
        dat_file_object with meta data and image numpy arrays.
        Meta data is a dict, one can expand the dict at will.
        Images are a list of numpy arrays.
    """

    def __init__(self, file_path=None, file_binary=None, file_name=None):
        super().__init__(file_path, file_binary, file_name)
        self.img_array_list = []
        self._read_img()

        # imgs are numpy arrays, with rows with only zeros cropped off
        self.imgs = [self._crop_img(arr) for arr in self.img_array_list]
        # assert(len(set(img.shape for img in self.imgs)) <= 1)
        # Pixels = namedtuple('Pixels', ['y', 'x'])
        self.img_pixels = XY2D(y=self.imgs[0].shape[0],
                               x=self.imgs[0].shape[1])  # size in (y, x)

    def _read_img(self):
        """
        Convert img binary to numpy array's, filling out the img_array_list.
        The image was compressed using zlib. So here they are decompressed.
        prerequisite: self.xPixel, self.yPixel, self.channels

        Returns
        -------
        None : None
        """
        try:
            # if it is compressed data, then decompress it
            decompressed_data = zlib.decompress(self._data_binary)
        except zlib.error:
            # else if it is not compressed, then do nothing
            decompressed_data = self._data_binary
        img_array = np.frombuffer(decompressed_data, np.dtype(cgc['g_file_dat_img_pixel_data_npdtype']))
        img_array = np.reshape(img_array[1: self.xPixel * self.yPixel * self.channels + 1],
                               (self.channels * self.yPixel, self.xPixel))
        for i in range(self.channels):
            self.img_array_list.append(img_array[self.yPixel * i:self.yPixel * (i + 1)])

    @staticmethod
    def _crop_img(arr):
        """
        Crop an image, by removing all rows which contain only zeros.

        Parameters
        ----------
        arr : numpy array
            Individual image

        Returns
        -------
        arr : numpy array
            Cropped image
        """
        return arr[~np.all(arr == 0, axis=1)]


class GRID_SPEC:
    """
    Read .gridspec file

    Parameters
    ----------
    file_path : str
        The file path to the .specgrid file
    """
    def __init__(self, file_path):

        self.fp = file_path
        _, self.fn = os.path.split(self.fp)
        # self.DAT_IMG = DAT_IMG(file_path + ".dat")

        with open(file_path, "rb") as file:
            b = np.fromfile(file, dtype=np.float32)

        a = b[:256].view(np.uint32)

        self.version = a[0]
        self.nx = a[1]
        self.ny = a[2]
        self.dx = a[3]
        self.dy = a[4]
        self.specxgrid = a[5]
        self.specygrid = a[6]
        self.vertpoints = a[7]
        self.vertmandelay = a[8]
        self.vertmangain = a[9]
        self.biasvoltage = b[10]
        self.tunnelcurrent = b[11]
        self.imagedatasize = a[12]
        self.specgriddatasize = a[13]
        self.specgridchan = a[14]
        self.specgridchannelselectval = a[15]
        self.specgriddatasize64 = np.int64(a[17])
        self.specgriddatasize64 = (self.specgriddatasize64 << 32) + a[16]
        self.xstart = a[18]
        self.xend = a[19]
        self.ystart = a[20]
        self.yend = a[21]
        self.specgridchannelselectval2 = a[22]
        self.specgridnx = a[23]
        self.specgridny = a[24]
        self.specgriddx = a[25]
        self.specgriddy = a[26]
        self.specgridcenterx = a[27]
        self.specgridcentery = a[28]

        self.count3 = self.vertpoints * 3

        self.specvz = b[256: 256 + self.count3]
        self.specvz3 = self.specvz.reshape(self.vertpoints, 3)
        self.data = b[256 + self.count3:]

        try:
            self.a, self.b = int(self.nx / self.specgriddx), int(self.ny / self.specgriddy)
            self.specdata = self.data.reshape(self.a, self.b, len(self.specvz3),
                                              int(len(self.data) / self.a / self.b / len(self.specvz3)))
        except ValueError:
            self.a, self.b = self.xend, self.yend
            self.specdata = self.data.reshape(self.a, self.b, len(self.specvz3),
                                              int(len(self.data) / self.a / self.b / len(self.specvz3)))

        self.cube_array = self.specdata[:, :, :, 1].T

        _, self.xpix, self.ypix = self.cube_array.shape
