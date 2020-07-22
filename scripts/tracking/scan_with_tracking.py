# -*- coding: utf-8 -*-
"""
Created on Thu Mar 28 18:48:48 2019

@author: xuc1

Scan with tracking
Autofilesave should be OFF

"""
from py_createc.Createc_pyFile import DAT_IMG
#from skimage.feature import register_translation as rt
from skimage.registration import phase_cross_correlation as pcc
from skimage.exposure import rescale_intensity as ri
from skimage.filters import gaussian
import numpy as np
import time
from py_createc.Createc_pyCOM import CreatecWin32
import logging
import logging.config
import yaml


def level_correction(Y):
    m, n = Y.shape
    assert m >=2 and n >= 2
    X1, X2 = np.mgrid[:m, :n]
    X = np.hstack((np.reshape(X1, (m*n, 1)), np.reshape(X2, (m*n, 1))))
    X = np.hstack((np.ones((m*n, 1)), X))
    YY = np.reshape(Y, (m*n, 1))
    theta = np.dot(np.dot(np.linalg.pinv(np.dot(X.transpose(), X)), X.transpose()), YY)
    plane = np.reshape(np.dot(X, theta), (m, n))
    return Y-plane

def find_shift(img_src, img_des, img_previous, extra_sec, continuous_drift=True):
    shift = [pcc(level_correction(gaussian(ri(src))), level_correction(gaussian(ri(des))))[0] 
              for src, des in zip([img_src.img_array_list[i] for i in params['shift_reg_channel']], 
                                  [img_des.img_array_list[i] for i in params['shift_reg_channel']])]
    shift = np.mean(shift, axis=0)
    dt1 = img_src.timestamp - img_previous.timestamp
    dt2 = time.time() + extra_sec - img_previous.timestamp
    shift_c = shift * dt2 / dt1
    return shift_c if continuous_drift else shift


with open('./scripts/tracking/logging_tracking.yaml', 'rt') as f:
    config = yaml.safe_load(f.read())
logging.config.dictConfig(config)    
logger = logging.getLogger('main')
 
with open('./scripts/tracking/parameters.yaml', 'rt') as f:
    params = yaml.safe_load(f.read())
    
logger.info('Start.'+'*'*30)    
createc = CreatecWin32()
template = createc.savedatfilename if params['use_last_as_template'] else params['template_folder']+params['template_file']
img_des = DAT_IMG(template)
img_previous = img_des
logger.info('template: '+ template[-params['g_filename_len']:])

idx = 0
Height_Range_Angstrom = np.linspace(params['StartHeight'], params['EndHeight'], params['Total_steps'])
for ch_zoff in Height_Range_Angstrom:
    logger.info('-' *10)
    logger.info('ch_zoff %.2f' % round(ch_zoff,2))

    for ch_bias in params['Bias_Range_mV']:
        idx += 1
        logger.info('ch_bias %.2f' % round(ch_bias,2))
        logger.info('scan for alignment to template')
        createc.pre_scan_01(img_des.chmode, img_des.rotation, img_des.ddeltaX,
                                   img_des.deltaX_dac, img_des.channels_code)
        createc.do_scan_01()
        time.sleep(2)
        createc.client.quicksave()
        cc_file_4align = createc.client.savedatfilename
        logger.info('cc_file_4align: ' + cc_file_4align[-params['g_filename_len']:])
        
        logger.info('Align to template')
        img_src = DAT_IMG(cc_file_4align)

        shift = find_shift(img_src, img_des, img_previous, params['g_reposition_delay'],
                           continuous_drift=True)

        logger.info('[dy, dx] = {}'.format(shift))
        createc.setxyoffpixel(dx=shift[1], dy=shift[0])
        time.sleep(params['g_reposition_delay'])
            

        # for testing shift registration
        """
        import random
        createc.do_scan_01()
        time.sleep(2)
        createc.client.quicksave()
        cc_file_after_align = createc.client.savedatfilename
        logger.info('cc_file_after_align: '+ cc_file_after_align[-params['g_filename_len']:])
        
        logger.info('Mock drifting')
        shift = random.choice([50, -50]), random.choice([50, -50])
        logger.info('[dy, dx] = {}'.format(shift))
        createc.setxyoffpixel(dx=shift[1], dy=shift[0])
        time.sleep(params['g_reposition_delay'])        
        """


        logger.info('const current mode scan')
        createc.pre_scan_01(params['Ccmode']['mode'],
                                   img_des.rotation,
                                   img_des.ddeltaX,
                                   params['deltaX_dac'],
                                   params['Ccmode']['channels_code'])
        createc.do_scan_01()
        time.sleep(2)
        createc.client.quicksave()
        logger.info('cc: ' + createc.client.savedatfilename[-params['g_filename_len']:])
        img_previous = DAT_IMG(createc.client.savedatfilename)

        logger.info('const height mode scan')
        createc.pre_scan_01(params['Chmode']['mode'],
                                   img_des.rotation,
                                   params['Chmode']['ddeltaX'],
                                   params['deltaX_dac'],
                                   params['Chmode']['channels_code'],
                                   ch_zoff, ch_bias)
        createc.do_scan_01()
        time.sleep(2)
        createc.client.quicksave()
        logger.info('ch: ' + createc.client.savedatfilename[-params['g_filename_len']:])

logger.info('Final template scan')        
createc.pre_scan_01(img_des.chmode,
                           img_des.rotation,
                           img_des.ddeltaX,
                           img_des.deltaX_dac,
                           img_des.channels_code)
createc.do_scan_01()
time.sleep(2)
createc.client.quicksave()
logger.info(createc.client.savedatfilename[-params['g_filename_len']:])                      
logger.info('Done.')