Modules and example scripts to interface with the Createc STM

- createc: contains two main modules
   - Createc_pyCOM: contains a wrapper class to interface with the Createc software
   
        After `import createc` an instance can be created using
        `stm = createc.Createc_pyCOM.CreatecWin32()`

        By calling `stm.client.stmbeep()`, the testing beep sound should be heard.
        All other remote operation can be found at [spm-wiki](http://archive.today/I7Aw0).
        
        In addtion, several custom methods are available, such as
        `stm.ramp_bias_mV` and `stm.ramp_current_pA` etc.

   - Createc_pyFile: contains several classes to read .dat, .vert files etc.
        For example, an image instance can be created by 
        `image_file = createc.Createc_pyFile.DAT_IMG('path/to/filename.dat')`

- examples: contains useful scripts to communicate with the STM.
