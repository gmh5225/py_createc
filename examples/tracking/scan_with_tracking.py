# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 18:48:48 2019

@author: xuc1

Scan with tracking
Autofilesave should be OFF
Be careful about daylight saving time where the continuous shift-finding can fail.
"""
from createc.Createc_pyFile import DAT_IMG
# from skimage.feature import register_translation as rt
from skimage.registration import phase_cross_correlation as pcc
from skimage.exposure import rescale_intensity as ri
from skimage.filters import gaussian
import numpy as np
import time
from createc.Createc_pyCOM import CreatecWin32
from createc.utils.image_utils import level_correction
import logging.config
import yaml
import sys
import os
import datetime


def find_shift(img_src, img_des, img_previous, extra_sec, continuous_drift=True):
    """

    Parameters
    ----------
    img_src
    img_des
    img_previous
    extra_sec
    continuous_drift

    Returns
    -------

    """
    shift = [pcc(level_correction(gaussian(ri(src))), level_correction(gaussian(ri(des))))[0]
             for src, des in zip([img_src.img_array_list[i] for i in params['shift_reg_channel']],
                                 [img_des.img_array_list[i] for i in params['shift_reg_channel']])]
    shift = np.mean(shift, axis=0)
    dt1 = img_src.timestamp - img_previous.timestamp
    dt2 = time.time() + extra_sec - img_previous.timestamp
    shift_c = shift * dt2 / dt1
    return shift_c if continuous_drift else shift


this_dir = os.path.dirname(__file__)
log_config = os.path.join(this_dir, 'logging_tracking.config')
log_fn = 'log_' + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + '.log'
logging.config.fileConfig(log_config, defaults={'logfilename': os.path.join(this_dir, 'logs', log_fn).replace('\\', '\\\\')})
logger = logging.getLogger('this_logger')

yaml_param = os.path.join(this_dir, 'parameters.yaml')
with open(yaml_param, 'rt') as f:
    params = yaml.safe_load(f.read())

stm = CreatecWin32()
template = stm.savedatfilename if params['use_last_as_template'] else params['template_folder'] + params[
    'template_file']
if template == '':
    print('There is no most recent image to be used as template')
    sys.exit()

try:
    img_des = DAT_IMG(template)
except FileNotFoundError:
    print('Template file cannot be opened.')
    sys.exit()

img_previous = img_des
logger.info('Start.' + '*' * 30)
logger.info('template: ' + template[-params['g_filename_len']:])

idx = 0

if params['Const_Height'] == 0:  # const current scan series
    Bias_Range_mV = np.linspace(params['StartBias_mV'], params['EndBias_mV'], params['Total_'])
    Current_Range_pA = np.linspace(params['StartCurrent_pA'], params['EndCurrent_pA'], params['Total_'])
    Height_Range_Angstrom = [0] * params['Total_']
else:  # const height scan series
    Bias_Range_mV = [img_des.bias] * params['Total_']
    Current_Range_pA = [img_des.current] * params['Total_']
    Height_Range_Angstrom = np.linspace(params['StartHeight'], params['EndHeight'], params['Total_'])
    CH_Bias_Range_mV = np.linspace(params['StartBias'], params['EndBias'], params['TotalBias'])

for ch_zoff, ci_bias, ci_current in zip(Height_Range_Angstrom, Bias_Range_mV, Current_Range_pA):
    logger.info('-' * 10)
    logger.info('ch_zoff %.2f' % round(ch_zoff, 2))
    logger.info('ci_bias %.2f' % round(ci_bias, 2))
    logger.info('ci_current %.2f' % round(ci_current, 2))

    for ch_bias in CH_Bias_Range_mV:
        idx += 1
        logger.info('ch_bias %.2f' % round(ch_bias, 2))
        logger.info('scan for alignment to template')
        stm.pre_scan_config(chmode=img_des.chmode,
                            ddeltaX=img_des.ddeltaX,
                            deltaX_dac=img_des.deltaX_dac,
                            channels_code=img_des.channels_code,
                            ch_zoff=0,
                            ch_bias=0,
                            bias=img_des.bias,
                            current=img_des.current)
        time_to_wait = float(stm.getparam('Sec/Image:'))
        time_to_wait = time_to_wait / 2 * (1 + 1 / float(stm.getparam('Delay Y')))
        stm.scanstart()
        time.sleep(time_to_wait)
        while stm.scanstatus:
            time.sleep(5)
        stm.filesave(stm.savedatfilename)
        cc_file_4align = stm.savedatfilename
        logger.info('cc_file_4align: ' + cc_file_4align[-params['g_filename_len']:])

        logger.info('Align to template')
        img_src = DAT_IMG(cc_file_4align)

        shift = find_shift(img_src, img_des, img_previous, params['g_reposition_delay'],
                           continuous_drift=True)

        logger.info('[dy, dx] = {}'.format(shift))
        stm.setxyoffpixel(dx=shift[1], dy=shift[0])
        time.sleep(params['g_reposition_delay'])

        # for testing shift registration
        """
        import random
        time_to_wait = float(stm.getparam('Sec/Image:'))
        time_to_wait = time_to_wait / 2 * (1 + 1 / float(stm.getparam('Delay Y')))
        stm.scanstart()
        time.sleep(time_to_wait)
        while stm.scanstatus:
            time.sleep(5)
        stm.filesave(stm.savedatfilename)
        cc_file_after_align = stm.savedatfilename
        logger.info('cc_file_after_align: '+ cc_file_after_align[-params['g_filename_len']:])
        
        logger.info('Mock drifting')
        shift = random.choice([50, -50]), random.choice([50, -50])
        logger.info('[dy, dx] = {}'.format(shift))
        stm.setxyoffpixel(dx=shift[1], dy=shift[0])
        time.sleep(params['g_reposition_delay'])        
        """

        if params['Pre_cc_scan']['in_use']:
            logger.info('Pre const-current scan')
            stm.pre_scan_config(chmode=0,  # pre_cc_scan is always in const mode
                                deltaX_dac=params['deltaX_dac'],
                                channels_code=params['Pre_cc_scan']['channels_code'])
            time_to_wait = float(stm.getparam('Sec/Image:'))
            time_to_wait = time_to_wait / 2 * (1 + 1 / float(stm.getparam('Delay Y')))
            stm.scanstart()
            time.sleep(time_to_wait)
            while stm.scanstatus:
                time.sleep(5)
            stm.filesave(stm.savedatfilename)
            logger.info('cc: ' + stm.savedatfilename[-params['g_filename_len']:])
            img_previous = DAT_IMG(stm.savedatfilename)

        logger.info('Data scan')
        stm.pre_scan_config(chmode=params['Const_Height'],
                            ddeltaX=params['Data_scan']['ddeltaX'],
                            channels_code=params['Data_scan']['channels_code'],
                            ch_zoff=ch_zoff,
                            ch_bias=ch_bias,
                            bias=ci_bias,
                            current=ci_current)
        time_to_wait = float(stm.getparam('Sec/Image:'))
        time_to_wait = time_to_wait / 2 * (1 + 1 / float(stm.getparam('Delay Y')))
        stm.scanstart()
        time.sleep(time_to_wait)
        while stm.scanstatus:
            time.sleep(5)
        stm.filesave(stm.savedatfilename)
        logger.info('data: ' + stm.savedatfilename[-params['g_filename_len']:])

logger.info('Final template scan')
stm.pre_scan_config(chmode=img_des.chmode,
                ddeltaX=img_des.ddeltaX,
                deltaX_dac=img_des.deltaX_dac,
                channels_code=img_des.channels_code,
                ch_zoff=0,
                ch_bias=0,
                bias=img_des.bias,
                current=img_des.current)
time_to_wait = float(stm.getparam('Sec/Image:'))
time_to_wait = time_to_wait / 2 * (1 + 1 / float(stm.getparam('Delay Y')))
stm.scanstart()
time.sleep(time_to_wait)
while stm.scanstatus:
    time.sleep(5)
stm.filesave(stm.savedatfilename)
logger.info(stm.savedatfilename[-params['g_filename_len']:])
logger.info('Done.')
