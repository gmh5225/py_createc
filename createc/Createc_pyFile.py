# -*- coding: utf-8 -*-
"""
Created on Wed May  8 17:57:09 2019

@author: xuc1
"""

import zlib
import numpy as np
import yaml
import re
import pandas as pd
from itertools import compress
import io
import os
from collections import namedtuple
from .utils.misc import XY2D

dir = os.path.dirname(__file__)
cgc_file = os.path.join(dir, 'Createc_global_const.yaml')
with open(cgc_file, 'rt') as f:
    cgc = yaml.safe_load(f.read())

class GENERIC_FILE:
    """
    Generic file class, common for .dat, .vert files etc.
    input: full file_path.
    output: generic file obj.
    """
    def __init__(self, file_path):
        self.fp = file_path
        self.meta = dict()

    def _read_binary(self):
        """
        Open file in raw binary format
        input: self
        output: _binary, which is a binary stream of the entire file
        
        """
        with open(self.fp, 'rb') as f:
            _binary = f.read()
            return _binary
 
    def _bin2meta_dict(self, start=0, end=cgc['g_file_meta_binary_len']):
        """
        Convert meta binary to meta info using ansi encoding, filling out the meta dictionary
        Here ansi means Windows-1252 extended ascii code page CP-1252
        input: self, start position and end position
        output: None, it just fills the _meta dict
        prerequisite: _binary stream
        """
        meta_list = self._binary[start:end].decode('cp1252').split('\n')
        for line in meta_list:
            temp = line.split('=')
            if len(temp) == 2:
                self.meta[temp[0]] = temp[1][:-1]
                
    def _extracted_meta(self):
        """
        Assign meta data to easily readable properties
        input: None
        output: None, it just populates all the self.properties
        One can expand these at will, one may use the method meta_key() to see what keys are available
        """
        self.file_version = self.meta['file_version']
        self.xPixel = int(self.meta['Num.X / Num.X'])
        self.yPixel = int(self.meta['Num.Y / Num.Y'])
        self.channels = int(self.meta['Channels / Channels'])
        self.ch_zoff = float(self.meta['CHModeZoff / CHModeZoff'])
        self.chmode = int(self.meta['CHMode / CHMode'])
        self.rotation = float(self.meta['Rotation / Rotation'])
        self.ddeltaX = int(self.meta['DX_DIV_DDelta-X / DX/DDeltaX'])
        self.deltaX_dac = int(self.meta['Delta X / Delta X [Dac]'])
        self.channels_code = self.meta['Channelselectval / Channelselectval']
                        
    def _file2meta_dict(self):
        """
        Not in use
        Open .dat file with asci encoding, read meta data directly from .dat file, fill out the meta_dict  
        input: self
        output: None       
        """
        with open(self.fp, 'r') as f:
            for i in range(cgc['g_file_meta_total_lines']):
                temp = f.readline().split('=')
                if len(temp) == 2:
                    self.meta[temp[0]] = temp[1][:-1]
    
    def _line_list2meta_dict(self, start, end):
        """
        Fill the self.meta dict from the line list
        input: self._line_list
        output: None. It just fills out the self.dict.
        prerequisite: self._line_list
        """
        self.meta['file_version'] = self._line_list[0]
        for l in self._line_list[start:end]:
            temp = l.split('\n')[0].split('=')
            if len(temp) == 2:
                self.meta[temp[0]] = temp[1]
    
    def _spec_meta(self, pos, index_header, vz_header, spec_headers):
        """
        Extract the spec meta data from the file, it includes Number of spec pts, X_position, Y_position and 
        Channel code
        input: line position number in the file, index_header, which is e.g. 'idx'
        vz_header, which is e.g. ['V', 'Z']
        and spec_headers, see Createc_global_const
        output: self.spec_total_pt
                self.spec_pos_x
                self.spec_pos_y
                self.spec_channel_code
                self.spec_headers
        """
        result = re.findall('(\d+)', self._line_list[pos])
        self.spec_total_pt = int(result[0])
        self.spec_pos_x = int(result[1])
        self.spec_pos_y = int(result[2])
        self.spec_channel_code = int(result[3])
        self._filter = [b == '1' for b in bin(self.spec_channel_code)[2:].rjust(len(cgc[spec_headers]))[::-1]]
        self.spec_headers = cgc[index_header] +\
                            cgc[vz_header]+\
                            list(compress(cgc[spec_headers], self._filter))
        
