.. -*-coding: utf-8 -*-

Installation als Nutzer
=======================

Nutzer von ``MPyLab`` (im Gegensatz zu Entwicklern von ``MpyLab``) installieren einfach von **PyPi** (https://pypi.org/)::

   pip3 install mpylab

Abhängigkeiten werden mitinstalliert. Es wird dringend empfohlen, eine virtuelle Umgebung zu nutzen, z.B.::

    > mkdir venv && cd venv
    > uv venv
    > source ./.venv/bin/activate
    (venv) > uv pip install mpylab

Die Verwendung von ``uv`` (https://docs.astral.sh/uv/) ist hierbei natürlich obtional.