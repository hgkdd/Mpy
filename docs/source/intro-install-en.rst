.. -*-coding: utf-8 -*-

Installation of ``MpyLab`` for Users
====================================

Users of ``MPyLab`` (as opposed to developers of ``MpyLab``) simply install from **PyPi** (https://pypi.org/)::

   pip3 install mpylab

Dependencies are installed along with it. It is strongly recommended to use a virtual environment, e.g.::

    > mkdir venv && cd venv
    > uv venv
    > source ./.venv/bin/activate
    (venv) > uv pip install mpylab

The use of ``uv`` (https://docs.astral.sh/uv/) is optional, of course.