.. -*-coding: utf-8 -*-

FAQs
====

Q:
    How do I install ``Mpylab`` as a user?


A:
    Users should use a local virtual environment. The easiest way using ``uv`` (https://docs.astral.sh/uv/) looks like this::

        > mkdir Mpylab
        > cd Mpylab
        > uv venv
        > source .venv/bin/activate
        > uv pip install Mpylab

Q:
    How do I install ``Mpylab`` as a developer?


A:
    Developers should install an editable version from the local Git repositories into a local virtual environment. The easiest way using ``uv`` (https://docs.astral.sh/uv/) looks like this::

        > mkdir mpylab-develop
        > cd mpylab-develop
        > git clone https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab/mpylab.git
        > git clone https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab/scuq.git
        > mkdir venv-mpylab
        > cd venv-mpylab
        > uv venv
        > source .venv/bin/activate
        > uv pip install -e ../scuq
        > uv pip inatall -e ../mpylab


Q:
    Where can I find documentation on ``Mpylab``?

A:
    The documentation is available online: (https://mpylab.readthedocs.io/en/latest/)

Q:
    How do I contribute to ``MpyLab``?

A:
    If you are a registered contributor, you simply push to the repository. Otherwise, you have to create a pull-request. See the github documentation for more details (https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).


Q:
   Why is Python used as the programming language?

A:
   Python (http://www.python.org/) has several advantages:

   - It is easy to learn
   - It is well documented
   - It is free
   - It runs on many platforms
   - There are many modules that are ideal for scientific calculations, measurement tasks, and graphical data output


Q:
    Which version of Python should be used?

A:
   Python version 3.8 or higher should be used.



Q:
   Which editor should be used?

A:
   Mainly, this is a matter of preference. An overview of Python development environments can be found
   here, for example: (https://wiki.python.org/moin/IntegratedDevelopmentEnvironments).
   Popular IDEs are PyCharm (https://www.jetbrains.com/pycharm/) or
   Visual Studio Code (https://code.visualstudio.com/).


Q:
   Which encoding should be used?

A:
   The standard is UTF-8 (8-bit Unicode Transformation Format).


Q:
   Which debugger should you use?

A:
    Python includes its own debugger, pdb (https://docs.python.org/3/library/pdb.html).
    The debuggers integrated into popular IDEs are at least as good.




Q:
   What other packages are required?

A:
   The dependencies can be found in the file ``requirements.txt`` (https://github.com/hgkdd/Mpy/blob/main/requirements.txt).

Q:
    How can I test changes without compromising the stability of the stable version?

A:
    MpyLab should always be installed in a virtual environment.
    This can be done (for example) as follows::

        /home/USER/dev/test % git clone https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab/mpylab.git
        Cloning into 'mpylab'...
        remote: Enumerating objects: 3515, done.
        remote: Counting objects: 100% (40/40), done.
        remote: Compressing objects: 100% (36/36), done.
        remote: Total 3515 (delta 10), reused 16 (delta 3), pack-reused 3475 (from 2)
        Receiving objects: 100% (3515/3515), 29.05 MiB | 6.44 MiB/s, done.
        Resolving deltas: 100% (2266/2266), done.
        /home/USER/dev/test % git clone https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab/scuq.git
        Cloning into 'scuq'...
        remote: Enumerating objects: 294, done.
        remote: Counting objects: 100% (294/294), done.
        remote: Compressing objects: 100% (111/111), done.
        remote: Total 294 (delta 174), reused 291 (delta 171), pack-reused 0 (from 0)
        Receiving objects: 100% (294/294), 787.84 KiB | 4.40 MiB/s, done.
        Resolving deltas: 100% (174/174), done.
        /home/USER/dev/test % mkdir venv-mpy-develop
        /home/USER/dev/test % cd venv-mpy-develop
        /home/USER/dev/test/venv-mpy-develop % uv venv
        Using CPython 3.11.2 interpreter at: /opt/local/bin/python3.11
        Creating virtual environment at: .venv
        Activate with: source .venv/bin/activate
        /home/USER/dev/test/venv-mpy-develop % source .venv/bin/activate
        (venv-mpy-develop) /home/USER/dev/test/venv-mpy-develop % uv pip install -e ../scuq
        Resolved 2 packages in 580ms
              Built scuq @ file:///home/USER/dev/test/scuq
        Prepared 2 packages in 789ms
        Installed 2 packages in 13ms
         + numpy==2.3.3
         + scuq==0.9.1 (from file:///home/USER/dev/test/scuq)
        (venv-mpy-develop) /home/USER/dev/test/venv-mpy-develop % uv pip install -e ../mpylab
        Resolved 27 packages in 659ms
              Built mpylab @ file:///home/USER/dev/test/mpylab
        Prepared 8 packages in 8.13s
        Installed 25 packages in 53ms
         + bidict==0.23.1
         + contourpy==1.3.3
         + cycler==0.12.1
         + fonttools==4.60.0
         + gpib-ctypes==0.3.0
         + kiwisolver==1.4.9
         + levenshtein==0.27.1
         + matplotlib==3.10.6
         + mpylab==0.9.4 (from file:///home/USER/dev/test/mpylab)
         + packaging==25.0
         + pathvalidate==3.3.1
         + pillow==11.3.0
         + ply==3.11
         + pydot==4.0.1
         + pyparsing==3.2.5
         + pyserial==3.5
         + python-dateutil==2.9.0.post0
         + pyusb==1.3.1
         + pyvisa==1.15.0
         + pyvisa-py==0.8.1
         + rapidfuzz==3.14.1
         + scipy==1.16.2
         + simpleeval==1.0.3
         + six==1.17.0
         + typing-extensions==4.15.0
        (venv-mpy-develop) /home/USER/dev/test/venv-mpy-develop %

    Changes to the source files in ``/home/USER/dev/test/mpylab`` and ``/home/USER/dev/test/scuq`` are then automatically available in ``venv``. Tested changes should then be imported into the central Git repository.


Q:
   How do I get the source code?

A:
   ``MpyLab`` and ``scuq`` (and more) are available on GitLab TU Chemnitz (https://gitlab.hrz.tu-chemnitz.de/chair-of-electromagnetic-theory-and-compatibility-at-tu-dresden/mpylab).


