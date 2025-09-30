Installation of ``MpyLab`` for Developpers
==========================================

The following walk-through shows the installation process for ``MpyLab`` (and ``scuq``) (for developpers) in a virtual environment beginnig with freshly cloned repositories.

Make a directory and change to that directory:

.. code-block:: console

    foo@bar:path> mkdir test-mpylab
    foo@bar:path> cd test-mpylab

Now clone the two main packages **scuq** and **mpylab**:

.. code-block:: console

    foo@bar:path/test-mpylab> gh repo clone hgkdd/scuq   # or git clone https://github.com/hgkdd/scuq.git
    Cloning into 'scuq'...
    remote: Enumerating objects: 294, done.
    remote: Counting objects: 100% (294/294), done.
    remote: Compressing objects: 100% (111/111), done.
    remote: Total 294 (delta 174), reused 291 (delta 171), pack-reused 0 (from 0)
    Receiving objects: 100% (294/294), 787.84 KiB | 12.50 MiB/s, done.
    Resolving deltas: 100% (174/174), done.
    foo@bar:path/test-mpylab> gh repo clone hgkdd/Mpy MpyLab  # or git clone https://github.com/hgkdd/Mpy.git MpyLab
    Cloning into 'MpyLab'...
    remote: Enumerating objects: 3515, done.
    remote: Counting objects: 100% (40/40), done.
    remote: Compressing objects: 100% (36/36), done.
    remote: Total 3515 (delta 10), reused 16 (delta 3), pack-reused 3475 (from 2)
    Receiving objects: 100% (3515/3515), 29.05 MiB | 39.20 MiB/s, done.
    Resolving deltas: 100% (2266/2266), done.

Next we create a virtual environment and activate the environment:

.. code-block:: console

    foo@bar:path/test-mpylab> mkdir venv-mpylab && cd venv-mpylab
    foo@bar:path/test-mpylab/venv-mpylab> uv venv
    Using CPython 3.11.2 interpreter at: /opt/local/bin/python3.11
    Creating virtual environment at: .venv
    Activate with: source .venv/bin/activate
    foo@bar:path/test-mpylab/venv-mpylab> source .venv/bin/activate
    (venv-mpylab) foo@bar:path/test-mpylab/venv-mpylab>

The active venv is marked with the prefix **(venv-mpylab)** in front of your prompt.

Now, we are going to install **scuq** from the source tree. The option '-e' installs it in editable mode:

.. code-block:: console

    (venv-mpylab) foo@bar:path/test-mpylab/venv-mpylab> uv pip install -e ../scuq
    Prepared 1 package in 402ms
    Installed 2 packages in 23ms
    + numpy==2.3.3
    + scuq==0.9.1 (from file:///../scuq)

Finally, install **mpylab** from its source tree as an editable module:

.. code-block:: console

    (venv-mpylab) foo@bar:path/test-mpylab/venv-mpylab> uv pip install -e ../Mpylab
    Resolved 27 packages in 151ms
       Built mpylab @ file:///Users/hgkrauth/Documents/Development/uv-git-test/Mpylab
    Prepared 1 package in 299ms
    Installed 25 packages in 61ms
     + bidict==0.23.1
     + contourpy==1.3.3
     + cycler==0.12.1
     + fonttools==4.60.0
     + gpib-ctypes==0.3.0
     + kiwisolver==1.4.9
     + levenshtein==0.27.1
     + matplotlib==3.10.6
     + mpylab==0.9.4 (from file:///../Mpylab)
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
    (venv-mpylab) foo@bar:path/test-mpylab/venv-mpylab>

You are now ready to use the ``MpyLab`` framework. Enjoy!


