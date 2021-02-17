Py-Createc
==========

Modules and example scripts to interface with the `Createc STM <https://www.createc.de/LT-STMAFM>`_.

Installation
------------

Installation of the package can be done through `PIP <https://pip.pypa.io>`_:

``pip install createc``


Quickstart
----------

:py:class:`createc.CreatecWin32` is a wrapper class to interface with the Createc software.
It provides access to all remote operations that can be found at the `stm-wiki <http://archive.today/I7Aw0>`_.
In addition, there are several custom methods available, such as :py:meth:`createc.CreatecWin32.ramp_bias_mV` and :py:meth:`createc.CreatecWin32.ramp_current_pA`, etc.

Here is an example that plays the testing beep sound on the STM:

.. code-block:: python

   import createc
   stm = createc.CreatecWin32()
   stm.client.stmbeep()

Furthermore, several classes are available to to read ``.dat``, ``.vert`` files etc.
For example, an image instance can be created by:

.. code-block:: python

   import createc
   image_file = createc.DAT_IMG('path/to/filename.dat')


More elaborate examples
-----------------------

The `examples folder <https://github.com/chenxu2394/py_createc/tree/main/examples>`_ contains useful scripts to communicate with the STM.
These scripts show off the more advanced features of the Py-Createc package.


API Documentation
-----------------

Finally, there is the comprehensive :ref:`API documentation`.


Citation
--------

If you use Py-Createc in a research project, pleace cite the following paper:


Author
------
Chen Xu <cxu.self@gmail.com>
