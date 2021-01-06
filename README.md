Modules and scripts to interface with Createc STM

- createc: contains two main modules
   - Createc_pyCOM: contains a wrapper class to interface with the Createc software
   
        After `import createc` an instance can be created using
        `stm = createc.Createc_pyCOM.CreatecWin32()`

        By calling `stm.client.stmbeep()`, the testing beep sound will be heard.
        All other availabe remote operation can be found at [spm-wiki](http://spm-wiki.createc.de/index.php?title=STMAFM_Remote_Operation)
        
        In addtion, several custom methods are available, such as
        `stm.ramp_bias_mV` and `stm.ramp_current_pA` etc.

   - Createc_pyFile: contains several classes to read .dat, .vert files etc.
        For example, an image instance can be created by 
        `image_file = createc.Createc_pyFile.DAT_IMG('path/to/filename.dat')`

- scripts: contains useful scripts
which can be excuted starting in the top directory using e.g.
python -m scripts.osc.oscilloscope -z

To do:
- adjust annotation font size in oscilloscope
- refactor list of z_off for tracking script
- refactor pyFile for inheritance
- isolate confidential parameters
- take gain into consideration for ramping current
- hover to show file name does not work for tilted image in map script