class VERT_SPEC(GENERIC_FILE):
    """
    Read the .vert file and generate useful and managable stuff
    """
    def __init__(self, file_path):
        super().__init__(file_path)
        with open(self.fp, 'r') as f:
            self._line_list = f.readlines()

        super()._line_list2meta_dict(start=0, end=cgc['g_file_meta_total_lines'])
        super()._extracted_meta()
            
        super()._spec_meta(pos = cgc['g_file_spec_meta_line'],
                           index_header = 'g_file_spec_index_header',
                           vz_header = 'g_file_spec_vz_header',
                           spec_headers = 'g_file_spec_headers')
        f_obj = io.StringIO('\n'.join(self._line_list[cgc['g_file_spec_skip_rows']:]))
        self.spec = pd.read_csv(filepath_or_buffer = f_obj, sep = cgc['g_file_spec_delimiter'],
                                header = None,
                                names = self.spec_headers,
                                index_col = cgc['g_file_spec_index_header'],
                                engine='python',
                                usecols=range(len(self.spec_headers)))
class DAT_IMG_v2:
    pass

class DAT_IMG:
    """
    Read .dat file and generate meta data and images as numpy arrays.
    input: option 1: one arg, i.e. the full .dat file path
           option 2: two named args
           a. the binary content of the file together
           b. the file_name as a string
    output: dat_file_object with meta data and image numpy arrays.
    Meta data is a dict, one can expand the dict at will, see the constructor.
    Images are a list of numpy arrays.
    """
    def __init__(self, file_path=None, file_binary=None, file_name=None):
        self.meta = dict()
        self.img_array_list = []
        
        if file_path is not None:
            self.fp = file_path
            _, self.fn = os.path.split(self.fp)
            self._meta_binary, self._data_binary = self._read_binary()
        else:
            self.fn = file_name
            self._meta_binary = file_binary[:int(cgc['g_file_meta_binary_len'])]
            self._data_binary = file_binary[int(cgc['g_file_data_bin_offset']):]

        self._bin2meta_dict()
        self._extracted_meta()

        self._read_img()

        # imgs are numpy arrays, with rows with only zeros cropped off
        self.imgs = [self._crop_img(arr) for arr in self.img_array_list]
        # assert(len(set(img.shape for img in self.imgs)) <= 1)
        # Pixels = namedtuple('Pixels', ['y', 'x'])
        self.img_pixels = XY2D(y=self.imgs[0].shape[0], 
                               x=self.imgs[0].shape[1]) # size in (y, x)
        
        
    def _extracted_meta(self):
        """
        Assign meta data to easily readable properties
        input: None
        output: None, it just populates all the self.properties
        One can expand these at will, one may use the method meta_key() to see what keys are available
        """
        self.file_version = self.meta['file_version']
        self.xPixel = int(self.meta['Num.X / Num.X'])
        self.yPixel = int(self.meta['Num.Y / Num.Y'])
        self.channels = int(self.meta['Channels / Channels'])
        self.ch_zoff = float(self.meta['CHModeZoff / CHModeZoff'])
        self.ch_bias = float(self.meta['CHModeBias[mV] / CHModeBias[mV]'])
        self.chmode = int(self.meta['CHMode / CHMode'])
        self.rotation = float(self.meta['Rotation / Rotation'])
        self.ddeltaX = int(self.meta['DX_DIV_DDelta-X / DX/DDeltaX'])
        self.deltaX_dac = int(self.meta['Delta X / Delta X [Dac]'])
        self.channels_code = self.meta['Channelselectval / Channelselectval']   
        self.scan_ymode = int(self.meta['ScanYMode / ScanYMode'])
        self.xPiezoConst = float(self.meta['Xpiezoconst']) # Createc software error
        self.yPiezoConst = float(self.meta['YPiezoconst'])
        self.zPiezoConst = float(self.meta['ZPiezoconst'])
        
    def _read_binary(self):
        """
        Open .dat file in raw binary format
        input: self
        output: _meta_binary, _data_binary
        
        """
        with open(self.fp, 'rb') as f:
            _meta_binary = f.read(int(cgc['g_file_meta_binary_len']))
            f.seek(int(cgc['g_file_data_bin_offset']))
            _data_binary = f.read()
            return _meta_binary, _data_binary
        
    def _bin2meta_dict(self):
        """
        Convert meta binary to meta info using ansi encoding, filling out the meta dictionary
        Here ansi means Windows-1252 extended ascii code page CP-1252
        input: self
        output: None
        """
        meta_list = self._meta_binary.decode('cp1252', errors='ignore').split('\n')
        self.meta['file_version'] = meta_list[0]
        for line in meta_list:
            temp = line.split('=')
            if len(temp) == 2:
                self.meta[temp[0]] = temp[1][:-1]
                
    def _read_img(self):
        """
        Convert img binary to numpy array's, filling out the img_array_list.
        The image was compressed using zlib. So here they are decompressed.
        input: self
        prerequisite: self.xPixel, self.yPixel, self.channels
        output: None
        """
        decompressed_data = zlib.decompress(self._data_binary)
        img_array = np.fromstring(decompressed_data, np.dtype(cgc['g_file_dat_img_pixel_data_npdtype']))
        img_array = np.reshape(img_array[1: self.xPixel*self.yPixel*self.channels+1], (self.channels*self.yPixel, self.xPixel))
        for i in range(self.channels):
            self.img_array_list.append(img_array[self.yPixel*i:self.yPixel*(i+1)])   
        
    def meta_keys(self):
        """
        Print all available keys in meta
        input: self
        output: None
        """
        return [k for k in self.meta]
    
    def _file2meta_dict(self):
        """
        Not in use
        Open .dat file with asci encoding, read meta data directly from .dat file, fill out the meta_dict  
        input: self
        output: None       
        """
        with open(self.fp, 'r') as f:
            for i in range(cgc['g_file_meta_total_lines']):
                temp = f.readline().split('=')
                if len(temp) == 2:
                    self.meta[temp[0]] = temp[1][:-1]
    
    def _file2img_arrays(self):
        """
        Not in use
        Open .dat file in raw binary format, start from a global constant g_file_data_bin_offset = 16384
        fill out the img_array_list with images in the format of numpy array's
        input: self
        prerequisite: self.xPixel, self.yPixel, self.channels
        output: None
        """
        with open(self.fp, 'rb') as f:
            f.seek(cgc['g_file_data_bin_offset'])
            decompressed_data = zlib.decompress(f.read())
            img_array = np.fromstring(decompressed_data, np.dtype(cgc['g_file_dat_img_pixel_data_npdtype']))
            img_array = np.reshape(img_array[1: self.xPixel*self.yPixel*self.channels+1], (self.channels*self.yPixel, self.xPixel))
            for i in range(self.channels):
                self.img_array_list.append(img_array[self.yPixel*i:self.yPixel*(i+1)])

    def _crop_img(self, arr):
        """
        crop an image, by removing all rows which contain only zeros.
        """
        return arr[~np.all(arr == 0, axis=1)]
    
    @property
    def offset(self):
        """
        return offset relatvie to the whole range in angstrom in the format of 
        namedtuple (x, y)
        """
        x_offset = np.float(self.meta['Scanrotoffx / OffsetX'])
        y_offset = np.float(self.meta['Scanrotoffy / OffsetY'])

        # x_piezo_const = np.float(self.meta['Xpiezoconst'])
        # y_piezo_const = np.float(self.meta['YPiezoconst'])

        x_offset = -x_offset*cgc['g_XY_volt']*self.xPiezoConst/2**cgc['g_XY_bits']
        y_offset = -y_offset*cgc['g_XY_volt']*self.yPiezoConst/2**cgc['g_XY_bits']

        # Offset = namedtuple('Offset', ['y', 'x'])
        return XY2D(y=y_offset, x=x_offset)

    @property
    def size(self):
        """
        return the true size of image in angstrom in namedtuple (x, y)
        """
        x = float(self.meta['Length x[A]']) * self.img_pixels.x / self.xPixel
        y = float(self.meta['Length y[A]']) * self.img_pixels.y / self.yPixel
        # Size = namedtuple('Size', ['y', 'x'])
        return XY2D(y=y, x=x)

    @property
    def nom_size(self):
        """
        return nominal size of image in angstrom in namedtuple (x, y)
        assuming no pre-termination while scanning
        """
        # Size = namedtuple('Size', ['y', 'x'])
        return XY2D(y=float(self.meta['Length y[A]']), 
                    x=float(self.meta['Length x[A]']))

    @property
    def datetime(self):
        """
        return datetime objext of the file using the file name
        """
        import textwrap, datetime
        temp = textwrap.wrap(''.join(filter(str.isdigit, self.fn)), 2)
        temp = [int(s) for s in temp]
        temp[0] += cgc['g_file_year_pre']
        return datetime.datetime(*temp)

    @property
    def timestamp(self):
        """
        same as datetime, but it converts to seconds since 1970, 1, 1.
        """
        import datetime
        return self.datetime.timestamp()