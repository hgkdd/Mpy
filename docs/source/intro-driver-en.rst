.. -*-coding: utf-8 -*-

Implementation of a driver
==========================

This document uses a simple example to describe the implementation of a custom
driver in ``MpyLab``.

The example uses a signal generator from Gigatronics with the type designation 12520A from
the 12000A Microwave Synthesizers Series.

The driver is based on the class :class:`SIGNALGENERATOR`, which in turn is based on the
class :class:`DRIVER`. All drivers are stored in the directory ``src/mpylab/device/``.

Creating a new driver
---------------------

The best way is to simply copy an existing driver, such as ``sg_res_swm.py``, and
save the file under a new name.
The syntax should consist of ``sg``, a manufacturer abbreviation, and a type abbreviation,
connected by underscores.

In general, the syntax is: ``sg_<manufacturer abbreviation>_<type abbreviation>.py``
In our specific case, the driver is called ``sg_gt_12520a.py``, for example.

Customizing the new driver
--------------------------

Now open the new driver file. It consists mainly of two parts:

    1. the definition of a new subclass for the specific signal generator
    2. the definition of a function :meth:`main`, which can be used to test the driver.


The first part consists of two parts:

    1. the definition of a function :meth:`__init__` to initialize the class
    2. the definition of a function :meth:`Init` to initialize the device

In the first part, the actual commands for controlling the device are defined in the dictionary ``_cmds``,
e.g., :meth:`SetFreq` to set the frequency. These commands are
all defined in the :class:`SIGNALGENERATOR` class.

For each entry, the dictionary contains a keyword with the general command
as a string, e.g., :meth:`SetFreq`. This keyword is assigned a list, where each
list entry is a tuple. Each tuple contains a command for an instruction and a
template for the subsequent response as a string.
Now you have to look up in the device documentation which GPIB/VISA command can be used to set the frequency, for example.

In our example, the command is::

   CW <value> <unit>

where the unit can be ``HZ``, ``KZ``, ``MZ``, or ``GZ`. The device does not respond to this command.

The :meth:`SetFreq` entry in the ``_cmds`` dictionary must now be adjusted accordingly::

   'SetFreq':  [("'CW %.1f HZ'%freq", None)]

The ``%.1f`` stands for the place where the value of the variable ``freq``
is written. ``%.1f`` stands for a floating point number with one decimal place.
Because no response is expected, the template is `None`.

Things get a little more complicated if you want to read a value from the device, e.g., the
frequency with :meth:`GetFreq`. The necessary GPIB/VISA command in our example is::

   OPCW

and the signal generator responds with, for example::

   1000000000.0

Accordingly, the :meth:`GetFreq` entry in the ``_cmds`` dictionary is::

   'GetFreq':  [( 'OPCW', r'(?P<freq>%s)'%self._FP)],

Since a response, namely the current frequency, is expected from the signal generator here,
the template is not ``None``, but corresponds to a specific character string, which will now be explained in more detail
.

The ``r`` before the string notation stands for Raw String Notation, and means that
backslashes in this string have no special meaning.

The ``%s`` means that the value of ``self._FP`` is inserted at this point.
The string ``self._FP`` contains the regular expression for a floating point number
in exponential notation.
The reason for this is that Python does not have a ``scanf`` command and can only extract numbers from strings
using regular expressions. The value of ``self._FP`` is defined in the
:class:`SIGNALGERATOR` class.

The ``(?P<freq>%s)`` now means that the floating point value of the frequency is extracted from the
response string
and stored as the variable ``freq``. This happens internally
in the :class:`DRIVER` class in the :meth:`_gpib_query` function via a ``re.match``.
The result of ``re.match`` is also a MatchObject that can be converted into a dictionary with ``groupdict``, which then contains the key ``freq`` and the frequency.

The same principle can be applied to all other commands.

In part B, the commands are made in the presets dictionary before default settings.
These commands must also be adjusted according to the above scheme if necessary.
			
Part B also consists of two main parts:

    1. the definition of a standard ``ini`` file
    2. the definition of a test run

In part a, a standard ``ini`` file is defined, which is used if no other
``ini`` file is entered via the command line. The ``ini`` file is defined within the file,
 customized using the :meth:`format_block` function, and made available as a
virtual file via ``StringIO``.

This ``ini`` file contains several blocks.

 - ``[description]`` for the general description of the device
 - ``[init_value]`` for the general definition of values
 - ``[channel_1]`` for the definition of values specific to a channel

Since signal generators can also have multiple outputs, there can also be
``[channel_2]``, etc., but in our case there is only ``[channel_1]``.
			
The following values are now defined in the ``[description]`` block::

   description: 'GT_12000A'      -> Type description
   type:        'SIGNALGENERATOR'     -> Associated Python class
   vendor:      'Giga-tronics'     -> Manufacturer

All other fields can be left blank, as the driver should be independent of the
exact serial number, etc.

The following values are defined in the ``[init_value]`` block, which represent the lowest common denominator of all types in the 12000A series::

   [Init_Value]
   fstart: 2e9     -> lowest frequency
   fstop: 8e9    -> highest frequency
   fstep: 0.1    -> smallest frequency step

Specifying the GPIB/VISA address does not really make sense here, but you can define one if you wish.

The `[Channel_1]` block contains information about the channel::

   name: RFOut        -> Name
   level: -100        -> Power value
   unit: ‘dBm’        -> Unit
   outputstate: 0    -> Output status (0=Off, 1=On)

In part B, the signal generator and driver are tested with a short test program.
To do this, the signal generator is initialized, a frequency is set, a power level is set,
and the output is switched on. The signal generator is then shut down.
	
Creating a special ``ini`` file
-------------------------------

The ``ini`` file is a simple text file that is saved under the name `sg_gt_12520a.ini`, for example.
It contains the blocks mentioned above, but its content is more specific It contains the blocks mentioned above, but its content is more specific
and designed not only for an entire type series, but for a specific type and
a specific device. Therefore, it is also useful to define a
serial number, firmware version, and other information here::

   [description]
   description: 12520A
   type:        SIGNAL GENERATOR
   vendor:      Giga-tronics
   serialnr:    121015
   deviceid:
   driver:      sg_gt_12000a.py
   version:     0.73
   build-nr:    49.24

   [Init_Value]
   fstart: 10e6
   fstop: 20e9
   fstep: 0.1
   gpib: 6
   virtual: 0

   [Channel_1]
   name: RFOut
   level: -100
   unit: ‘dBm’
   outputstate: 0


Testing the new driver
-----------------------

The easiest way to test the new driver is to simply call it up. To do this, go to the /mpylab/device/ directory using the command line and call up::

   python sg_gt_12000a.py

This creates the new driver class and starts the test program. If the
program runs without any error messages, then everything defined in the test program is working.

With::

   python sg_gt_12000a.py sg_gt_12520a.ini

you can configure and test the driver with the special ``ini`` file.

If problems occur, it is useful to call python with the -i switch to remain in interactive mode after the error occurs.
If the new class was created without any problems, you can use::

   sg=SIGNALGENERATOR()
   ini=‘sg_gt_12520a.ini’
   err=sg.Init(ini)
   err,freq=sg.SetFreq(1e9)
   ...

to find an error.


The procedure described can of course also be applied to power meters, amplifiers,
etc.

